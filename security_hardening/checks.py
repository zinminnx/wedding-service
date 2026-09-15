from django.conf import settings
from django.core.checks import Error, Tags, Warning, register


@register(Tags.security)
def everafter_security_checks(app_configs, **kwargs):
    if not getattr(settings, "EVERAFTER_PRODUCTION", False):
        return []

    issues = []
    if settings.DEBUG:
        issues.append(Error("DEBUG must be False in production.", id="everafter.E14001"))

    secret = str(getattr(settings, "SECRET_KEY", "") or "")
    if len(secret) < 50:
        issues.append(Error("DJANGO_SECRET_KEY must be at least 50 characters in production.", id="everafter.E14002"))

    hosts = list(getattr(settings, "ALLOWED_HOSTS", []) or [])
    if not hosts or "*" in hosts:
        issues.append(Error("Set explicit DJANGO_ALLOWED_HOSTS; wildcard hosts are not allowed.", id="everafter.E14003"))

    if not getattr(settings, "SESSION_COOKIE_SECURE", False):
        issues.append(Error("SESSION_COOKIE_SECURE must be enabled in production.", id="everafter.E14004"))
    if not getattr(settings, "CSRF_COOKIE_SECURE", False):
        issues.append(Error("CSRF_COOKIE_SECURE must be enabled in production.", id="everafter.E14005"))
    if not getattr(settings, "SECURE_SSL_REDIRECT", False):
        issues.append(Error("SECURE_SSL_REDIRECT must be enabled in production.", id="everafter.E14006"))
    if int(getattr(settings, "SECURE_HSTS_SECONDS", 0) or 0) < 3600:
        issues.append(Warning("HSTS is below one hour. Use a longer value after HTTPS is confirmed.", id="everafter.W14001"))

    origins = list(getattr(settings, "CSRF_TRUSTED_ORIGINS", []) or [])
    insecure_origins = [item for item in origins if not item.startswith("https://")]
    if insecure_origins:
        issues.append(Error("Production CSRF trusted origins must use https://.", id="everafter.E14007"))

    return issues
