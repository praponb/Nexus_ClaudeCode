import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("reference_data", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="MaintenanceType",
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
    ]
