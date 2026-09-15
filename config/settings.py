import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")

DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# --------------------------------------------------
# Base
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


# --------------------------------------------------
# Security
# --------------------------------------------------



DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = ["127.0.0.1", "localhost"]


# --------------------------------------------------
# Applications
# --------------------------------------------------

INSTALLED_APPS = [
    "security_hardening",
    "audit_analytics",
    "dashboard_themes",
    "modules",
    "invitation_themes",
    "photos",
    "staffing",
    "accounts",
    "weddings",
    "guests",
    "invitations",
    "event_tools",
    "transportation",
    "budgeting",
    "planner",
    "vendors",
    "financial_docs",
    "printing",
    "archive_restore",
    "integrations",
    "rsvp",
    "payment_providers",
    "gifts",
    "checkins",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]


# --------------------------------------------------
# Middleware
# --------------------------------------------------

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "security_hardening.middleware.SecurityHardeningMiddleware",
    "modules.middleware.ModuleGateMiddleware",
    "audit_analytics.middleware.AuditTrailMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# --------------------------------------------------
# URLs / Templates
# --------------------------------------------------

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "dashboard_themes.context_processors.dashboard_theme",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# --------------------------------------------------
# Database
# --------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", "5433"),
    }
}


# --------------------------------------------------
# Password validation
# --------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# --------------------------------------------------
# Internationalization
# --------------------------------------------------

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Yangon"

USE_I18N = True

USE_TZ = True


# --------------------------------------------------
# Static files
# --------------------------------------------------

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"


# --------------------------------------------------
# Email - Development only
# --------------------------------------------------

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"


AUTH_USER_MODEL = "accounts.User"


# Uploaded media - local development only
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# EverVow v12.0 - Microsoft Graph / OneDrive
GRAPH_TENANT_ID = os.getenv("GRAPH_TENANT_ID", "")
GRAPH_CLIENT_ID = os.getenv("GRAPH_CLIENT_ID", "")
GRAPH_CLIENT_SECRET = os.getenv("GRAPH_CLIENT_SECRET", "")
GRAPH_DRIVE_ID = os.getenv("GRAPH_DRIVE_ID", "")
GRAPH_ROOT_FOLDER = os.getenv("GRAPH_ROOT_FOLDER", "EverVow")
GRAPH_TIMEOUT_SECONDS = int(os.getenv("GRAPH_TIMEOUT_SECONDS", "20"))


# EverVow v13.0 - Archive & Restore
# Safety ceiling for one synchronous archive build. Set 0 to disable the ceiling.
EVERAFTER_ARCHIVE_MAX_BYTES = int(os.getenv("EVERAFTER_ARCHIVE_MAX_BYTES", str(512 * 1024 * 1024)))


# EverVow v14.0 - Security & Production Hardening
# Production hardening is intentionally opt-in. Local development stays unchanged
# until EVERAFTER_PRODUCTION=True is configured in the deployment environment.
def _ea_env_bool(name, default=False):
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _ea_csv(name, default=""):
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


EVERAFTER_PRODUCTION = _ea_env_bool("EVERAFTER_PRODUCTION", False)
EVERAFTER_TRUST_PROXY = _ea_env_bool("EVERAFTER_TRUST_PROXY", False)
EVERAFTER_RATE_LIMIT_ENABLED = _ea_env_bool("EVERAFTER_RATE_LIMIT_ENABLED", True)
EVERAFTER_LOGIN_LIMIT = int(os.getenv("EVERAFTER_LOGIN_LIMIT", "12"))
EVERAFTER_PUBLIC_READ_LIMIT = int(os.getenv("EVERAFTER_PUBLIC_READ_LIMIT", "240"))
EVERAFTER_PUBLIC_WRITE_LIMIT = int(os.getenv("EVERAFTER_PUBLIC_WRITE_LIMIT", "60"))
EVERAFTER_AGENT_LIMIT = int(os.getenv("EVERAFTER_AGENT_LIMIT", "600"))

if "CACHES" not in globals():
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "everafter-security",
        }
    }

# Safe in both development and production.
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
FILE_UPLOAD_PERMISSIONS = 0o640
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o750
DATA_UPLOAD_MAX_NUMBER_FIELDS = int(os.getenv("EVERAFTER_MAX_FORM_FIELDS", "2000"))
DATA_UPLOAD_MAX_NUMBER_FILES = int(os.getenv("EVERAFTER_MAX_UPLOAD_FILES", "50"))
FILE_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv("EVERAFTER_UPLOAD_MEMORY_BYTES", str(5 * 1024 * 1024)))

# Explicit host/origin configuration can also be used in development when needed.
if not EVERAFTER_PRODUCTION:
    ALLOWED_HOSTS = _ea_csv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost")
    CSRF_TRUSTED_ORIGINS = _ea_csv("DJANGO_CSRF_TRUSTED_ORIGINS", "")

if EVERAFTER_PRODUCTION:
    from django.core.exceptions import ImproperlyConfigured

    DEBUG = False
    _production_secret = os.getenv("DJANGO_SECRET_KEY", "").strip()
    if len(_production_secret) < 50:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY must be at least 50 characters in production.")
    SECRET_KEY = _production_secret

    ALLOWED_HOSTS = _ea_csv("DJANGO_ALLOWED_HOSTS", "")
    if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
        raise ImproperlyConfigured("Set explicit DJANGO_ALLOWED_HOSTS for production; wildcard hosts are not allowed.")

    CSRF_TRUSTED_ORIGINS = _ea_csv("DJANGO_CSRF_TRUSTED_ORIGINS", "")
    if any(not origin.startswith("https://") for origin in CSRF_TRUSTED_ORIGINS):
        raise ImproperlyConfigured("Production CSRF trusted origins must use https://.")

    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = _ea_env_bool("EVERAFTER_SSL_REDIRECT", True)
    SECURE_HSTS_SECONDS = int(os.getenv("EVERAFTER_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = _ea_env_bool("EVERAFTER_HSTS_INCLUDE_SUBDOMAINS", True)
    SECURE_HSTS_PRELOAD = _ea_env_bool("EVERAFTER_HSTS_PRELOAD", False)

    if EVERAFTER_TRUST_PROXY:
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
        USE_X_FORWARDED_HOST = _ea_env_bool("EVERAFTER_USE_X_FORWARDED_HOST", False)

    # Persistent PostgreSQL connections reduce connection churn under WSGI workers.
    DATABASES["default"]["CONN_MAX_AGE"] = int(os.getenv("DB_CONN_MAX_AGE", "60"))
    DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

# Security events intentionally omit raw IP addresses and request bodies.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "everafter": {
            "format": "{asctime} {levelname} {name} {message}",
            "style": "{",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "everafter",
        }
    },
    "loggers": {
        "everafter.security": {
            "handlers": ["console"],
            "level": os.getenv("EVERAFTER_SECURITY_LOG_LEVEL", "WARNING"),
            "propagate": False,
        }
    },
}
# EverVow v14.1.1 - Auth flow
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

# EverVow v14.1.5 - image originals on OneDrive; VPS caches thumbnails only
EVERVOW_THUMBNAIL_CACHE_ROOT = Path(os.getenv("EVERVOW_THUMBNAIL_CACHE_ROOT", os.getenv("EVERAFTER_THUMBNAIL_CACHE_ROOT", str(BASE_DIR / "media_cache"))))
# Backward-compatible alias for installs that still reference the pre-rebrand setting.
EVERAFTER_THUMBNAIL_CACHE_ROOT = EVERVOW_THUMBNAIL_CACHE_ROOT
