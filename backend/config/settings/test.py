"""Settings for the automated test suite (CI / pytest).

The SECRET_KEY below is an explicit non-secret test placeholder.

Database selection: compose/CI provide explicit ``POSTGRES_*`` variables. On a
bare developer machine without env vars, fall back to the local PostgreSQL
superuser role matching the current OS user (the Homebrew/Linux default) so
``pytest`` works against a stock local PostgreSQL install.
"""

import getpass

from config.settings.base import *  # noqa: F401,F403
from config.settings.base import DATABASES, REST_FRAMEWORK, env

DEBUG = False
SECRET_KEY = env("DJANGO_SECRET_KEY") or "insecure-test-placeholder-not-a-secret"

LOCAL_AUTH_ENABLED = True

if not env("POSTGRES_USER"):
    DATABASES["default"]["USER"] = getpass.getuser()
    DATABASES["default"]["PASSWORD"] = ""

# Fast, deterministic password hashing in tests.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

# Raise throttle ceilings so functional tests are not rate-limited; dedicated
# tests patch the throttle classes directly to verify throttling behaviour.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_RATES": {"login": "1000/minute", "import_export": "1000/hour"},
}

CELERY_TASK_ALWAYS_EAGER = True
