from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class CheckIn(models.Model):
    wedding = models.ForeignKey(
        "weddings.Wedding",
        on_delete=models.CASCADE,
        related_name="checkins",
    )
    guest = models.OneToOneField(
        "guests.Guest",
        on_delete=models.CASCADE,
        related_name="checkin",
    )
    invitation = models.OneToOneField(
        "invitations.Invitation",
        on_delete=models.CASCADE,
        related_name="checkin",
    )

    checked_in_count = models.PositiveSmallIntegerField(default=0)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_in_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="wedding_checkins",
    )

    return_gift_quantity = models.PositiveSmallIntegerField(default=0)
    return_gift_issued_at = models.DateTimeField(null=True, blank=True)
    return_gift_issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="return_gift_issues",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-checked_in_at", "guest__name"]
        indexes = [
            models.Index(
                fields=["wedding", "checked_in_at"],
                name="checkin_wedding_time_idx",
            ),
        ]

    def clean(self):
        errors = {}
        if self.guest_id and self.wedding_id and self.guest.wedding_id != self.wedding_id:
            errors["guest"] = "Guest must belong to the same wedding."
        if self.invitation_id and self.wedding_id and self.invitation.wedding_id != self.wedding_id:
            errors["invitation"] = "Invitation must belong to the same wedding."
        if self.invitation_id and self.guest_id and self.invitation.guest_id != self.guest_id:
            errors["invitation"] = "Invitation must belong to this guest."
        if self.guest_id and self.checked_in_count > self.guest.allowed_party_size:
            errors["checked_in_count"] = (
                f"Check-in count cannot exceed {self.guest.allowed_party_size}."
            )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.guest.name} - {self.checked_in_count} checked in"
