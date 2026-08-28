"""Trusted client-IP resolution for throttling and audit (NFR-007).

``X-Forwarded-For`` is client-supplied: whatever a caller prepends survives to
the origin, because nothing here can distinguish an edge-appended hop from a
forged one. Two things were trusting it anyway:

* DRF's ``BaseThrottle.get_ident`` falls back to the *entire* X-Forwarded-For
  string when ``NUM_PROXIES`` is unset, so varying that header handed out a
  fresh throttle bucket per request and defeated the login rate limit outright.
* The same value was written to ``AuditEvent.ip_address``, a PostgreSQL
  ``inet`` column, so a non-IP value raised ``DataError`` -- an unauthenticated
  500 on the login endpoint.

Resolution order here is: one explicitly trusted header, then ``REMOTE_ADDR``.
Set ``TRUSTED_CLIENT_IP_HEADER`` to the META key the edge *overwrites* on every
request (``HTTP_CF_CONNECTING_IP`` behind Cloudflare); leave it empty when the
app is reached directly. The result is always a syntactically valid IP or
``None``, never caller-controlled free text.
"""

import ipaddress

from django.conf import settings


def client_ip(request) -> str | None:
    """Best trustworthy client IP for ``request``, or None if there isn't one."""
    header = getattr(settings, "TRUSTED_CLIENT_IP_HEADER", "") or ""
    candidates = []
    if header:
        candidates.append(request.META.get(header))
    candidates.append(request.META.get("REMOTE_ADDR"))

    for candidate in candidates:
        if not candidate:
            continue
        value = str(candidate).strip()
        try:
            ipaddress.ip_address(value)
        except ValueError:
            continue
        return value
    return None
