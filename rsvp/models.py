from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from guests.models import Guest
from invitations.models import Invitation
from weddings.models import Wedding


class RSVP(models.Model):
    class Response(models.TextChoices):
        ATTENDING = "ATTENDING", "Attending"
        NOT_ATTENDING = "NOT_ATTENDING", "Not attending"
        MAYBE = "MAYBE", "Maybe"

    wedding = models.ForeignKey(
        Wedding,
        on_delete=models.CASCADE,
        related_name="rsvps",
    )

    guest = models.OneToOneField(
        Guest,
        on_delete=models.CASCADE,
        related_name="rsvp",
    )

    invitation = models.OneToOneField(
        Invitation,
        on_delete=models.CASCADE,
        related_name="rsvp",
    )

    response = models.CharField(
        max_length=20,
        choices=Response.choices,
        db_index=True,
    )

    attending_adults = models.PositiveSmallIntegerField(default=0)
    attending_children = models.PositiveSmallIntegerField(default=0)
    notes = models.TextField(blank=True)

    responded_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-responded_at"]
        indexes = [
            models.Index(
                fields=["wedding", "response"],
                name="rsvp_wedding_response_idx",
            ),
        ]

    @property
    def total_attending(self):
        return self.attending_adults + self.attending_children

    def clean(self):
        errors = {}

        if self.guest_id and self.wedding_id:
            if self.guest.wedding_id != self.wedding_id:
                errors["guest"] = "Guest must belong to the same wedding."

        if self.invitation_id and self.wedding_id:
            if self.invitation.wedding_id != self.wedding_id:
                errors["invitation"] = "Invitation must belong to the same wedding."

        if self.invitation_id and self.guest_id:
            if self.invitation.guest_id != self.guest_id:
                errors["invitation"] = "Invitation must belong to this guest."

        if self.response == self.Response.ATTENDING:
            total = self.attending_adults + self.attending_children
            if total < 1:
                errors["attending_adults"] = "At least one attendee is required."
            if self.guest_id and total > self.guest.allowed_party_size:
                errors["attending_adults"] = (
                    f"Total attendees cannot exceed {self.guest.allowed_party_size}."
                )
        else:
            self.attending_adults = 0
            self.attending_children = 0

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        if not self.responded_at:
            self.responded_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.guest.name} - {self.get_response_display()}"
