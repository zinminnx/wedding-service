from django.contrib import admin

from .models import WeddingEventSettings


@admin.register(WeddingEventSettings)
class WeddingEventSettingsAdmin(admin.ModelAdmin):
    list_display = ("wedding", "calendar_enabled", "venue_enabled", "smart_map_enabled", "updated_at")
    list_filter = ("calendar_enabled", "venue_enabled", "smart_map_enabled")
    search_fields = ("wedding__name", "wedding__public_id", "wedding__wedding_location")
    readonly_fields = ("created_at", "updated_at")
