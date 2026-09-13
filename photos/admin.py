from django.contrib import admin

from .models import WeddingPhoto, WeddingPhotoSettings


@admin.register(WeddingPhotoSettings)
class WeddingPhotoSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "wedding",
        "guest_upload_enabled",
        "moderation_required",
        "slideshow_enabled",
        "guest_can_download_own",
    )
    search_fields = ("wedding__name", "wedding__public_id")


@admin.register(WeddingPhoto)
class WeddingPhotoAdmin(admin.ModelAdmin):
    list_display = (
        "public_id",
        "wedding",
        "guest",
        "source",
        "status",
        "file_size",
        "created_at",
    )
    list_filter = ("status", "source", "created_at")
    search_fields = (
        "public_id",
        "wedding__name",
        "guest__name",
        "guest__phone",
        "original_filename",
    )
    readonly_fields = ("public_id", "file_size", "mime_type", "created_at", "updated_at")
