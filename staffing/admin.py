from django.contrib import admin

from .models import WeddingStaffMembership


@admin.register(WeddingStaffMembership)
class WeddingStaffMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "wedding", "role", "status", "created_at")
    list_filter = ("role", "status")
    search_fields = ("user__username", "user__email", "wedding__name", "wedding__public_id")
    raw_id_fields = ("user", "wedding", "created_by")
