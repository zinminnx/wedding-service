from django.contrib import admin

from .models import ArchiveEvent, ArchiveSnapshot


@admin.register(ArchiveSnapshot)
class ArchiveSnapshotAdmin(admin.ModelAdmin):
    list_display = ("public_id", "wedding_name", "status", "archive_size", "file_count", "verified_at", "created_at")
    list_filter = ("status", "created_at", "verified_at")
    search_fields = ("public_id", "wedding_public_id", "wedding_name", "sha256")
    readonly_fields = ("public_id", "sha256", "manifest", "created_at", "updated_at")


@admin.register(ArchiveEvent)
class ArchiveEventAdmin(admin.ModelAdmin):
    list_display = ("snapshot", "action", "wedding_public_id", "actor", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("snapshot__public_id", "wedding_public_id", "message")
    readonly_fields = ("created_at",)
