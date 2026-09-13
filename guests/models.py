import uuid

from django.db import models

from weddings.models import Wedding


class GuestGroup(models.Model):
    wedding = models.ForeignKey(
        Wedding,
        on_delete=models.CASCADE,
        related_name="guest_groups",
    )

    name = models.CharField(
        max_length=100,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=["wedding", "name"],
                name="unique_guest_group_per_wedding",
            )
        ]

    def __str__(self):
        return f"{self.wedding.public_id} - {self.name}"


class Guest(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"

    public_id = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
    )

    wedding = models.ForeignKey(
        Wedding,
        on_delete=models.CASCADE,
        related_name="guests",
    )

    group = models.ForeignKey(
        GuestGroup,
        on_delete=models.SET_NULL,
        related_name="guests",
        null=True,
        blank=True,
    )

    name = models.CharField(
        max_length=150,
    )

    phone = models.CharField(
        max_length=30,
        blank=True,
    )

    email = models.EmailField(
        blank=True,
    )

    allowed_party_size = models.PositiveSmallIntegerField(
        default=1,
    )

    notes = models.TextField(
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["name"]

        indexes = [
            models.Index(
                fields=["wedding", "name"],
                name="guest_wedding_name_idx",
            ),
            models.Index(
                fields=["wedding", "phone"],
                name="guest_wedding_phone_idx",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.public_id:
            self.public_id = f"GST-{uuid.uuid4().hex[:10].upper()}"

        if self.group and self.group.wedding_id != self.wedding_id:
            raise ValueError(
                "Guest group must belong to the same wedding."
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.public_id} - {self.name}"