from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import CoreModel


class Assignment(CoreModel):
    """Links an asset to a custodian/destination. Exactly one active (returned_at
    IS NULL) primary assignment per asset (BR-002)."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CLOSED = "closed", "Closed"

    asset = models.ForeignKey("assets.Asset", on_delete=models.PROTECT, related_name="assignments")
    custodian = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="custody_assignments",
    )
    department = models.ForeignKey(
        "reference_data.Department",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    location = models.ForeignKey(
        "reference_data.Location",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    assigned_at = models.DateTimeField(default=timezone.now)
    expected_return_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    notes = models.TextField(blank=True, default="")
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    close_reason = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["asset"],
                condition=models.Q(returned_at__isnull=True),
                name="unique_active_assignment_per_asset",
            ),
        ]
        indexes = [
            models.Index(fields=["asset", "returned_at"], name="assignment_asset_open_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.asset.tag} -> {self.custodian or self.department or self.location}"


class TransferRecord(CoreModel):
    """Asset movement between custodians/locations/departments (FR-008)."""

    class Status(models.TextChoices):
        PENDING_APPROVAL = "pending_approval", "Pending approval"
        IN_TRANSIT = "in_transit", "In transit"
        RECEIVED = "received", "Received"
        CANCELLED = "cancelled", "Cancelled"

    asset = models.ForeignKey("assets.Asset", on_delete=models.PROTECT, related_name="transfers")
    from_custodian = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    to_custodian = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    from_location = models.ForeignKey(
        "reference_data.Location",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    to_location = models.ForeignKey(
        "reference_data.Location",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    from_department = models.ForeignKey(
        "reference_data.Department",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    to_department = models.ForeignKey(
        "reference_data.Department",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    reason = models.TextField(blank=True, default="")
    evidence = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.IN_TRANSIT)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["asset", "status"], name="transfer_asset_status_idx"),
        ]

    def __str__(self) -> str:
        return f"Transfer {self.asset.tag} ({self.status})"


class Reservation(CoreModel):
    """Time-boxed hold on an asset (FR-010). Overlap prevention is enforced at
    the service level with row locks (design section 10.1)."""

    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        CONFIRMED = "confirmed", "Confirmed"
        CHECKED_OUT = "checked_out", "Checked out"
        RETURNED = "returned", "Returned"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"

    ACTIVE_STATUSES = ("requested", "confirmed", "checked_out")

    asset = models.ForeignKey("assets.Asset", on_delete=models.PROTECT, related_name="reservations")
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    purpose = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.CONFIRMED)
    notes = models.TextField(blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["asset", "status"], name="reservation_asset_status_idx"),
        ]

    def __str__(self) -> str:
        return f"Reservation {self.asset.tag} ({self.status})"


class ExceptionReport(CoreModel):
    """Lost/stolen/missing/damaged report (FR-013). Resolution never erases the
    original event (BR-003)."""

    class ReportType(models.TextChoices):
        LOST = "lost", "Lost"
        STOLEN = "stolen", "Stolen"
        MISSING = "missing", "Missing"
        DAMAGED = "damaged", "Damaged"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        RESOLVED = "resolved", "Resolved"

    asset = models.ForeignKey(
        "assets.Asset", on_delete=models.PROTECT, related_name="exception_reports"
    )
    report_type = models.CharField(max_length=16, choices=ReportType.choices)
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    description = models.TextField(blank=True, default="")
    evidence = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    resolution = models.TextField(blank=True, default="")
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["asset", "status"], name="exception_asset_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.report_type} report on {self.asset.tag} ({self.status})"
