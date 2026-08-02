from django.conf import settings
from django.db import models

from apps.core.models import CoreModel


class Notification(CoreModel):
    """In-app notification (FR-023). ``dedupe_key`` prevents duplicate unread
    notifications for the same event (partial unique constraint)."""

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    type = models.CharField(max_length=48)
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True, default="")
    link = models.CharField(max_length=255, blank=True, default="")
    read_at = models.DateTimeField(null=True, blank=True)
    dedupe_key = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["recipient", "dedupe_key"],
                condition=models.Q(read_at__isnull=True) & ~models.Q(dedupe_key=""),
                name="unique_unread_dedupe_notification",
            ),
        ]
        indexes = [
            models.Index(fields=["recipient", "read_at"], name="notif_recipient_read_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.type} -> {self.recipient} ({'read' if self.read_at else 'unread'})"


class NotificationPreference(CoreModel):
    """Per-user preference: optional event types the user has muted.
    Mandatory compliance types cannot be muted (FR-023)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preference",
    )
    muted_types = models.JSONField(default=list, blank=True)

    def __str__(self) -> str:
        return f"Preferences for {self.user}"
