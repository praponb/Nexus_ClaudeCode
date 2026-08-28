"""Rate-throttle helpers (NFR-007).

DRF's ``SimpleRateThrottle`` leaves ``get_cache_key`` abstract, and
``ScopedRateThrottle`` implements it but derives the scope from the view's
``throttle_scope`` attribute — silently allowing every request when the view
does not set one. ``ScopedSimpleRateThrottle`` keeps the declarative
class-level ``scope`` while providing the cache-key behaviour.
"""

from rest_framework.throttling import SimpleRateThrottle

from apps.core.client_ip import client_ip


class ScopedSimpleRateThrottle(SimpleRateThrottle):
    """SimpleRateThrottle with a concrete per-user/per-IP cache key."""

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            # Deliberately not DRF's get_ident(): it trusts X-Forwarded-For,
            # which a caller can rotate to get a fresh bucket every request.
            # Unidentifiable clients share one bucket rather than escaping the
            # limit -- this fails closed.
            ident = client_ip(request) or "unknown"
        return self.cache_format % {"scope": self.scope, "ident": ident}
