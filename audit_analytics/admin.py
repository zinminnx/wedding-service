from django.contrib import admin

from .models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("public_id", "wedding", "created_at", "category", "action", "actor_label", "source")
    list_filter = ("category", "source", "created_at")
    search_fields = ("public_id", "wedding__name", "action", "message", "actor_label", "entity_id")
    readonly_fields = [field.name for field in AuditEvent._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
