from django.conf import settings
from django.db import models

from apps.core.models import CoreModel


class ApprovalRequest(CoreModel):
    """Approval workflow request (FR-024).

    Created when a configured transition rule (requires_approval) gates a
    transfer/disposal/write-off/sensitive update. Immutable after decision:
    the approve/reject/return services reject any second decision, and the
    decision itself is recorded via lifecycle + audit events.
    """

    class RequestType(models.TextChoices):
        TRANSFER = "transfer", "Transfer"
        DISPOSAL = "disposal", "Disposal"
        WRITE_OFF = "write_off", "Write-off"
        SENSITIVE_UPDATE = "sensitive_update", "Sensitive update"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        RETURNED = "returned", "Returned"
        CANCELLED = "cancelled", "Cancelled"

    request_type = models.CharField(max_length=24, choices=RequestType.choices)
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    asset = models.ForeignKey(
        "assets.Asset", on_delete=models.PROTECT, related_name="approval_requests"
    )
    to_code = models.CharField(max_length=32, blank=True, default="")
    payload = models.JSONField(default=dict, blank=True)
    reason = models.TextField(blank=True, default="")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    comments = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"], name="approval_status_idx"),
            models.Index(fields=["asset", "status"], name="approval_asset_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.request_type} approval for {self.asset.tag} ({self.status})"
