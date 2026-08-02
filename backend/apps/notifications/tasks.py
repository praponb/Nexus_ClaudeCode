"""Celery tasks for notification jobs (FR-023; D-10)."""

from celery import shared_task


@shared_task
def send_due_reminders() -> dict:
    """Daily warranty-expiry / maintenance-due reminder digest."""
    from apps.notifications.services import generate_due_reminders

    return generate_due_reminders()
