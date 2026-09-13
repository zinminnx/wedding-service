from django.contrib import admin

from .models import Invitation


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = (
        "guest",
        "wedding",
        "status",
        "open_count",
        "sent_at",
        "first_opened_at",
        "last_opened_at",
        "created_at",
    )

    list_filter = (
        "status",
        "wedding",
        "created_at",
    )

    search_fields = (
        "guest__name",
        "guest__phone",
        "wedding__public_id",
        "wedding__name",
        "token",
    )

    readonly_fields = (
        "token",
        "qr_token",
        "open_count",
        "first_opened_at",
        "last_opened_at",
        "created_at",
        "updated_at",
    )
