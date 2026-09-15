from django.db import transaction
from django.utils import timezone

from .models import PrintJob


class InvalidPrintTransition(ValueError):
    pass


@transaction.atomic
def transition_job(job, action):
    job = PrintJob.objects.select_for_update().get(pk=job.pk)
    now = timezone.now()

    if action == "cancel":
        if job.status not in {PrintJob.Status.QUEUED, PrintJob.Status.CLAIMED}:
            raise InvalidPrintTransition("Only queued or claimed jobs can be cancelled.")
        job.status = PrintJob.Status.CANCELLED
        job.completed_at = now
        job.error_message = ""
    elif action == "requeue":
        if job.status not in {PrintJob.Status.FAILED, PrintJob.Status.CANCELLED}:
            raise InvalidPrintTransition("Only failed or cancelled jobs can be requeued.")
        job.status = PrintJob.Status.QUEUED
        job.claimed_by_label = ""
        job.claimed_at = None
        job.printing_started_at = None
        job.completed_at = None
        job.error_message = ""
    elif action == "mark_printed":
        if job.status not in {PrintJob.Status.QUEUED, PrintJob.Status.CLAIMED, PrintJob.Status.PRINTING}:
            raise InvalidPrintTransition("This job cannot be marked printed from its current state.")
        job.status = PrintJob.Status.PRINTED
        job.completed_at = now
        job.error_message = ""
    elif action == "mark_failed":
        if job.status not in {PrintJob.Status.QUEUED, PrintJob.Status.CLAIMED, PrintJob.Status.PRINTING}:
            raise InvalidPrintTransition("This job cannot be marked failed from its current state.")
        job.status = PrintJob.Status.FAILED
        job.completed_at = now
        job.error_message = "Manually marked failed in the dashboard."
    else:
        raise InvalidPrintTransition("Unknown print action.")

    job.save(update_fields=[
        "status", "claimed_by_label", "claimed_at", "printing_started_at",
        "completed_at", "error_message", "updated_at",
    ])
    return job
