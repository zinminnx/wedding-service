import hashlib
import secrets
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


def generate_print_public_id():
    return f"PRN-{uuid.uuid4().hex[:10].upper()}"


def generate_source_token():
    return secrets.token_urlsafe(32)


class WeddingPrintSettings(models.Model):
    wedding = models.OneToOneField(
        "weddings.Wedding",
        on_delete=models.CASCADE,
        related_name="print_settings",
    )
    queue_enabled = models.BooleanField(default=True)
    queue_paused = models.BooleanField(default=False)
    default_copies = models.PositiveSmallIntegerField(default=1)
    default_paper_size = models.CharField(max_length=16, default="4X6")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Wedding print settings"
        verbose_name_plural = "Wedding print settings"

    def clean(self):
        super().clean()
        if self.default_copies < 1 or self.default_copies > 99:
            raise ValidationError({"default_copies": "Default copies must be between 1 and 99."})

    def __str__(self):
        return f"Print settings - {self.wedding}"


class PrintAgentDevice(models.Model):
    wedding = models.ForeignKey(
        "weddings.Wedding",
        on_delete=models.CASCADE,
        related_name="print_agent_devices",
    )
    name = models.CharField(max_length=120)
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    token_prefix = models.CharField(max_length=16)
    enabled = models.BooleanField(default=True)
    printer_name = models.CharField(max_length=200, blank=True)
    hostname = models.CharField(max_length=120, blank=True)
    agent_version = models.CharField(max_length=40, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=500, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_print_agents",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        indexes = [
            models.Index(fields=["wedding", "enabled"], name="print_agent_wed_enabled_idx"),
            models.Index(fields=["wedding", "last_seen_at"], name="print_agent_wed_seen_idx"),
        ]

    @staticmethod
    def _new_secret():
        return secrets.token_urlsafe(48)

    @staticmethod
    def _digest(secret):
        return hashlib.sha256(secret.encode("utf-8")).hexdigest()

    @classmethod
    def issue_token(cls, *, wedding, name, printer_name="", created_by=None):
        secret = cls._new_secret()
        device = cls.objects.create(
            wedding=wedding,
            name=name,
            token_hash=cls._digest(secret),
            token_prefix=secret[:12],
            printer_name=printer_name,
            created_by=created_by,
        )
        return device, secret

    def rotate_token(self):
        secret = self._new_secret()
        self.token_hash = self._digest(secret)
        self.token_prefix = secret[:12]
        self.enabled = True
        self.last_error = ""
        self.save(update_fields=["token_hash", "token_prefix", "enabled", "last_error", "updated_at"])
        return secret

    def __str__(self):
        return f"{self.wedding} - {self.name}"


class PrintJob(models.Model):
    class Status(models.TextChoices):
        QUEUED = "QUEUED", "Queued"
        CLAIMED = "CLAIMED", "Claimed"
        PRINTING = "PRINTING", "Printing"
        PRINTED = "PRINTED", "Printed"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"

    class PaperSize(models.TextChoices):
        PHOTO_4X6 = "4X6", "4 × 6 in"
        PHOTO_5X7 = "5X7", "5 × 7 in"
        A6 = "A6", "A6"
        A5 = "A5", "A5"
        A4 = "A4", "A4"
        CUSTOM = "CUSTOM", "Custom / Printer default"

    class FitMode(models.TextChoices):
        FIT = "FIT", "Fit entire image"
        FILL = "FILL", "Fill page / crop"
        ORIGINAL = "ORIGINAL", "Original size"

    public_id = models.CharField(
        max_length=20,
        unique=True,
        default=generate_print_public_id,
        editable=False,
    )
    wedding = models.ForeignKey(
        "weddings.Wedding",
        on_delete=models.CASCADE,
        related_name="print_jobs",
    )
    photo = models.ForeignKey(
        "photos.WeddingPhoto",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="print_jobs",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.QUEUED,
        db_index=True,
    )
    copies = models.PositiveSmallIntegerField(default=1)
    paper_size = models.CharField(
        max_length=16,
        choices=PaperSize.choices,
        default=PaperSize.PHOTO_4X6,
    )
    fit_mode = models.CharField(
        max_length=16,
        choices=FitMode.choices,
        default=FitMode.FIT,
    )
    notes = models.CharField(max_length=255, blank=True)
    source_token = models.CharField(
        max_length=64,
        unique=True,
        default=generate_source_token,
        editable=False,
    )
    agent_device = models.ForeignKey(
        "printing.PrintAgentDevice",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jobs",
    )
    claim_expires_at = models.DateTimeField(null=True, blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requested_print_jobs",
    )
    claimed_by_label = models.CharField(max_length=120, blank=True)
    error_message = models.CharField(max_length=500, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    printing_started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["wedding", "status", "created_at"], name="print_wed_status_idx"),
            models.Index(fields=["wedding", "created_at"], name="print_wed_time_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.copies < 1 or self.copies > 99:
            errors["copies"] = "Copies must be between 1 and 99."
        if self.photo_id:
            if self.wedding_id and self.photo.wedding_id != self.wedding_id:
                errors["photo"] = "Photo must belong to the same wedding."
            if self.photo.status != self.photo.Status.APPROVED:
                errors["photo"] = "Only approved photos can be queued for printing."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_active(self):
        return self.status in {self.Status.QUEUED, self.Status.CLAIMED, self.Status.PRINTING}

    def __str__(self):
        return f"{self.public_id} - {self.get_status_display()}"
