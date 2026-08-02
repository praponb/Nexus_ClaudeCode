"""Idempotency-Key support for retry-sensitive POST endpoints (D-08).

Behaviour:
- No ``Idempotency-Key`` header: the handler runs normally (header is
  recommended, not required).
- Key present and a matching record exists (same user + endpoint + key,
  younger than 24h): the original response is replayed verbatim; the handler
  never runs, so no duplicate asset/assignment/event can be created.
- Key reused with a *different* payload: 409 ``IDEMPOTENCY_KEY_REUSED``.
- Only definitive responses (<500) are persisted.
"""

import hashlib
import json
from collections.abc import Callable
from datetime import timedelta
from typing import Any

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.utils.encoders import JSONEncoder

from apps.core.exceptions import ApiException
from apps.core.models import IdempotencyRecord

IDEMPOTENCY_TTL = timedelta(hours=24)
MAX_KEY_LENGTH = 128


def _request_hash(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _json_safe(body: Any) -> Any:
    """Render a response body exactly as the API would (ISO datetimes, decimal
    strings, UUID strings) so the stored snapshot is persistable and a replay
    is byte-identical to the first response."""
    return json.loads(json.dumps(body, cls=JSONEncoder))


def run_idempotent(
    *,
    user,
    endpoint: str,
    key: str,
    request_payload: Any,
    handler: Callable[[], tuple[int, dict]],
) -> tuple[int, dict, bool]:
    """Execute ``handler`` at most once per (user, endpoint, key).

    ``handler`` returns ``(status_code, response_body)``. Returns
    ``(status_code, response_body, replayed)``.
    """
    if not key:
        raise ApiException(
            400,
            "VALIDATION_FAILED",
            "The Idempotency-Key header must not be empty.",
            field_errors={"idempotency_key": ["Provide a non-empty unique key."]},
        )
    if len(key) > MAX_KEY_LENGTH:
        raise ApiException(
            400,
            "VALIDATION_FAILED",
            "The Idempotency-Key header is too long.",
            field_errors={"idempotency_key": [f"Maximum length is {MAX_KEY_LENGTH}."]},
        )
    request_hash = _request_hash(request_payload)
    cutoff = timezone.now() - IDEMPOTENCY_TTL
    with transaction.atomic():
        record = (
            IdempotencyRecord.objects.select_for_update()
            .filter(user=user, endpoint=endpoint, key=key, created_at__gte=cutoff)
            .first()
        )
        if record is not None:
            if record.request_hash != request_hash:
                raise ApiException(
                    409,
                    "IDEMPOTENCY_KEY_REUSED",
                    "This Idempotency-Key was already used with a different request.",
                )
            return record.response_status, record.response_body, True
        status, body = handler()
        safe_body = _json_safe(body)
        if status < 500:
            try:
                IdempotencyRecord.objects.create(
                    user=user,
                    endpoint=endpoint,
                    key=key,
                    request_hash=request_hash,
                    response_status=status,
                    response_body=safe_body,
                )
            except IntegrityError:
                # Concurrent duplicate raced past the lock-free window; fetch and
                # replay the winner's record.
                record = IdempotencyRecord.objects.get(user=user, endpoint=endpoint, key=key)
                return record.response_status, record.response_body, True
        return status, safe_body, False


def idempotency_key_from(request) -> str | None:
    """Return the raw Idempotency-Key header value, or None when absent."""
    raw = request.headers.get("Idempotency-Key")
    if raw is None:
        return None
    return raw.strip()
