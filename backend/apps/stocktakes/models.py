from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import CoreModel


class StocktakeSession(CoreModel):
    """A scoped physical-inventory counting exercise (FR-022)."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        OPEN = "open", "Open"
        RECONCILING = "reconciling", "Reconciling"
        CLOSED = "closed", "Closed"

    name = models.CharField(max_length=120)
    locations = models.ManyToManyField("reference_data.Location", blank=True, related_name="+")
    operators = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="+")
    start_at = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    snapshot_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    instructions = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.status})"


class StocktakeObservation(CoreModel):
    """One scanned/manual observation within a session (FR-022)."""

    class Outcome(models.TextChoices):
        FOUND = "found", "Found"
        NOT_FOUND = "not_found", "Not found"
        UNEXPECTED = "unexpected", "Unexpected"
        DUPLICATE = "duplicate", "Duplicate scan"
        MOVED = "moved", "Moved"
        CONDITION_MISMATCH = "condition_mismatch", "Condition mismatch"

    session = models.ForeignKey(
        StocktakeSession, on_delete=models.CASCADE, related_name="observations"
    )
    asset = models.ForeignKey(
        "assets.Asset",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="stocktake_observations",
    )
    tag_scanned = models.CharField(max_length=64)
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    observed_at = models.DateTimeField(default=timezone.now)
    location = models.ForeignKey(
        "reference_data.Location",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    condition = models.ForeignKey(
        "reference_data.AssetCondition",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    note = models.TextField(blank=True, default="")
    outcome = models.CharField(max_length=32, choices=Outcome.choices, default=Outcome.FOUND)

    class Meta:
        ordering = ["-observed_at", "-id"]
        indexes = [
            models.Index(fields=["session", "outcome"], name="stocktake_obs_outcome_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.tag_scanned} -> {self.outcome} ({self.session.name})"
