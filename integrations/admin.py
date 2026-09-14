from django.contrib import admin

from .models import StoredObject, WeddingStorageSettings


@admin.register(WeddingStorageSettings)
class WeddingStorageSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "wedding", "provider", "health_status", "last_health_check_at", "updated_at",
    )
    list_filter = ("provider", "health_status")
    search_fields = ("wedding__name", "wedding__public_id", "onedrive_drive_id", "root_folder")
    readonly_fields = ("health_status", "health_message", "last_health_check_at", "created_at", "updated_at")


@admin.register(StoredObject)
class StoredObjectAdmin(admin.ModelAdmin):
    list_display = (
        "created_at", "wedding", "category", "backend", "status", "size_bytes", "relative_path",
    )
    list_filter = ("backend", "category", "status", "wedding")
    search_fields = (
        "wedding__name", "wedding__public_id", "relative_path", "remote_item_id",
        "sha256", "source_app", "source_model", "source_object_id",
    )
    readonly_fields = ("created_at", "updated_at")
