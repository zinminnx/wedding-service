import hashlib
import hmac

from django.utils import timezone

from .models import PrintAgentDevice


def _raw_token(request):
    authorization = request.headers.get("Authorization", "").strip()
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return request.headers.get("X-Print-Agent-Token", "").strip()


def authenticate_agent(request):
    token = _raw_token(request)
    if len(token) < 32 or len(token) > 256:
        return None
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    device = (
        PrintAgentDevice.objects.select_related("wedding")
        .filter(token_hash=digest, enabled=True)
        .first()
    )
    if not device or not hmac.compare_digest(device.token_hash, digest):
        return None
    # Deliberately lightweight; every authenticated call refreshes last_seen_at.
    PrintAgentDevice.objects.filter(pk=device.pk).update(last_seen_at=timezone.now())
    device.last_seen_at = timezone.now()
    return device
