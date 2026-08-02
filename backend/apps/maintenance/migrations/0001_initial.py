import uuid

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("assets", "0001_initial"),
        ("reference_data", "0002_maintenance_type"),
    ]

    operations = [
        migrations.CreateModel(
            name="MaintenanceRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("issue", models.TextField(blank=True, default="")),
                ("provider", models.CharField(blank=True, default="", max_length=120)),
                ("technician", models.CharField(blank=True, default="", max_length=120)),
                ("started_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("cost", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ("cost_currency", models.CharField(blank=True, default="", max_length=3)),
                ("result", models.TextField(blank=True, default="")),
                ("next_due", models.DateField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("open", "Open"), ("completed", "Completed"), ("cancelled", "Cancelled")],
                        default="open",
                        max_length=16,
                    ),
                ),
                (
                    "asset",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="maintenance_records",
                        to="assets.asset",
                    ),
                ),
                (
                    "maintenance_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="reference_data.maintenancetype",
                    ),
                ),
            ],
            options={
                "ordering": ["-started_at", "-id"],
                "indexes": [
                    models.Index(fields=["asset", "status"], name="maintenance_asset_status_idx"),
                    models.Index(fields=["next_due"], name="maintenance_next_due_idx"),
                ],
            },
        ),
    ]
