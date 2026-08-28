"""Base settings for the Asset Inventory backend.

All environment-specific behaviour is driven by environment variables. See
``backend/.env`` for the full variable reference (checked-in placeholders
only). Never commit real secrets.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def env(key: str, default: str | None = None) -> str | None:
    return os.environ.get(key, default)


def env_bool(key: str, default: bool = False) -> bool:
    value = os.environ.get(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(key: str, default: list[str] | None = None) -> list[str]:
    value = os.environ.get(key)
    if value is None:
        return list(default or [])
    return [item.strip() for item in value.split(",") if item.strip()]


APP_ENV = env("APP_ENV", "local")
APP_BASE_URL = env("APP_BASE_URL", "http://localhost:3000")
SECRET_KEY = env("DJANGO_SECRET_KEY") or env("SECRET_KEY") or "local-dev-only-not-a-secret"
DEBUG = env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", ["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_filters",
    "corsheaders",
    "drf_spectacular",
    "apps.core",
    "apps.accounts",
    "apps.reference_data",
    "apps.assets",
    "apps.assignments",
    "apps.maintenance",
    "apps.stocktakes",
    "apps.bulk",
    "apps.approvals",
    "apps.notifications",
    "apps.audit",
    "apps.reporting",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.core.middleware.CorrelationIdMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.SecurityHeadersMiddleware",
]

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
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", "asset_inventory"),
        "USER": env("POSTGRES_USER", "asset_inventory"),
        "PASSWORD": env("POSTGRES_PASSWORD", ""),
        "HOST": env("POSTGRES_HOST", "localhost"),
        "PORT": env("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 60,
    }
}

AUTH_USER_MODEL = "accounts.User"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Local (session-cookie) authentication is the v1 dev/test mode (design D-01).
# Production must use OIDC SSO; local auth is hard-disabled there unless both
# LOCAL_AUTH_ENABLED=true and LOCAL_AUTH_ALLOW_IN_PRODUCTION=true are set.
LOCAL_AUTH_ENABLED = env_bool("LOCAL_AUTH_ENABLED", APP_ENV != "production")

# Approval workflows (FR-024, A-05): configurable; ship enabled with
# separation-of-duties on. Simple organizations may disable them entirely;
# with approvals disabled, transition rules never hold actions for review.
APPROVALS_ENABLED = env_bool("APPROVALS_ENABLED", True)
APPROVAL_SEPARATION_OF_DUTIES = env_bool("APPROVAL_SEPARATION_OF_DUTIES", True)

# Notifications (FR-023): email is sent only when SMTP is configured; in-app
# notifications are always recorded. Failures are logged without content.
EMAIL_HOST = env("EMAIL_HOST", "")
EMAIL_PORT = int(env("EMAIL_PORT", "587") or "587")
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "asset-inventory@localhost")

# Retention (FR-030): business records are never physically deleted; this is
# the documented retention horizon for archived records (no purge in v1).
ARCHIVE_RETENTION_DAYS = int(env("ARCHIVE_RETENTION_DAYS", "2555") or "2555")

# Session policy: 30-minute idle timeout with sliding renewal (design section 12).
SESSION_COOKIE_AGE = int(env("SESSION_IDLE_SECONDS", "1800") or "1800")
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

CORS_ALLOWED_ORIGINS = env_list("DJANGO_CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = True
# The frontend's useApi composable sends these custom headers: X-Correlation-ID
# on every request, Idempotency-Key on unsafe retry-sensitive POSTs (design
# D-08), and If-Match on asset updates (optimistic concurrency, BR-009).
# Without them explicitly allowed, the browser's CORS preflight rejects the
# request before it ever reaches Django, surfacing to the user as a generic
# "network error" even though the server itself is healthy and reachable.
from corsheaders.defaults import default_headers as _cors_default_headers  # noqa: E402

CORS_ALLOW_HEADERS = (
    *_cors_default_headers,
    "x-correlation-id",
    "idempotency-key",
    "if-match",
)

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Attachments (D-04): metadata in PostgreSQL; files on local media volume in
# dev/test, S3-compatible storage in production via django-storages. Direct
# URLs are never exposed; downloads go through the authorized endpoint.
MEDIA_ROOT: str = env("MEDIA_ROOT") or str(BASE_DIR / "media")
ATTACHMENT_MAX_BYTES = int(env("ATTACHMENT_MAX_BYTES", str(10 * 1024 * 1024)) or "10485760")
ATTACHMENT_ALLOWED_EXTENSIONS = env_list(
    "ATTACHMENT_ALLOWED_EXTENSIONS",
    ["pdf", "png", "jpg", "jpeg", "gif", "webp", "txt", "csv", "docx", "xlsx"],
)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CONTENT_SECURITY_POLICY = env(
    "CONTENT_SECURITY_POLICY",
    "default-src 'self'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'",
)

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardPagination",
    "PAGE_SIZE": 25,
    "EXCEPTION_HANDLER": "apps.core.exceptions.exception_handler",
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
        "rest_framework.filters.SearchFilter",
    ],
    # Free-text search is `?q=` everywhere in this system -- the global search
    # endpoint (`GET /search/assets/?q=`), the asset register's shareable URL,
    # and saved-view configs all use it. Without this override SearchFilter
    # would listen on its default `?search=` instead and silently ignore `q`,
    # returning an unfiltered list rather than an error.
    "SEARCH_PARAM": "q",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # Production-safe defaults. local.py and test.py deliberately raise these
    # ceilings for developer convenience -- do NOT copy those dev values back
    # here: a permissive rate in base.py silently disables brute-force
    # protection in production while making the overrides look like no-ops.
    "DEFAULT_THROTTLE_RATES": {
        "login": "10/minute",
        "import_export": "60/hour",
        "search": "120/minute",
    },
}

# META key of a client-IP header the edge OVERWRITES on every request, used to
# identify callers for throttling and audit. Empty means "trust nothing but
# REMOTE_ADDR". Behind Cloudflare this is HTTP_CF_CONNECTING_IP; never point it
# at HTTP_X_FORWARDED_FOR, which is caller-supplied. See apps/core/client_ip.py.
TRUSTED_CLIENT_IP_HEADER = env("TRUSTED_CLIENT_IP_HEADER", "") or ""

SPECTACULAR_SETTINGS = {
    "TITLE": "Asset Inventory API",
    "DESCRIPTION": "Versioned REST API for the Asset Inventory Web Application.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SERVE_PERMISSIONS": ["rest_framework.permissions.IsAuthenticated"],
    "COMPONENT_SPLIT_REQUEST": True,
}

LOG_LEVEL = env("LOG_LEVEL", "INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {"()": "apps.core.logging.JsonFormatter"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "json"},
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
}

# Cache. DRF's throttles store their counters in the *default* cache, so this
# is what makes rate limiting real (design section 12: "Rate limiting
# (Redis-backed)"). Django's implicit default is LocMemCache, which is
# per-process and lost on restart -- under the production image's
# `gunicorn --workers 3` that silently triples every configured rate and
# resets it on each deploy. Redis db 3: 1 and 2 are the Celery broker/results.
CACHE_URL = env("CACHE_URL") or "redis://localhost:6379/3"
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": CACHE_URL,
    },
}

# Celery (Cycle 2+ background jobs: import/export commit, notifications).
CELERY_BROKER_URL = env("CELERY_BROKER_URL") or env("REDIS_URL") or "redis://localhost:6379/1"
CELERY_RESULT_BACKEND = (
    env("CELERY_RESULT_BACKEND") or env("REDIS_URL") or "redis://localhost:6379/2"
)
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", APP_ENV == "local")
