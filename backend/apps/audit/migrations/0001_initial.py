import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AuditEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("actor_type", models.CharField(default="user", max_length=16)),
                ("action", models.CharField(max_length=64)),
                ("target_type", models.CharField(blank=True, default="", max_length=64)),
                ("target_uuid", models.UUIDField(blank=True, null=True)),
                ("before", models.JSONField(blank=True, null=True)),
                ("after", models.JSONField(blank=True, null=True)),
                ("outcome", models.CharField(default="success", max_length=16)),
                ("correlation_id", models.UUIDField(blank=True, null=True)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("prev_hash", models.CharField(blank=True, default="", max_length=64)),
                ("record_hash", models.CharField(blank=True, default="", max_length=64)),
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
            ],
            options={
                "ordering": ["id"],
                "indexes": [
                    models.Index(fields=["target_type", "target_uuid"], name="audit_target_idx"),
                    models.Index(fields=["correlation_id"], name="audit_correlation_idx"),
                ],
            },
        ),
    ]
