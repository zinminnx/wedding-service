from django.contrib import admin

from .models import Wedding


@admin.register(Wedding)
class WeddingAdmin(admin.ModelAdmin):
    list_display = (
        "public_id",
        "name",
        "owner",
        "status",
        "wedding_date",
        "expire_date",
        "created_at",
    )

    list_filter = (
        "status",
        "created_at",
    )

    search_fields = (
        "public_id",
        "name",
        "bride_name",
        "groom_name",
        "owner__username",
    )

    prepopulated_fields = {
        "slug": ("name",),
    }

    readonly_fields = (
        "public_id",
        "created_at",
        "updated_at",
    )