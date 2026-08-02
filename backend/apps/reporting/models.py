from django.conf import settings
from django.db import models

from apps.core.models import CoreModel


class SavedView(CoreModel):
    """Named, shareable asset-list filter/sort configuration (FR-006)."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_views",
    )
    name = models.CharField(max_length=120)
    config = models.JSONField(default=dict, blank=True)
    shared = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False)

    class Meta:
        unique_together = [("owner", "name")]

    def __str__(self) -> str:
        return f"{self.owner}: {self.name}"
