from django.conf import settings
from django.db import models

from apps.core.models import CoreModel


class ImportJob(CoreModel):
    """Bulk CSV import (FR-018): upload -> validate/preview -> commit ->
    result report. Commit is idempotent and safely repeatable."""

    class Status(models.TextChoices):
        VALIDATED = "validated", "Validated"
        COMMITTING = "committing", "Committing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    class DuplicatePolicy(models.TextChoices):
        REJECT = "reject", "Reject duplicates"
        SKIP = "skip", "Skip duplicates"
        UPDATE = "update", "Update duplicates"

    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="import_jobs",
    )
    original_filename = models.CharField(max_length=255)
    storage_key = models.CharField(max_length=255)
    policy = models.CharField(
        max_length=16, choices=DuplicatePolicy.choices, default=DuplicatePolicy.SKIP
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.VALIDATED)
    total_rows = models.PositiveIntegerField(default=0)
    created_count = models.PositiveIntegerField(default=0)
    updated_count = models.PositiveIntegerField(default=0)
    skipped_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    row_results = models.JSONField(default=list, blank=True)
    correlation_id = models.UUIDField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Import {self.original_filename} ({self.status})"


class ExportJob(CoreModel):
    """CSV export with field-permission + formula-injection controls (FR-019)."""

    class Status(models.TextChoices):
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="export_jobs",
    )
    filters = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.COMPLETED)
    storage_key = models.CharField(max_length=255, blank=True, default="")
    row_count = models.PositiveIntegerField(default=0)
    error = models.CharField(max_length=255, blank=True, default="")
    correlation_id = models.UUIDField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Export by {self.requester} ({self.status})"
