import secrets
import uuid
from pathlib import Path

from django.conf import settings
from django.db import models


def generate_photo_public_id():
    return f"PHO-{uuid.uuid4().hex[:10].upper()}"


def generate_slideshow_token():
    return secrets.token_urlsafe(24)


def photo_upload_to(instance, filename):
    suffix = Path(filename).suffix.lower()
    if len(suffix) > 10:
        suffix = ""
    return f"weddings/{instance.wedding.public_id}/photos/{uuid.uuid4().hex}{suffix}"


class WeddingPhotoSettings(models.Model):
    wedding = models.OneToOneField(
        "weddings.Wedding",
        on_delete=models.CASCADE,
        related_name="photo_settings",
    )
    guest_upload_enabled = models.BooleanField(default=True)
    moderation_required = models.BooleanField(default=True)
    slideshow_enabled = models.BooleanField(default=False)
    guest_can_download_own = models.BooleanField(default=True)
    max_upload_mb = models.PositiveSmallIntegerField(default=15)
    max_files_per_upload = models.PositiveSmallIntegerField(default=10)
    slideshow_token = models.CharField(
        max_length=64,
        unique=True,
        default=generate_slideshow_token,
        editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Wedding photo settings"
        verbose_name_plural = "Wedding photo settings"

    def __str__(self):
        return f"Photo settings - {self.wedding.name}"


class WeddingPhoto(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    class Source(models.TextChoices):
        GUEST = "GUEST", "Guest"
        STAFF = "STAFF", "Staff"
        OWNER = "OWNER", "Owner"

    public_id = models.CharField(
        max_length=20,
        unique=True,
        default=generate_photo_public_id,
        editable=False,
    )
    wedding = models.ForeignKey(
        "weddings.Wedding",
        on_delete=models.CASCADE,
        related_name="photos",
    )
    guest = models.ForeignKey(
        "guests.Guest",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="photos",
    )
    invitation = models.ForeignKey(
        "invitations.Invitation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="photos",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_wedding_photos",
    )
    source = models.CharField(max_length=12, choices=Source.choices, default=Source.GUEST)
    image = models.FileField(upload_to=photo_upload_to, blank=True)
    storage_object = models.OneToOneField(
        "integrations.StoredObject",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="wedding_photo",
    )
    original_filename = models.CharField(max_length=255, blank=True)
    mime_type = models.CharField(max_length=80, blank=True)
    file_size = models.PositiveBigIntegerField(default=0)
    caption = models.CharField(max_length=280, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="moderated_wedding_photos",
    )
    moderated_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    download_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["wedding", "status", "-created_at"], name="photo_wed_status_idx"),
            models.Index(fields=["wedding", "guest", "-created_at"], name="photo_wed_guest_idx"),
        ]

    def __str__(self):
        guest_name = self.guest.name if self.guest_id and self.guest else self.source
        return f"{self.public_id} - {guest_name}"
