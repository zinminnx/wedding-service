from django.contrib import admin

from .models import Guest, GuestGroup


@admin.register(GuestGroup)
class GuestGroupAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "wedding",
        "created_at",
    )

    list_filter = (
        "wedding",
    )

    search_fields = (
        "name",
        "wedding__public_id",
        "wedding__name",
    )


@admin.register(Guest)
class GuestAdmin(admin.ModelAdmin):
    list_display = (
        "public_id",
        "name",
        "wedding",
        "group",
        "phone",
        "allowed_party_size",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "wedding",
        "group",
    )

    search_fields = (
        "public_id",
        "name",
        "phone",
        "email",
        "wedding__public_id",
        "wedding__name",
    )

    readonly_fields = (
        "public_id",
        "created_at",
        "updated_at",
    )