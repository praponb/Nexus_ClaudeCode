"""Production settings. Fails fast on missing or insecure configuration (D-13)."""

from django.core.exceptions import ImproperlyConfigured

from config.settings.base import *  # noqa: F401,F403
from config.settings.base import APP_ENV, env, env_bool, env_list

DEBUG = False

if env_bool("DJANGO_DEBUG", False):
    raise ImproperlyConfigured("DEBUG must be disabled in production settings.")

_REQUIRED_ENV = [
    "DJANGO_SECRET_KEY",
    "DJANGO_ALLOWED_HOSTS",
    "DJANGO_CORS_ALLOWED_ORIGINS",
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_HOST",
]

_missing = [name for name in _REQUIRED_ENV if not env(name)]
if _missing:
    raise ImproperlyConfigured(
        "Missing required production environment variables: " + ", ".join(_missing)
    )

SECRET_KEY = env("DJANGO_SECRET_KEY", "") or ""
if len(SECRET_KEY) < 32 or "replace-me" in SECRET_KEY or "insecure" in SECRET_KEY:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY is missing, too short, or a placeholder.")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS")
CORS_ALLOWED_ORIGINS = env_list("DJANGO_CORS_ALLOWED_ORIGINS")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

# Local (password) auth is a development convenience. In production it requires
# an explicit double opt-in so it cannot be enabled accidentally (design D-01).
LOCAL_AUTH_ENABLED = env_bool("LOCAL_AUTH_ENABLED", False)
if (
    APP_ENV == "production"
    and LOCAL_AUTH_ENABLED
    and not env_bool("LOCAL_AUTH_ALLOW_IN_PRODUCTION", False)
):
    raise ImproperlyConfigured(
        "Local password authentication is disabled in production. Use OIDC SSO, or set "
        "LOCAL_AUTH_ALLOW_IN_PRODUCTION=true to explicitly override."
    )

SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"

# Star-imported DATABASES is loosely typed; the OPTIONS dict is intentional.
DATABASES["default"]["OPTIONS"] = {  # type: ignore[assignment]  # noqa: F405
    "sslmode": env("POSTGRES_SSLMODE", "require") or "require",
}
