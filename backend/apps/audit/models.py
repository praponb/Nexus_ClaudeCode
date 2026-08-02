import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class AuditEvent(models.Model):
    """Append-only, tamper-evident audit record (FR-025).

    ``record_hash`` chains to ``prev_hash`` so modification of earlier rows is
    detectable. Application code never updates or deletes these rows; database
    roles in production additionally revoke UPDATE/DELETE on this table.
    """

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    actor_type = models.CharField(max_length=16, default="user")
    action = models.CharField(max_length=64)
    target_type = models.CharField(max_length=64, blank=True, default="")
    target_uuid = models.UUIDField(null=True, blank=True)
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)
    outcome = models.CharField(max_length=16, default="success")
    correlation_id = models.UUIDField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    prev_hash = models.CharField(max_length=64, blank=True, default="")
    record_hash = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(fields=["target_type", "target_uuid"], name="audit_target_idx"),
            models.Index(fields=["correlation_id"], name="audit_correlation_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.action} by {self.actor or self.actor_type} @ {self.created_at}"
