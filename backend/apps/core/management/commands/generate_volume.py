"""Generate a volume dataset for performance checks (NFR-004/NFR-006).

Separate from ``seed_dev``: this command only bulk-creates tagged assets so
hot endpoints (list/search/dashboard) can be measured at planning volumes,
e.g. ``python manage.py generate_volume --assets 100000``.
"""

from django.core.management.base import BaseCommand, CommandError

from apps.assets.models import Asset
from apps.assets.services import default_status
from apps.reference_data.models import Category


class Command(BaseCommand):
    help = "Bulk-generate assets for performance testing (non-production data)."

    def add_arguments(self, parser):
        parser.add_argument("--assets", type=int, default=1000)
        parser.add_argument("--batch", type=int, default=1000)
        parser.add_argument("--prefix", default="VOL")

    def handle(self, *args, **options):
        status = default_status()
        if status is None:
            raise CommandError("No asset statuses configured; run seed_dev first.")
        category, _ = Category.objects.get_or_create(
            code="volume", defaults={"name": "Volume generated"}
        )
        total = options["assets"]
        batch_size = max(1, options["batch"])
        prefix = options["prefix"]
        existing = Asset.objects.filter(tag__startswith=f"{prefix}-").count()
        created = 0
        while created < total:
            chunk = min(batch_size, total - created)
            rows = [
                Asset(
                    tag=f"{prefix}-{existing + created + index + 1:07d}",
                    name=f"Volume asset {existing + created + index + 1}",
                    category=category,
                    status=status,
                )
                for index in range(chunk)
            ]
            Asset.objects.bulk_create(rows)
            created += chunk
        self.stdout.write(self.style.SUCCESS(f"Created {created} assets with prefix '{prefix}-'."))
