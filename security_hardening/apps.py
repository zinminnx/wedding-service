from django.apps import AppConfig


class SecurityHardeningConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "security_hardening"
    verbose_name = "EverAfter Security Hardening"

    def ready(self):
        # Register deployment checks only when Django's app registry is ready.
        from . import checks  # noqa: F401
