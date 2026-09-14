from django.contrib import admin

from .models import WeddingTransportationSettings


@admin.register(WeddingTransportationSettings)
class WeddingTransportationSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "wedding",
        "guide_enabled",
        "bus_guide_enabled",
        "provider",
        "updated_at",
    )
    list_filter = ("guide_enabled", "bus_guide_enabled", "provider")
    search_fields = ("wedding__name", "wedding__public_id")
