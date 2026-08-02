import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("reference_data", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Asset",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tag", models.CharField(max_length=64, unique=True)),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True, default="")),
                ("serial_number", models.CharField(blank=True, default="", max_length=120)),
                ("manufacturer", models.CharField(blank=True, default="", max_length=120)),
                ("brand", models.CharField(blank=True, default="", max_length=120)),
                ("model", models.CharField(blank=True, default="", max_length=120)),
                ("barcode_value", models.CharField(blank=True, default="", max_length=120)),
                ("external_ids", models.JSONField(blank=True, default=dict)),
                ("acquisition_type", models.CharField(blank=True, default="", max_length=32)),
                ("purchase_date", models.DateField(blank=True, null=True)),
                ("purchase_price", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ("purchase_currency", models.CharField(blank=True, default="", max_length=3)),
                ("po_reference", models.CharField(blank=True, default="", max_length=64)),
                ("invoice_reference", models.CharField(blank=True, default="", max_length=64)),
                ("lease_reference", models.CharField(blank=True, default="", max_length=64)),
                ("lease_end", models.DateField(blank=True, null=True)),
                ("warranty_provider", models.CharField(blank=True, default="", max_length=120)),
                ("warranty_start", models.DateField(blank=True, null=True)),
                ("warranty_end", models.DateField(blank=True, null=True)),
                ("last_maintenance_date", models.DateField(blank=True, null=True)),
                ("next_maintenance_due", models.DateField(blank=True, null=True)),
                ("maintenance_interval_months", models.PositiveIntegerField(blank=True, null=True)),
                ("hostname", models.CharField(blank=True, default="", max_length=120)),
                ("mac_address", models.CharField(blank=True, default="", max_length=32)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("os", models.CharField(blank=True, default="", max_length=120)),
                ("specs", models.JSONField(blank=True, default=dict)),
                ("imei", models.CharField(blank=True, default="", max_length=32)),
                ("license_id", models.CharField(blank=True, default="", max_length=120)),
                ("category_attributes", models.JSONField(blank=True, default=dict)),
                ("received_date", models.DateField(blank=True, null=True)),
                ("in_service_date", models.DateField(blank=True, null=True)),
                ("useful_life_end", models.DateField(blank=True, null=True)),
                ("retirement_date", models.DateField(blank=True, null=True)),
                ("disposal_date", models.DateField(blank=True, null=True)),
                ("disposal_method", models.CharField(blank=True, default="", max_length=64)),
                ("disposal_reason", models.TextField(blank=True, default="")),
                ("data_quality_status", models.CharField(default="ok", max_length=16)),
                ("version", models.PositiveIntegerField(default=1)),
                (
                    "record_status",
                    models.CharField(
                        choices=[("active", "Active"), ("archived", "Archived")],
                        default="active",
                        max_length=16,
                    ),
                ),
                (
                    "category",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="assets",
                        to="reference_data.category",
                    ),
                ),
                (
                    "condition",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="assets",
                        to="reference_data.assetcondition",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="assets_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "custodian",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="custody_assets",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "department",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="assets",
                        to="reference_data.department",
                    ),
                ),
                (
                    "location",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="assets",
                        to="reference_data.location",
                    ),
                ),
                (
                    "parent_asset",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="child_assets",
                        to="assets.asset",
                    ),
                ),
                (
                    "status",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="assets",
                        to="reference_data.assetstatus",
                    ),
                ),
                (
                    "supplier",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="assets",
                        to="reference_data.supplier",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="assets_updated",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["serial_number"], name="asset_serial_idx"),
                    models.Index(fields=["warranty_end"], name="asset_warranty_end_idx"),
                    models.Index(fields=["next_maintenance_due"], name="asset_maint_due_idx"),
                ],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(
                            ("warranty_start__isnull", True),
                            ("warranty_end__isnull", True),
                            ("warranty_end__gte", models.F("warranty_start")),
                            _connector="OR",
                        ),
                        name="asset_warranty_dates_valid",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="AssetTagSequence",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("prefix", models.CharField(max_length=32, unique=True)),
                ("next_value", models.BigIntegerField(default=1)),
            ],
        ),
        migrations.CreateModel(
            name="LifecycleEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("event_type", models.CharField(max_length=48)),
                ("actor_label", models.CharField(blank=True, default="", max_length=120)),
                ("occurred_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("summary", models.CharField(max_length=255)),
                ("details", models.JSONField(blank=True, default=dict)),
                ("correlation_id", models.UUIDField(blank=True, null=True)),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "asset",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lifecycle_events",
                        to="assets.asset",
                    ),
                ),
            ],
            options={
                "ordering": ["-occurred_at", "-id"],
                "indexes": [
                    models.Index(fields=["asset", "occurred_at"], name="lifecycle_asset_time_idx"),
                ],
            },
        ),
    ]
