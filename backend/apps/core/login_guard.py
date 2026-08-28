"""Per-username failed-login lockout (NFR-007, design section 12).

``LoginThrottle`` buckets by client IP, which stops one host guessing quickly
but does nothing about a distributed attack: N hosts get N x the per-IP budget
against a single account. This module adds the missing axis -- a counter keyed
on the *username being attempted*, so the total number of guesses against one
account is bounded no matter how many addresses they come from.

Failures only. A successful sign-in clears the counter, so ordinary users who
mistype a password once are never affected, and the shared public demo account
is never penalised for the traffic it is there to serve.

Counters live in the default cache (Redis in compose/production), so they are
shared across gunicorn workers and expire on their own.

Trade-off, deliberately accepted: because attempts are counted for *any*
username -- existing or not, which is what stops the lockout from leaking which
accounts exist -- anyone who learns a username can keep that account locked by
failing on it. The window is therefore short and configurable, exempt usernames
are supported, and ``reset()`` gives an operator an immediate unlock:

    docker compose exec backend python -c "
    import django; django.setup()
    from apps.core.login_guard import reset; reset('<username>')"
"""

import hashlib

from django.conf import settings
from django.core.cache import cache

CACHE_PREFIX = "login-fail"


def _normalize(username: str) -> str:
    return (username or "").strip().lower()


def _cache_key(username: str) -> str:
    # Hashed rather than interpolated raw: usernames are attacker-supplied, and
    # a raw value would put arbitrary text (spaces, control chars, unbounded
    # length) straight into a cache key.
    digest = hashlib.sha256(_normalize(username).encode("utf-8")).hexdigest()
    return f"{CACHE_PREFIX}:{digest[:32]}"


def _threshold() -> int:
    return int(getattr(settings, "LOGIN_LOCKOUT_THRESHOLD", 10) or 10)


def _window_seconds() -> int:
    return int(getattr(settings, "LOGIN_LOCKOUT_WINDOW_SECONDS", 900) or 900)


def is_exempt(username: str) -> bool:
    """True for accounts that must never be lockable.

    The public demo account is exempt by design: its password is published, so
    there is nothing to protect, and locking it would deny every visitor at once.
    """
    exempt = {_normalize(name) for name in getattr(settings, "LOGIN_LOCKOUT_EXEMPT_USERNAMES", [])}
    return _normalize(username) in exempt


def failure_count(username: str) -> int:
    if is_exempt(username):
        return 0
    return int(cache.get(_cache_key(username)) or 0)


def is_locked(username: str) -> bool:
    if is_exempt(username):
        return False
    return failure_count(username) >= _threshold()


def record_failure(username: str) -> int:
    """Count one failed attempt; returns the new total for this window."""
    if is_exempt(username):
        return 0
    key = _cache_key(username)
    # `add` only succeeds when the key is absent, which starts a fixed window.
    # `incr` deliberately does not extend the TTL, so the window runs from the
    # first failure rather than sliding forward with every further attempt.
    if cache.add(key, 1, timeout=_window_seconds()):
        return 1
    try:
        return int(cache.incr(key))
    except ValueError:
        # Expired between the add and the incr.
        cache.set(key, 1, timeout=_window_seconds())
        return 1


def reset(username: str) -> None:
    """Clear the counter -- on successful sign-in, or as an operator unlock."""
    cache.delete(_cache_key(username))
