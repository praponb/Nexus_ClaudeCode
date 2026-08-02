import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import CoreModel


class Asset(CoreModel):
    """Core inventory record. Public identity is ``uuid``; ``tag`` is the
    human-readable unique key (immutable, unique forever - BR-001)."""

    class RecordStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"

    tag = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    category = models.ForeignKey(
        "reference_data.Category", on_delete=models.PROTECT, related_name="assets"
    )
    status = models.ForeignKey(
        "reference_data.AssetStatus", on_delete=models.PROTECT, related_name="assets"
    )
    condition = models.ForeignKey(
        "reference_data.AssetCondition",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="assets",
    )
    department = models.ForeignKey(
        "reference_data.Department",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="assets",
    )
    location = models.ForeignKey(
        "reference_data.Location",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="assets",
    )
    custodian = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="custody_assets",
    )
    serial_number = models.CharField(max_length=120, blank=True, default="")
    manufacturer = models.CharField(max_length=120, blank=True, default="")
    brand = models.CharField(max_length=120, blank=True, default="")
    model = models.CharField(max_length=120, blank=True, default="")
    parent_asset = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="child_assets",
    )
    barcode_value = models.CharField(max_length=120, blank=True, default="")
    external_ids = models.JSONField(default=dict, blank=True)
    acquisition_type = models.CharField(max_length=32, blank=True, default="")
    purchase_date = models.DateField(null=True, blank=True)
    purchase_price = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    purchase_currency = models.CharField(max_length=3, blank=True, default="")
    po_reference = models.CharField(max_length=64, blank=True, default="")
    invoice_reference = models.CharField(max_length=64, blank=True, default="")
    supplier = models.ForeignKey(
        "reference_data.Supplier",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="assets",
    )
    lease_reference = models.CharField(max_length=64, blank=True, default="")
    lease_end = models.DateField(null=True, blank=True)
    warranty_provider = models.CharField(max_length=120, blank=True, default="")
    warranty_start = models.DateField(null=True, blank=True)
    warranty_end = models.DateField(null=True, blank=True)
    last_maintenance_date = models.DateField(null=True, blank=True)
    next_maintenance_due = models.DateField(null=True, blank=True)
    maintenance_interval_months = models.PositiveIntegerField(null=True, blank=True)
    hostname = models.CharField(max_length=120, blank=True, default="")
    mac_address = models.CharField(max_length=32, blank=True, default="")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    os = models.CharField(max_length=120, blank=True, default="")
    specs = models.JSONField(default=dict, blank=True)
    imei = models.CharField(max_length=32, blank=True, default="")
    license_id = models.CharField(max_length=120, blank=True, default="")
    category_attributes = models.JSONField(default=dict, blank=True)
    received_date = models.DateField(null=True, blank=True)
    in_service_date = models.DateField(null=True, blank=True)
    useful_life_end = models.DateField(null=True, blank=True)
    retirement_date = models.DateField(null=True, blank=True)
    disposal_date = models.DateField(null=True, blank=True)
    disposal_method = models.CharField(max_length=64, blank=True, default="")
    disposal_reason = models.TextField(blank=True, default="")
    data_quality_status = models.CharField(max_length=16, default="ok")
    # FR-030: legal/audit hold — set by system administrators only; any future
    # retention/purge job must skip held records.
    legal_hold = models.BooleanField(default=False)
    version = models.PositiveIntegerField(default=1)
    record_status = models.CharField(
        max_length=16,
        choices=RecordStatus.choices,
        default=RecordStatus.ACTIVE,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assets_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assets_updated",
    )

    class Meta:
        indexes = [
            models.Index(fields=["serial_number"], name="asset_serial_idx"),
            models.Index(fields=["warranty_end"], name="asset_warranty_end_idx"),
            models.Index(fields=["next_maintenance_due"], name="asset_maint_due_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(warranty_start__isnull=True)
                    | models.Q(warranty_end__isnull=True)
                    | models.Q(warranty_end__gte=models.F("warranty_start"))
                ),
                name="asset_warranty_dates_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.tag} - {self.name}"


class AssetTagSequence(CoreModel):
    """Per-prefix counter for server-side tag generation (locked increments)."""

    prefix = models.CharField(max_length=32, unique=True)
    next_value = models.BigIntegerField(default=1)

    def __str__(self) -> str:
        return f"{self.prefix} @ {self.next_value}"


class LifecycleEvent(models.Model):
    """Append-only business history for an asset (BR-003)."""

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="lifecycle_events")
    event_type = models.CharField(max_length=48)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    actor_label = models.CharField(max_length=120, blank=True, default="")
    occurred_at = models.DateTimeField(default=timezone.now)
    summary = models.CharField(max_length=255)
    details = models.JSONField(default=dict, blank=True)
    correlation_id = models.UUIDField(null=True, blank=True)

    class Meta:
        ordering = ["-occurred_at", "-id"]
        indexes = [
            models.Index(fields=["asset", "occurred_at"], name="lifecycle_asset_time_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.asset.tag}: {self.event_type} @ {self.occurred_at}"


class Attachment(CoreModel):
    """Attachment metadata (FR-015). Files live on the configured storage
    backend; downloads only via the authorized endpoint (D-04)."""

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="attachments")
    filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size = models.PositiveIntegerField()
    storage_key = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    purpose = models.CharField(max_length=64, blank=True, default="")
    scan_status = models.CharField(max_length=16, default="not_scanned")

    class Meta:
        indexes = [
            models.Index(fields=["asset"], name="attachment_asset_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.filename} on {self.asset.tag}"


class Note(CoreModel):
    """Asset note/comment (FR-016). Append-only: corrections are new notes."""

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="notes")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    body = models.TextField()

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"Note on {self.asset.tag} by {self.author}"
