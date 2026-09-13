from django.contrib import admin

from .models import CheckIn


@admin.register(CheckIn)
class CheckInAdmin(admin.ModelAdmin):
    list_display = (
        "guest",
        "wedding",
        "checked_in_count",
        "checked_in_at",
        "return_gift_quantity",
        "return_gift_issued_at",
    )
    list_filter = ("wedding", "checked_in_at", "return_gift_issued_at")
    search_fields = ("guest__name", "guest__phone", "guest__public_id")
    readonly_fields = ("created_at", "updated_at")
