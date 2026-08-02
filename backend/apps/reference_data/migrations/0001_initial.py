import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AssetCondition",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("code", models.CharField(max_length=32, unique=True)),
                ("label", models.CharField(max_length=64)),
                ("icon", models.CharField(blank=True, default="", max_length=64)),
                ("semantic_treatment", models.CharField(default="neutral", max_length=32)),
                ("active", models.BooleanField(default=True)),
                ("sort_order", models.IntegerField(default=0)),
            ],
            options={"ordering": ["sort_order", "code"]},
        ),
        migrations.CreateModel(
            name="AssetStatus",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("code", models.CharField(max_length=32, unique=True)),
                ("label", models.CharField(max_length=64)),
                ("icon", models.CharField(blank=True, default="", max_length=64)),
                ("semantic_treatment", models.CharField(default="neutral", max_length=32)),
                ("is_terminal", models.BooleanField(default=False)),
                ("active", models.BooleanField(default=True)),
                ("sort_order", models.IntegerField(default=0)),
            ],
            options={"ordering": ["sort_order", "code"]},
        ),
        migrations.CreateModel(
            name="Category",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=120)),
                ("code", models.CharField(max_length=32, unique=True)),
                ("description", models.TextField(blank=True, default="")),
                ("active", models.BooleanField(default=True)),
                (
                    "parent",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="children",
                        to="reference_data.category",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="CostCenter",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=120)),
                ("code", models.CharField(max_length=32, unique=True)),
                ("description", models.TextField(blank=True, default="")),
                ("active", models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name="Department",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=120)),
                ("code", models.CharField(max_length=32, unique=True)),
                ("description", models.TextField(blank=True, default="")),
                ("active", models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name="Location",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=120)),
                ("code", models.CharField(max_length=32, unique=True)),
                ("site", models.CharField(blank=True, default="", max_length=120)),
                ("building", models.CharField(blank=True, default="", max_length=64)),
                ("floor", models.CharField(blank=True, default="", max_length=64)),
                ("room", models.CharField(blank=True, default="", max_length=64)),
                ("active", models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name="Supplier",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=120)),
                ("code", models.CharField(max_length=32, unique=True)),
                ("description", models.TextField(blank=True, default="")),
                ("contact_email", models.EmailField(blank=True, default="", max_length=254)),
                ("active", models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name="CategoryAttributeDefinition",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("key", models.CharField(max_length=64)),
                ("label", models.CharField(max_length=120)),
                (
                    "field_type",
                    models.CharField(
                        choices=[
                            ("text", "Text"),
                            ("longtext", "Long text"),
                            ("number", "Number"),
                            ("decimal", "Decimal"),
                            ("currency", "Currency"),
                            ("date", "Date"),
                            ("datetime", "Date/time"),
                            ("bool", "Boolean"),
                            ("choice", "Choice"),
                            ("multichoice", "Multiple choice"),
                            ("reference", "Reference"),
                        ],
                        max_length=24,
                    ),
                ),
                ("required", models.BooleanField(default=False)),
                ("options", models.JSONField(blank=True, default=list)),
                ("unique", models.BooleanField(default=False)),
                ("restricted", models.BooleanField(default=False)),
                (
                    "category",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attribute_definitions",
                        to="reference_data.category",
                    ),
                ),
            ],
            options={"unique_together": {("category", "key")}},
        ),
        migrations.CreateModel(
            name="StatusTransitionRule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("requires_reason", models.BooleanField(default=False)),
                ("requires_evidence", models.BooleanField(default=False)),
                ("requires_approval", models.BooleanField(default=False)),
                ("allowed_roles", models.JSONField(blank=True, default=list)),
                (
                    "from_status",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="transitions_from",
                        to="reference_data.assetstatus",
                    ),
                ),
                (
                    "to_status",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="transitions_to",
                        to="reference_data.assetstatus",
                    ),
                ),
            ],
            options={"unique_together": {("from_status", "to_status")}},
        ),
    ]
