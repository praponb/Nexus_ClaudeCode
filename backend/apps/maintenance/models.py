from django.db import models
from django.utils import timezone

from apps.core.models import CoreModel


class MaintenanceRecord(CoreModel):
    """Typed maintenance/repair record (FR-011). The asset stays Under
    Maintenance while a record is open. ``cost`` is finance-restricted."""

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    asset = models.ForeignKey(
        "assets.Asset", on_delete=models.PROTECT, related_name="maintenance_records"
    )
    maintenance_type = models.ForeignKey(
        "reference_data.MaintenanceType",
        on_delete=models.PROTECT,
        related_name="+",
    )
    issue = models.TextField(blank=True, default="")
    provider = models.CharField(max_length=120, blank=True, default="")
    technician = models.CharField(max_length=120, blank=True, default="")
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    cost = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    cost_currency = models.CharField(max_length=3, blank=True, default="")
    result = models.TextField(blank=True, default="")
    next_due = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)

    class Meta:
        ordering = ["-started_at", "-id"]
        indexes = [
            models.Index(fields=["asset", "status"], name="maintenance_asset_status_idx"),
            models.Index(fields=["next_due"], name="maintenance_next_due_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.maintenance_type.name} on {self.asset.tag} ({self.status})"
