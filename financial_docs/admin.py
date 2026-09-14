from django.contrib import admin

from .models import FinancialAuditEvent, FinancialDocument


@admin.register(FinancialDocument)
class FinancialDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "wedding", "document_type", "visibility", "source_label", "created_by", "created_at")
    list_filter = ("document_type", "visibility", "wedding")
    search_fields = ("title", "original_name", "source_label", "notes", "wedding__name")
    readonly_fields = ("original_name", "file_size", "created_at", "updated_at")


@admin.register(FinancialAuditEvent)
class FinancialAuditEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "wedding", "action", "entity_type", "actor", "message")
    list_filter = ("action", "entity_type", "wedding")
    search_fields = ("message", "entity_id", "wedding__name", "actor__username")
    readonly_fields = ("wedding", "actor", "action", "entity_type", "entity_id", "message", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
