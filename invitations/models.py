import secrets

from django.db import models

from guests.models import Guest
from weddings.models import Wedding


def generate_invitation_token():
    return secrets.token_urlsafe(32)


def generate_qr_token():
    return secrets.token_urlsafe(32)


class Invitation(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        READY = "READY", "Ready"
        SENT = "SENT", "Sent"
        OPENED = "OPENED", "Opened"
        REVOKED = "REVOKED", "Revoked"
        EXPIRED = "EXPIRED", "Expired"

    wedding = models.ForeignKey(
        Wedding,
        on_delete=models.CASCADE,
        related_name="invitations",
    )

    guest = models.OneToOneField(
        Guest,
        on_delete=models.CASCADE,
        related_name="invitation",
    )

    token = models.CharField(
        max_length=100,
        unique=True,
        default=generate_invitation_token,
        editable=False,
    )

    qr_token = models.CharField(
        max_length=100,
        unique=True,
        default=generate_qr_token,
        editable=False,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )

    sent_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    first_opened_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    last_opened_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    open_count = models.PositiveIntegerField(
        default=0,
    )

    revoked_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def save(self, *args, **kwargs):
        if self.guest.wedding_id != self.wedding_id:
            raise ValueError(
                "Invitation guest must belong to the same wedding."
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.wedding.public_id} - {self.guest.name}"