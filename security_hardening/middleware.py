import hashlib
import hmac
import logging
import secrets
import time

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse


logger = logging.getLogger("everafter.security")


class SecurityHardeningMiddleware:
    """
    Small dependency-free hardening layer.

    - Adds a random request correlation ID.
    - Adds conservative browser security headers.
    - Prevents authenticated dashboard/auth pages from being stored by shared caches.
    - Applies fixed-window rate limits to sensitive/public endpoints.

    Client addresses are never written to the cache or log in plaintext. The limiter
    stores a keyed SHA-256 fingerprint derived from the address and SECRET_KEY.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.everafter_request_id = secrets.token_hex(12)
        limited = self._rate_limit(request)
        if limited is not None:
            return self._finalize(request, limited)
        response = self.get_response(request)
        return self._finalize(request, response)

    def _finalize(self, request, response):
        response["X-Request-ID"] = getattr(request, "everafter_request_id", "")
        if not response.has_header("Referrer-Policy"):
            response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if not response.has_header("Permissions-Policy"):
            response["Permissions-Policy"] = "camera=(self), microphone=(), geolocation=()"
        if not response.has_header("X-Permitted-Cross-Domain-Policies"):
            response["X-Permitted-Cross-Domain-Policies"] = "none"

        path = request.path or "/"
        authenticated = bool(getattr(getattr(request, "user", None), "is_authenticated", False))
        if authenticated and (path.startswith("/dashboard/") or path.startswith("/admin/")):
            response["Cache-Control"] = "private, no-store, max-age=0"
            response["Pragma"] = "no-cache"
        elif path.startswith("/accounts/") or path.startswith("/health/"):
            response["Cache-Control"] = "no-store, max-age=0"
        return response

    def _rate_limit(self, request):
        if not getattr(settings, "EVERAFTER_RATE_LIMIT_ENABLED", True):
            return None

        if not getattr(settings, "EVERAFTER_PRODUCTION", False):
            remote = request.META.get("REMOTE_ADDR", "")
            if remote in {"127.0.0.1", "::1"}:
                return None

        rule = self._match_rule(request)
        if rule is None:
            return None
        bucket, limit, window = rule
        fingerprint = self._client_fingerprint(request)
        slot = int(time.time() // window)
        key = f"ea:rl:{bucket}:{slot}:{fingerprint}"

        try:
            if cache.add(key, 1, timeout=window + 5):
                count = 1
            else:
                count = cache.incr(key)
        except Exception:
            # Security controls should fail open rather than take the application down
            # if the cache backend has a transient outage.
            logger.exception("Rate-limit cache failure request_id=%s", request.everafter_request_id)
            return None

        if count <= limit:
            return None

        retry_after = window - (int(time.time()) % window)
        logger.warning(
            "Rate limit exceeded bucket=%s client=%s request_id=%s",
            bucket,
            fingerprint[:16],
            request.everafter_request_id,
        )
        if request.path.startswith("/api/"):
            response = JsonResponse({"detail": "Too many requests. Try again later."}, status=429)
        else:
            response = HttpResponse("Too many requests. Please try again later.", status=429)
        response["Retry-After"] = str(max(retry_after, 1))
        return response

    def _match_rule(self, request):
        method = request.method.upper()
        path = request.path or "/"

        # Limits are deliberately conservative enough for NAT/shared mobile networks.
        if method == "POST" and path in {"/accounts/login/", "/admin/login/"}:
            return "login", int(getattr(settings, "EVERAFTER_LOGIN_LIMIT", 12)), 300
        if path.startswith("/api/printing/agent/"):
            return "print-agent", int(getattr(settings, "EVERAFTER_AGENT_LIMIT", 600)), 60
        if path.startswith("/i/"):
            if method == "POST":
                return "public-write", int(getattr(settings, "EVERAFTER_PUBLIC_WRITE_LIMIT", 60)), 600
            if method in {"GET", "HEAD"}:
                return "public-read", int(getattr(settings, "EVERAFTER_PUBLIC_READ_LIMIT", 240)), 60
        return None

    def _client_fingerprint(self, request):
        trust_proxy = bool(getattr(settings, "EVERAFTER_TRUST_PROXY", False))
        value = request.META.get("REMOTE_ADDR", "") or "unknown"
        if trust_proxy:
            forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
            if forwarded:
                value = forwarded.split(",", 1)[0].strip() or value
        secret = str(getattr(settings, "SECRET_KEY", "everafter"))
        return hmac.new(secret.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()
