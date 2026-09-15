from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Validate EverVow production security settings without creating a test database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--allow-development",
            action="store_true",
            help="Return success when EVERAFTER_PRODUCTION is disabled; useful during local patch installation.",
        )

    def handle(self, *args, **options):
        production = bool(getattr(settings, "EVERAFTER_PRODUCTION", False))
        if not production:
            message = "EVERAFTER_PRODUCTION is disabled. Local development mode is active."
            if options["allow_development"]:
                self.stdout.write(self.style.WARNING(message))
                return
            raise CommandError(message)

        failures = []
        warnings = []

        secret = str(getattr(settings, "SECRET_KEY", "") or "")
        hosts = list(getattr(settings, "ALLOWED_HOSTS", []) or [])
        origins = list(getattr(settings, "CSRF_TRUSTED_ORIGINS", []) or [])

        if settings.DEBUG:
            failures.append("DEBUG must be False")
        if len(secret) < 50:
            failures.append("DJANGO_SECRET_KEY must be at least 50 characters")
        if not hosts:
            failures.append("DJANGO_ALLOWED_HOSTS is empty")
        if "*" in hosts:
            failures.append("DJANGO_ALLOWED_HOSTS must not contain *")
        if any(host in {"127.0.0.1", "localhost"} for host in hosts):
            warnings.append("ALLOWED_HOSTS still includes localhost/127.0.0.1")
        if not getattr(settings, "SESSION_COOKIE_SECURE", False):
            failures.append("SESSION_COOKIE_SECURE is not enabled")
        if not getattr(settings, "CSRF_COOKIE_SECURE", False):
            failures.append("CSRF_COOKIE_SECURE is not enabled")
        if not getattr(settings, "SECURE_SSL_REDIRECT", False):
            failures.append("SECURE_SSL_REDIRECT is not enabled")
        if int(getattr(settings, "SECURE_HSTS_SECONDS", 0) or 0) < 3600:
            warnings.append("HSTS is below one hour")
        if any(not value.startswith("https://") for value in origins):
            failures.append("Every CSRF trusted origin must use https://")
        if not origins:
            warnings.append("DJANGO_CSRF_TRUSTED_ORIGINS is empty; same-origin may work, but set it explicitly for the production domain")
        if not getattr(settings, "EVERAFTER_RATE_LIMIT_ENABLED", False):
            warnings.append("Rate limiting is disabled")

        for item in warnings:
            self.stdout.write(self.style.WARNING(f"WARNING: {item}"))
        if failures:
            for item in failures:
                self.stderr.write(self.style.ERROR(f"ERROR: {item}"))
            raise CommandError(f"Production security check failed with {len(failures)} error(s).")

        self.stdout.write(self.style.SUCCESS("EverVow production security check: PASS"))
