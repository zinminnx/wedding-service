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

    limit_overridden = models.BooleanField(default=False)
    override_reason = models.CharField(max_length=255, blank=True)
    override_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="checkin_limit_overrides",
    )
    override_at = models.DateTimeField(null=True, blank=True)

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
            if not self.limit_overridden:
                errors["checked_in_count"] = (
                    f"Check-in count cannot exceed {self.guest.allowed_party_size} without an authorized override."
                )
            elif not (self.override_reason or "").strip():
                errors["override_reason"] = "An override reason is required when the party limit is exceeded."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def remaining_capacity(self):
        if not self.guest_id:
            return 0
        return max(self.guest.allowed_party_size - self.checked_in_count, 0)

    @property
    def attendance_state(self):
        if self.checked_in_count < 1:
            return "NOT_CHECKED_IN"
        if self.checked_in_count < self.guest.allowed_party_size:
            return "PARTIAL"
        if self.checked_in_count == self.guest.allowed_party_size:
            return "COMPLETE"
        return "OVERRIDDEN"

    def __str__(self):
        return f"{self.guest.name} - {self.checked_in_count} checked in"


class CheckInEvent(models.Model):
    class Action(models.TextChoices):
        ARRIVAL = "ARRIVAL", "Arrival"
        UNDO = "UNDO", "Undo"
        OVERRIDE = "OVERRIDE", "Limit Override"

    wedding = models.ForeignKey(
        "weddings.Wedding",
        on_delete=models.CASCADE,
        related_name="checkin_events",
    )
    checkin = models.ForeignKey(
        CheckIn,
        on_delete=models.CASCADE,
        related_name="events",
    )
    guest = models.ForeignKey(
        "guests.Guest",
        on_delete=models.CASCADE,
        related_name="checkin_events",
    )
    action = models.CharField(max_length=16, choices=Action.choices)
    quantity_delta = models.SmallIntegerField()
    resulting_count = models.PositiveSmallIntegerField(default=0)
    reason = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="checkin_events_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["wedding", "-created_at"], name="checkin_event_wed_time_idx"),
            models.Index(fields=["guest", "-created_at"], name="checkin_event_guest_time_idx"),
        ]

    def clean(self):
        errors = {}
        if self.checkin_id and self.wedding_id and self.checkin.wedding_id != self.wedding_id:
            errors["checkin"] = "Check-in event must belong to the same wedding."
        if self.guest_id and self.wedding_id and self.guest.wedding_id != self.wedding_id:
            errors["guest"] = "Guest must belong to the same wedding."
        if self.checkin_id and self.guest_id and self.checkin.guest_id != self.guest_id:
            errors["guest"] = "Guest must match the check-in record."
        if self.action == self.Action.OVERRIDE and not (self.reason or "").strip():
            errors["reason"] = "Override events require a reason."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.guest} {self.quantity_delta:+d} -> {self.resulting_count}"
