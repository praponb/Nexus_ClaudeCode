"""Celery tasks for bulk jobs (D-10). Eager in local/test; jobs are
idempotent (commit replay returns the completed job unchanged)."""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def process_import_job(self, job_id: int) -> None:
    from apps.bulk.models import ImportJob
    from apps.bulk.services import run_import

    try:
        job = ImportJob.objects.get(pk=job_id)
    except ImportJob.DoesNotExist:
        logger.warning("import job %s no longer exists", job_id)
        return
    try:
        run_import(job)
    except Exception as exc:  # noqa: BLE001
        logger.exception("import job %s failed", job_id)
        raise self.retry(exc=exc) from exc


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def process_export_job(self, job_id: int, include_finance: bool) -> None:
    from apps.bulk.models import ExportJob
    from apps.bulk.services import run_export

    try:
        job = ExportJob.objects.get(pk=job_id)
    except ExportJob.DoesNotExist:
        logger.warning("export job %s no longer exists", job_id)
        return
    try:
        run_export(job, include_finance=include_finance)
    except Exception as exc:  # noqa: BLE001
        logger.exception("export job %s failed", job_id)
        raise self.retry(exc=exc) from exc
