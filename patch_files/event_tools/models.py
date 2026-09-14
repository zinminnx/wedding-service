from django.db import models


class WeddingEventSettings(models.Model):
    wedding = models.OneToOneField(
        "weddings.Wedding",
        on_delete=models.CASCADE,
        related_name="event_tools_settings",
    )

    # Invitation calendar behavior. Wedding date/time stays on Wedding.
    calendar_enabled = models.BooleanField(default=True)
    calendar_title = models.CharField(max_length=180, blank=True)
    calendar_description = models.TextField(blank=True)
    event_duration_minutes = models.PositiveSmallIntegerField(default=240)
    reminder_1_minutes = models.PositiveIntegerField(default=10080)  # 7 days
    reminder_2_minutes = models.PositiveIntegerField(default=1440)   # 1 day
    reminder_3_minutes = models.PositiveIntegerField(default=180)    # 3 hours

    # Invitation venue/map display behavior only.
    # Venue data itself lives on weddings.Wedding as the single source of truth.
    venue_enabled = models.BooleanField(default=True)
    smart_map_enabled = models.BooleanField(default=True)
    show_google_maps = models.BooleanField(default=True)
    show_apple_maps = models.BooleanField(default=True)
    show_address = models.BooleanField(default=True)
    show_landmark = models.BooleanField(default=True)
    show_location_note = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Wedding event settings"
        verbose_name_plural = "Wedding event settings"

    def __str__(self):
        return f"Calendar & Venue display - {self.wedding.name}"

    @property
    def effective_title(self):
        if self.calendar_title.strip():
            return self.calendar_title.strip()
        couple = " & ".join(
            part for part in [self.wedding.groom_name.strip(), self.wedding.bride_name.strip()] if part
        )
        return f"{couple} Wedding" if couple else self.wedding.name
