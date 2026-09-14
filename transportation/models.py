from django.db import models


class WeddingTransportationSettings(models.Model):
    class Provider(models.TextChoices):
        MANUAL = "MANUAL", "Manual guidance only"
        BUS_PROJECT = "BUS_PROJECT", "Bus Project API (adapter-ready)"

    wedding = models.OneToOneField(
        "weddings.Wedding",
        on_delete=models.CASCADE,
        related_name="transportation_settings",
    )
    guide_enabled = models.BooleanField(default=True)
    bus_guide_enabled = models.BooleanField(default=False)
    provider = models.CharField(
        max_length=24,
        choices=Provider.choices,
        default=Provider.MANUAL,
    )
    transport_note = models.TextField(blank=True)
    fallback_message = models.CharField(
        max_length=255,
        default="Bus route information is temporarily unavailable. Please use the map and venue details above.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Wedding transportation settings"
        verbose_name_plural = "Wedding transportation settings"

    def __str__(self):
        return f"Transportation - {self.wedding.name}"
