"""Local development settings (used by docker compose dev stack).

The SECRET_KEY default below is a public, well-known development placeholder -
it is NOT a secret and must never be used outside local development.
"""

from config.settings.base import *  # noqa: F401,F403
from config.settings.base import env, env_list

DEBUG = True

SECRET_KEY = env("DJANGO_SECRET_KEY") or "django-insecure-local-dev-placeholder-not-a-secret"

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", ["localhost", "127.0.0.1", "backend"])

CORS_ALLOWED_ORIGINS = env_list(
    "DJANGO_CORS_ALLOWED_ORIGINS",
    ["http://localhost:3000", "http://127.0.0.1:3000"],
)
CSRF_TRUSTED_ORIGINS = env_list(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    ["http://localhost:3000", "http://127.0.0.1:3000"],
)

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

LOCAL_AUTH_ENABLED = True

REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["login"] = "1000/minute"
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["import_export"] = "1000/hour"

