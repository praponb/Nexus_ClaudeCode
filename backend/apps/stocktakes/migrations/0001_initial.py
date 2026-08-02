import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("assets", "0001_initial"),
        ("reference_data", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="StocktakeSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=120)),
                ("start_at", models.DateTimeField(blank=True, null=True)),
                ("due_at", models.DateTimeField(blank=True, null=True)),
                ("snapshot_at", models.DateTimeField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("open", "Open"),
                            ("reconciling", "Reconciling"),
                            ("closed", "Closed"),
                        ],
                        default="draft",
                        max_length=16,
                    ),
                ),
                ("instructions", models.TextField(blank=True, default="")),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+", to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "locations",
                    models.ManyToManyField(
                        blank=True, related_name="+", to="reference_data.location"
                    ),
                ),
                (
                    "operators",
                    models.ManyToManyField(
                        blank=True, related_name="+", to=settings.AUTH_USER_MODEL
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="StocktakeObservation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tag_scanned", models.CharField(max_length=64)),
                ("observed_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("note", models.TextField(blank=True, default="")),
                (
                    "outcome",
                    models.CharField(
                        choices=[
                            ("found", "Found"),
                            ("not_found", "Not found"),
                            ("unexpected", "Unexpected"),
                            ("duplicate", "Duplicate scan"),
                            ("moved", "Moved"),
                            ("condition_mismatch", "Condition mismatch"),
                        ],
                        default="found",
                        max_length=32,
                    ),
                ),
                (
                    "asset",
                    models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="stocktake_observations",
                        to="assets.asset",
                    ),
                ),
                (
                    "condition",
                    models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+", to="reference_data.assetcondition",
                    ),
                ),
                (
                    "location",
                    models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+", to="reference_data.location",
                    ),
                ),
                (
                    "operator",
                    models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+", to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="observations",
                        to="stocktakes.stocktakesession",
                    ),
                ),
            ],
            options={
                "ordering": ["-observed_at", "-id"],
                "indexes": [
                    models.Index(fields=["session", "outcome"], name="stocktake_obs_outcome_idx"),
                ],
            },
        ),
    ]
