import uuid

from django.conf import settings
from django.db import models


class CoreModel(models.Model):
    """Abstract base: public UUID identifier plus UTC audit timestamps."""

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class IdempotencyRecord(CoreModel):
    """Stored Idempotency-Key responses (D-08).

    Scoped per user + endpoint + key; records older than 24h are ignored
    (treated as expired). Replays return the original response verbatim;
    reusing a key with a different payload is a 409 conflict.
    """

    key = models.CharField(max_length=128)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="+",
    )
    endpoint = models.CharField(max_length=255)
    request_hash = models.CharField(max_length=64)
    response_status = models.PositiveIntegerField()
    response_body = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "endpoint", "key"],
                name="unique_idempotency_scope",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.endpoint} {self.key} ({self.user})"
