"""Rate-throttle helpers (NFR-007).

DRF's ``SimpleRateThrottle`` leaves ``get_cache_key`` abstract, and
``ScopedRateThrottle`` implements it but derives the scope from the view's
``throttle_scope`` attribute — silently allowing every request when the view
does not set one. ``ScopedSimpleRateThrottle`` keeps the declarative
class-level ``scope`` while providing the cache-key behaviour.
"""

from rest_framework.throttling import SimpleRateThrottle


class ScopedSimpleRateThrottle(SimpleRateThrottle):
    """SimpleRateThrottle with a concrete per-user/per-IP cache key."""

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}
