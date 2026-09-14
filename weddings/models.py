import uuid

from django.conf import settings
from django.db import models


class Wedding(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        ACTIVE = "ACTIVE", "Active"
        EXPIRED = "EXPIRED", "Expired"
        ARCHIVE_PENDING = "ARCHIVE_PENDING", "Archive Pending"
        EXPORTING = "EXPORTING", "Exporting"
        EXPORTED = "EXPORTED", "Exported"
        DELETE_PENDING = "DELETE_PENDING", "Delete Pending"
        ARCHIVED = "ARCHIVED", "Archived"

    public_id = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_weddings",
    )

    name = models.CharField(max_length=255)

    slug = models.SlugField(
        max_length=255,
        unique=True,
    )

    bride_name = models.CharField(
        max_length=150,
        blank=True,
    )

    groom_name = models.CharField(
        max_length=150,
        blank=True,
    )

    start_date = models.DateField(
        null=True,
        blank=True,
    )

    wedding_date = models.DateTimeField(
        null=True,
        blank=True,
    )

    expire_date = models.DateTimeField(
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )

    timezone = models.CharField(
        max_length=64,
        default="Asia/Yangon",
    )

    # Venue master data. wedding_location is retained as the canonical venue name
    # for backwards compatibility with earlier EverAfter releases.
    wedding_location = models.CharField(max_length=255, blank=True)
    venue_full_address = models.CharField(max_length=500, blank=True)
    venue_latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    venue_longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    venue_landmark = models.CharField(max_length=255, blank=True)
    venue_location_note = models.TextField(blank=True)

    google_maps_url = models.URLField(max_length=1000, blank=True)


    guest_limit = models.PositiveIntegerField(
        default=100,
    )

    photo_limit = models.PositiveIntegerField(
        default=100,
    )

    print_limit = models.PositiveIntegerField(
        default=0,
    )

    published_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    expired_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    archived_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.public_id:
            self.public_id = f"WED-{uuid.uuid4().hex[:10].upper()}"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.public_id} - {self.name}"