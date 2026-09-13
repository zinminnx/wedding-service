from django.contrib import admin

from .models import RSVP


@admin.register(RSVP)
class RSVPAdmin(admin.ModelAdmin):
    list_display = (
        "guest",
        "wedding",
        "response",
        "attending_adults",
        "attending_children",
        "responded_at",
    )
    list_filter = ("response", "wedding", "responded_at")
    search_fields = (
        "guest__name",
        "guest__phone",
        "wedding__name",
        "wedding__public_id",
    )
    readonly_fields = ("created_at", "updated_at")
