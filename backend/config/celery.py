"""Celery application (Cycle 2+ background jobs; wired now, unused in Cycle 1)."""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

try:
    from celery import Celery
except ImportError:  # pragma: no cover - celery optional until Cycle 2
    app = None
else:
    app = Celery("asset_inventory")
    app.config_from_object("django.conf:settings", namespace="CELERY")
    app.autodiscover_tasks()
