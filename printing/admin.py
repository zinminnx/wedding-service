from django.contrib import admin

from .models import PrintAgentDevice, PrintJob, WeddingPrintSettings


@admin.register(WeddingPrintSettings)
class WeddingPrintSettingsAdmin(admin.ModelAdmin):
    list_display = ("wedding", "queue_enabled", "queue_paused", "default_copies", "default_paper_size", "updated_at")
    list_filter = ("queue_enabled", "queue_paused", "default_paper_size")
    search_fields = ("wedding__name", "wedding__public_id")


@admin.register(PrintJob)
class PrintJobAdmin(admin.ModelAdmin):
    list_display = ("public_id", "wedding", "photo", "status", "copies", "paper_size", "created_at")
    list_filter = ("status", "paper_size", "fit_mode", "wedding")
    search_fields = ("public_id", "photo__public_id", "photo__original_filename", "wedding__name")
    readonly_fields = ("public_id", "source_token", "created_at", "updated_at")


@admin.register(PrintAgentDevice)
class PrintAgentDeviceAdmin(admin.ModelAdmin):
    list_display = ("name", "wedding", "enabled", "printer_name", "hostname", "agent_version", "last_seen_at")
    list_filter = ("enabled", "wedding")
    search_fields = ("name", "wedding__name", "printer_name", "hostname")
    readonly_fields = ("token_hash", "token_prefix", "last_seen_at", "created_at", "updated_at")
