from django.conf import settings
from django.db import models


class WeddingStorageSettings(models.Model):
    class Provider(models.TextChoices):
        LOCAL = "LOCAL", "Local Media"
        ONEDRIVE = "ONEDRIVE", "Microsoft OneDrive"

    class Health(models.TextChoices):
        UNKNOWN = "UNKNOWN", "Unknown"
        OK = "OK", "Healthy"
        ERROR = "ERROR", "Error"

    wedding = models.OneToOneField(
        "weddings.Wedding",
        on_delete=models.CASCADE,
        related_name="storage_settings",
    )
    provider = models.CharField(
        max_length=16,
        choices=Provider.choices,
        default=Provider.LOCAL,
        db_index=True,
    )
    # Optional per-wedding override. Secrets are intentionally never stored here.
    onedrive_drive_id = models.CharField(max_length=180, blank=True)
    root_folder = models.CharField(max_length=220, blank=True)
    health_status = models.CharField(
        max_length=16,
        choices=Health.choices,
        default=Health.UNKNOWN,
        db_index=True,
    )
    health_message = models.CharField(max_length=255, blank=True)
    last_health_check_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Wedding storage settings"
        verbose_name_plural = "Wedding storage settings"

    def __str__(self):
        return f"{self.wedding} - {self.get_provider_display()}"


class StoredObject(models.Model):
    class Backend(models.TextChoices):
        LOCAL = "LOCAL", "Local Media"
        ONEDRIVE = "ONEDRIVE", "Microsoft OneDrive"

    class Category(models.TextChoices):
        PHOTO = "PHOTO", "Photo"
        FINANCIAL_DOCUMENT = "FINANCIAL_DOCUMENT", "Financial Document"
        ARCHIVE = "ARCHIVE", "Archive"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        AVAILABLE = "AVAILABLE", "Available"
        FAILED = "FAILED", "Failed"
        DELETED = "DELETED", "Deleted"

    wedding = models.ForeignKey(
        "weddings.Wedding",
        on_delete=models.CASCADE,
        related_name="stored_objects",
    )
    backend = models.CharField(max_length=16, choices=Backend.choices, db_index=True)
    category = models.CharField(
        max_length=32,
        choices=Category.choices,
        default=Category.OTHER,
        db_index=True,
    )
    relative_path = models.CharField(max_length=500)
    remote_item_id = models.CharField(max_length=255, blank=True, db_index=True)
    remote_web_url = models.URLField(max_length=1000, blank=True)
    mime_type = models.CharField(max_length=160, blank=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    sha256 = models.CharField(max_length=64, blank=True, db_index=True)
    source_app = models.CharField(max_length=80, blank=True)
    source_model = models.CharField(max_length=80, blank=True)
    source_object_id = models.CharField(max_length=80, blank=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    last_error = models.CharField(max_length=500, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_storage_objects",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["wedding", "backend", "status"], name="storage_wed_backend_idx"),
            models.Index(fields=["wedding", "category"], name="storage_wed_cat_idx"),
            models.Index(fields=["source_app", "source_model", "source_object_id"], name="storage_source_idx"),
        ]

    def __str__(self):
        return f"{self.wedding} - {self.backend} - {self.relative_path}"
