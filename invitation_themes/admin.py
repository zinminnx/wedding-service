from django.contrib import admin

from .models import InvitationTheme, WeddingInvitationDesign


@admin.register(InvitationTheme)
class InvitationThemeAdmin(admin.ModelAdmin):
    list_display = ("name", "key", "category", "status", "visible", "featured", "is_default", "version", "sort_order")
    list_filter = ("status", "visible", "featured", "is_default", "category")
    search_fields = ("name", "key", "description")
    ordering = ("sort_order", "name")
    readonly_fields = ("created_at", "updated_at")
    actions = ("publish_selected", "disable_selected", "show_selected", "hide_selected")

    @admin.action(description="Publish selected themes")
    def publish_selected(self, request, queryset):
        updated = 0
        for theme in queryset:
            theme.status = InvitationTheme.Status.PUBLISHED
            theme.full_clean()
            theme.save(update_fields=["status", "updated_at"])
            updated += 1
        self.message_user(request, f"Published {updated} theme(s).")

    @admin.action(description="Disable selected themes")
    def disable_selected(self, request, queryset):
        queryset.update(status=InvitationTheme.Status.DISABLED, visible=False)

    @admin.action(description="Show selected themes in gallery")
    def show_selected(self, request, queryset):
        queryset.filter(status=InvitationTheme.Status.PUBLISHED).update(visible=True)

    @admin.action(description="Hide selected themes from gallery")
    def hide_selected(self, request, queryset):
        queryset.update(visible=False)


@admin.register(WeddingInvitationDesign)
class WeddingInvitationDesignAdmin(admin.ModelAdmin):
    list_display = ("wedding", "draft_theme", "published_theme", "published_at", "updated_by", "updated_at")
    search_fields = ("wedding__name", "wedding__public_id")
    list_select_related = ("wedding", "draft_theme", "published_theme", "updated_by")
    readonly_fields = ("created_at", "updated_at", "published_at")
