from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class PlannerTask(models.Model):
    class Kind(models.TextChoices):
        TASK = "TASK", "Task"
        CHECKLIST = "CHECKLIST", "Checklist"
        MILESTONE = "MILESTONE", "Milestone"

    class Status(models.TextChoices):
        TODO = "TODO", "To do"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        WAITING = "WAITING", "Waiting"
        DONE = "DONE", "Done"
        CANCELLED = "CANCELLED", "Cancelled"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        NORMAL = "NORMAL", "Normal"
        HIGH = "HIGH", "High"
        URGENT = "URGENT", "Urgent"

    wedding = models.ForeignKey("weddings.Wedding", on_delete=models.CASCADE, related_name="planner_tasks")
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.TASK, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TODO, db_index=True)
    priority = models.CharField(max_length=12, choices=Priority.choices, default=Priority.NORMAL, db_index=True)
    due_at = models.DateTimeField(null=True, blank=True, db_index=True)
    reminder_at = models.DateTimeField(null=True, blank=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_planner_tasks",
    )
    sort_order = models.PositiveIntegerField(default=100)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_planner_tasks",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["status", "due_at", "sort_order", "title"]
        indexes = [
            models.Index(fields=["wedding", "status"], name="planner_task_status_idx"),
            models.Index(fields=["wedding", "due_at"], name="planner_task_due_idx"),
        ]

    def clean(self):
        if self.reminder_at and self.due_at and self.reminder_at > self.due_at:
            raise ValidationError({"reminder_at": "Reminder should be before the task due time."})

    def save(self, *args, **kwargs):
        self.full_clean()
        if self.status == self.Status.DONE and self.completed_at is None:
            self.completed_at = timezone.now()
        elif self.status != self.Status.DONE:
            self.completed_at = None
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        return bool(self.due_at and self.status not in {self.Status.DONE, self.Status.CANCELLED} and self.due_at < timezone.now())

    def __str__(self):
        return self.title


class PlannerAppointment(models.Model):
    wedding = models.ForeignKey("weddings.Wedding", on_delete=models.CASCADE, related_name="planner_appointments")
    title = models.CharField(max_length=180)
    starts_at = models.DateTimeField(db_index=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    reminder_at = models.DateTimeField(null=True, blank=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_planner_appointments",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_planner_appointments",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["starts_at", "title"]
        indexes = [models.Index(fields=["wedding", "starts_at"], name="planner_appt_time_idx")]

    def clean(self):
        errors = {}
        if self.ends_at and self.ends_at < self.starts_at:
            errors["ends_at"] = "End time cannot be before start time."
        if self.reminder_at and self.reminder_at > self.starts_at:
            errors["reminder_at"] = "Reminder should be before the appointment starts."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class PlannerNote(models.Model):
    wedding = models.ForeignKey("weddings.Wedding", on_delete=models.CASCADE, related_name="planner_notes")
    title = models.CharField(max_length=180)
    body = models.TextField()
    is_pinned = models.BooleanField(default=False, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_planner_notes",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_pinned", "-updated_at"]
        indexes = [models.Index(fields=["wedding", "is_pinned"], name="planner_note_pin_idx")]

    def __str__(self):
        return self.title


class RunSheetItem(models.Model):
    class Status(models.TextChoices):
        PLANNED = "PLANNED", "Planned"
        READY = "READY", "Ready"
        DONE = "DONE", "Done"
        SKIPPED = "SKIPPED", "Skipped"

    wedding = models.ForeignKey("weddings.Wedding", on_delete=models.CASCADE, related_name="run_sheet_items")
    scheduled_at = models.DateTimeField(db_index=True)
    title = models.CharField(max_length=180)
    location = models.CharField(max_length=255, blank=True)
    owner_label = models.CharField(max_length=120, blank=True, help_text="Person/team responsible, e.g. MC or Reception")
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PLANNED, db_index=True)
    sort_order = models.PositiveIntegerField(default=100)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_run_sheet_items",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["scheduled_at", "sort_order", "title"]
        indexes = [models.Index(fields=["wedding", "scheduled_at"], name="planner_run_time_idx")]

    def __str__(self):
        return self.title
