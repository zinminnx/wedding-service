from django.contrib import admin

from .models import DashboardTheme, UserDashboardPreference


@admin.register(DashboardTheme)
class DashboardThemeAdmin(admin.ModelAdmin):
    list_display = ("name", "key", "is_active", "is_default", "sort_order", "updated_at")
    list_filter = ("is_active", "is_default")
    search_fields = ("name", "key", "description")
    ordering = ("sort_order", "name")


@admin.register(UserDashboardPreference)
class UserDashboardPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "theme", "density", "updated_at")
    list_filter = ("density", "theme")
    search_fields = ("user__username", "user__email")
