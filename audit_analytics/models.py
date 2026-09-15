import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


def generate_audit_public_id():
    return f"AUD-{uuid.uuid4().hex[:12].upper()}"


class AuditEvent(models.Model):
    class Category(models.TextChoices):
        SYSTEM = "SYSTEM", "System"
        WEDDING = "WEDDING", "Wedding"
        ACCESS = "ACCESS", "Access & Staff"
        GUESTS = "GUESTS", "Guests"
        INVITATIONS = "INVITATIONS", "Invitations"
        RSVP = "RSVP", "RSVP"
        GIFTS = "GIFTS", "Gifts & Payments"
        CHECKIN = "CHECKIN", "Check-in"
        PHOTOS = "PHOTOS", "Photos"
        PRINTING = "PRINTING", "Printing"
        PLANNER = "PLANNER", "Planner & Vendors"
        FINANCE = "FINANCE", "Finance"
        STORAGE = "STORAGE", "Storage"
        ARCHIVE = "ARCHIVE", "Archive & Restore"
        THEME = "THEME", "Themes"
        MODULE = "MODULE", "Modules"

    class Source(models.TextChoices):
        MIDDLEWARE = "MIDDLEWARE", "Request audit"
        BACKFILL = "BACKFILL", "Historical backfill"
        MANUAL = "MANUAL", "Application event"

    public_id = models.CharField(
        max_length=24,
        unique=True,
        default=generate_audit_public_id,
        editable=False,
    )
    wedding = models.ForeignKey(
        "weddings.Wedding",
        on_delete=models.CASCADE,
        related_name="audit_events",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="everafter_audit_events",
    )
    actor_label = models.CharField(max_length=160, blank=True)
    actor_role = models.CharField(max_length=40, blank=True)
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.SYSTEM,
        db_index=True,
    )
    action = models.CharField(max_length=128, db_index=True)
    entity_type = models.CharField(max_length=80, blank=True)
    entity_id = models.CharField(max_length=80, blank=True)
    message = models.CharField(max_length=500, blank=True)
    route_name = models.CharField(max_length=160, blank=True)
    status_code = models.PositiveSmallIntegerField(default=0)
    source = models.CharField(
        max_length=16,
        choices=Source.choices,
        default=Source.MANUAL,
        db_index=True,
    )
    metadata = models.JSONField(default=dict, blank=True)
    source_fingerprint = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        editable=False,
    )
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["wedding", "created_at"], name="audit_wed_time_idx"),
            models.Index(fields=["wedding", "category"], name="audit_wed_cat_idx"),
            models.Index(fields=["wedding", "actor"], name="audit_wed_actor_idx"),
        ]

    def __str__(self):
        return f"{self.public_id} - {self.action}"
