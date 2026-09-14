from django.contrib import admin

from .models import PlannerAppointment, PlannerNote, PlannerTask, RunSheetItem


@admin.register(PlannerTask)
class PlannerTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "wedding", "kind", "status", "priority", "due_at", "assigned_to")
    list_filter = ("wedding", "kind", "status", "priority")
    search_fields = ("title", "description", "wedding__name")


@admin.register(PlannerAppointment)
class PlannerAppointmentAdmin(admin.ModelAdmin):
    list_display = ("title", "wedding", "starts_at", "location", "assigned_to")
    list_filter = ("wedding", "starts_at")
    search_fields = ("title", "location", "notes", "wedding__name")


@admin.register(PlannerNote)
class PlannerNoteAdmin(admin.ModelAdmin):
    list_display = ("title", "wedding", "is_pinned", "created_by", "updated_at")
    list_filter = ("wedding", "is_pinned")
    search_fields = ("title", "body", "wedding__name")


@admin.register(RunSheetItem)
class RunSheetItemAdmin(admin.ModelAdmin):
    list_display = ("scheduled_at", "title", "wedding", "location", "owner_label", "status")
    list_filter = ("wedding", "status", "scheduled_at")
    search_fields = ("title", "location", "owner_label", "notes", "wedding__name")
