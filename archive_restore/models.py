import uuid

from django.conf import settings
from django.db import models


def generate_archive_public_id():
    return f"ARC-{uuid.uuid4().hex[:12].upper()}"


class ArchiveSnapshot(models.Model):
    class Status(models.TextChoices):
        BUILDING = "BUILDING", "Building"
        READY = "READY", "Ready"
        VERIFY_FAILED = "VERIFY_FAILED", "Verification Failed"
        FAILED = "FAILED", "Failed"
        RESTORING = "RESTORING", "Restoring"
        RESTORED = "RESTORED", "Restored"

    public_id = models.CharField(max_length=24, unique=True, default=generate_archive_public_id, editable=False)
    wedding = models.ForeignKey(
        "weddings.Wedding",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="archive_snapshots",
    )
    wedding_public_id = models.CharField(max_length=30, db_index=True)
    wedding_name = models.CharField(max_length=255)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.BUILDING, db_index=True)
    stored_object = models.OneToOneField(
        "integrations.StoredObject",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="archive_snapshot",
    )
    archive_size = models.PositiveBigIntegerField(default=0)
    sha256 = models.CharField(max_length=64, blank=True, db_index=True)
    data_object_count = models.PositiveIntegerField(default=0)
    file_count = models.PositiveIntegerField(default=0)
    manifest = models.JSONField(default=dict, blank=True)
    last_error = models.CharField(max_length=1000, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    restored_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_archive_snapshots",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["wedding_public_id", "status"], name="archive_wed_status_idx"),
            models.Index(fields=["wedding", "created_at"], name="archive_wed_time_idx"),
        ]

    @property
    def is_verified(self):
        return bool(self.verified_at and self.status in {self.Status.READY, self.Status.RESTORED})

    def __str__(self):
        return f"{self.public_id} - {self.wedding_name}"


class ArchiveEvent(models.Model):
    class Action(models.TextChoices):
        EXPORT_STARTED = "EXPORT_STARTED", "Export Started"
        EXPORT_READY = "EXPORT_READY", "Export Ready"
        EXPORT_FAILED = "EXPORT_FAILED", "Export Failed"
        VERIFIED = "VERIFIED", "Verified"
        VERIFY_FAILED = "VERIFY_FAILED", "Verify Failed"
        ARCHIVED = "ARCHIVED", "Wedding Archived"
        RESTORED = "RESTORED", "Wedding Restored"
        DELETE_PENDING = "DELETE_PENDING", "Delete Pending"
        DOWNLOADED = "DOWNLOADED", "Archive Downloaded"

    snapshot = models.ForeignKey(ArchiveSnapshot, on_delete=models.CASCADE, related_name="events")
    wedding_public_id = models.CharField(max_length=30, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="archive_events",
    )
    action = models.CharField(max_length=32, choices=Action.choices, db_index=True)
    message = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["wedding_public_id", "created_at"], name="archive_evt_wed_time_idx")]

    def __str__(self):
        return f"{self.snapshot.public_id} - {self.action}"
