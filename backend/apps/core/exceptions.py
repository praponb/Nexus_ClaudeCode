"""Uniform API error envelope (design section 11.2).

Every non-2xx API response has the shape::

    {"error": {"code": ..., "message": ..., "field_errors": {...},
               "correlation_id": ..., "retryable": bool}}
"""

import logging
from typing import Any

from django.conf import settings
from django.http import Http404
from rest_framework import exceptions as drf_exceptions
from rest_framework.response import Response

from apps.core.context import correlation_id_var

logger = logging.getLogger("api.errors")


class ApiException(Exception):
    """Domain/business exception rendered as a stable error envelope."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        field_errors: dict[str, list[str]] | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.field_errors = field_errors or {}
        self.retryable = retryable


def envelope(
    code: str,
    message: str,
    field_errors: dict[str, list[str]] | None = None,
    retryable: bool = False,
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "field_errors": field_errors or {},
            "correlation_id": correlation_id_var.get(None),
            "retryable": retryable,
        }
    }


def _normalize_validation_detail(detail: Any, prefix: str = "") -> dict[str, list[str]]:
    """Flatten DRF validation detail into ``{field: [message, ...]}``.

    DRF errors can nest arbitrarily (e.g. a serializer raising
    ``{"category_attributes": {"ram_gb": [...]}}`` for per-category dynamic
    fields). A single level of dict/list handling would ``str()`` that
    nested dict wholesale, leaking a raw Python repr (including
    ``ErrorDetail(...)``) straight into the API response. Recurse instead,
    joining keys with ``.`` (e.g. ``category_attributes.ram_gb``).
    """
    normalized: dict[str, list[str]] = {}
    if isinstance(detail, dict):
        for field, messages in detail.items():
            key = f"{prefix}.{field}" if prefix else str(field)
            if isinstance(messages, dict):
                normalized.update(_normalize_validation_detail(messages, key))
            elif isinstance(messages, list | tuple):
                normalized[key] = [str(message) for message in messages]
            else:
                normalized[key] = [str(messages)]
        return normalized
    key = prefix or "non_field_errors"
    if isinstance(detail, list | tuple):
        return {key: [str(message) for message in detail]}
    return {key: [str(detail)]}


def exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    if isinstance(exc, ApiException):
        return Response(
            envelope(exc.code, exc.message, exc.field_errors, exc.retryable),
            status=exc.status_code,
        )
    if isinstance(exc, drf_exceptions.ValidationError):
        return Response(
            envelope(
                "VALIDATION_FAILED",
                "One or more fields failed validation.",
                _normalize_validation_detail(exc.detail),
            ),
            status=400,
        )
    if isinstance(exc, drf_exceptions.NotAuthenticated | drf_exceptions.AuthenticationFailed):
        return Response(
            envelope("AUTHENTICATION_REQUIRED", "Authentication is required."),
            status=401,
        )
    if isinstance(exc, drf_exceptions.PermissionDenied):
        return Response(
            envelope("PERMISSION_DENIED", "You do not have permission to perform this action."),
            status=403,
        )
    if isinstance(exc, drf_exceptions.NotFound | Http404):
        return Response(
            envelope("NOT_FOUND", "The requested resource was not found."),
            status=404,
        )
    if isinstance(exc, drf_exceptions.MethodNotAllowed):
        return Response(
            envelope("METHOD_NOT_ALLOWED", "This method is not allowed on the resource."),
            status=405,
        )
    if isinstance(exc, drf_exceptions.UnsupportedMediaType):
        return Response(
            envelope("UNSUPPORTED_MEDIA_TYPE", "Unsupported media type."),
            status=415,
        )
    if isinstance(exc, drf_exceptions.Throttled):
        headers = {"Retry-After": str(exc.wait)} if exc.wait else {}
        return Response(
            envelope("RATE_LIMITED", "Too many requests. Please retry later.", retryable=True),
            status=429,
            headers=headers,
        )
    if isinstance(exc, drf_exceptions.APIException):
        return Response(
            envelope("API_ERROR", "The request could not be processed."),
            status=exc.status_code,
        )
    # Unexpected exception: never leak stack traces to clients (NFR-007).
    logger.exception("Unhandled exception while processing API request")
    if settings.DEBUG:
        return None  # let Django render its debug page during local development
    return Response(
        envelope("INTERNAL_ERROR", "An unexpected error occurred. Please contact support."),
        status=500,
    )
