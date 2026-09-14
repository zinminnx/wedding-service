from django.contrib import admin

from .models import CheckIn, CheckInEvent


@admin.register(CheckIn)
class CheckInAdmin(admin.ModelAdmin):
    list_display = (
        "guest",
        "wedding",
        "checked_in_count",
        "checked_in_at",
        "limit_overridden",
        "return_gift_quantity",
        "return_gift_issued_at",
    )
    list_filter = ("wedding", "limit_overridden", "checked_in_at", "return_gift_issued_at")
    search_fields = ("guest__name", "guest__phone", "guest__public_id")
    readonly_fields = ("created_at", "updated_at")


@admin.register(CheckInEvent)
class CheckInEventAdmin(admin.ModelAdmin):
    list_display = ("guest", "wedding", "action", "quantity_delta", "resulting_count", "created_by", "created_at")
    list_filter = ("wedding", "action", "created_at")
    search_fields = ("guest__name", "guest__phone", "guest__public_id", "reason")
    readonly_fields = ("created_at",)
