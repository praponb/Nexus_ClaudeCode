"""Audit recording service (FR-025).

Explicit service calls only - never model signals (stack section 7.4).
Appends are serialized by locking the current chain tail row.
"""

import hashlib
import json
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditEvent


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))


def _compute_hash(prev_hash: str, payload: dict) -> str:
    material = prev_hash + "|" + _canonical(payload)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _payload_for(event: AuditEvent) -> dict:
    return {
        "prev_hash": event.prev_hash,
        "actor": str(event.actor.uuid) if event.actor else None,
        "actor_type": event.actor_type,
        "action": event.action,
        "target_type": event.target_type,
        "target_uuid": str(event.target_uuid) if event.target_uuid else None,
        "before": event.before,
        "after": event.after,
        "outcome": event.outcome,
        "correlation_id": str(event.correlation_id) if event.correlation_id else None,
        "created_at": event.created_at.isoformat(),
    }


def record_audit(
    *,
    actor=None,
    action: str,
    target=None,
    before: dict | None = None,
    after: dict | None = None,
    outcome: str = "success",
    correlation_id=None,
    ip_address: str | None = None,
    actor_type: str = "user",
) -> AuditEvent:
    target_type = ""
    target_uuid = None
    if target is not None:
        target_type = target._meta.label_lower
        target_uuid = target.uuid
    with transaction.atomic():
        last = AuditEvent.objects.select_for_update().order_by("-id").first()
        prev_hash = last.record_hash if last is not None else ""
        event = AuditEvent(
            actor=actor,
            actor_type=actor_type,
            action=action,
            target_type=target_type,
            target_uuid=target_uuid,
            before=before,
            after=after,
            outcome=outcome,
            correlation_id=correlation_id,
            ip_address=ip_address,
            created_at=timezone.now(),
            prev_hash=prev_hash,
        )
        event.record_hash = _compute_hash(prev_hash, _payload_for(event))
        event.save()
    return event


def verify_chain() -> bool:
    """Recompute the hash chain; returns False if any record was tampered with."""
    prev_hash = ""
    for event in AuditEvent.objects.order_by("id"):
        if event.prev_hash != prev_hash:
            return False
        if event.record_hash != _compute_hash(prev_hash, _payload_for(event)):
            return False
        prev_hash = event.record_hash
    return True
