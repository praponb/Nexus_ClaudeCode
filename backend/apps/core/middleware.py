import uuid
from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse

from apps.core.context import correlation_id_var


class CorrelationIdMiddleware:
    """Reads or generates X-Correlation-ID, exposes it on the request, echoes it back."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        raw = request.headers.get("X-Correlation-ID", "")
        correlation_id = raw.strip()
        if correlation_id:
            try:
                correlation_id = str(uuid.UUID(correlation_id))
            except ValueError:
                correlation_id = ""
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        # Attached for views/services; typed as a plain string attribute.
        request.correlation_id = correlation_id  # type: ignore[attr-defined]
        token = correlation_id_var.set(correlation_id)
        try:
            response = self.get_response(request)
        finally:
            correlation_id_var.reset(token)
        response["X-Correlation-ID"] = correlation_id
        return response


class SecurityHeadersMiddleware:
    """Defense-in-depth headers; TLS-related headers come from Django SecurityMiddleware."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        csp = getattr(settings, "CONTENT_SECURITY_POLICY", "")
        if csp:
            response.headers.setdefault("Content-Security-Policy", csp)
        return response
