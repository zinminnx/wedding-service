from django.contrib import admin

from .models import FeatureModule, ServicePackage, WeddingModuleProfile, WeddingModuleSetting


@admin.register(FeatureModule)
class FeatureModuleAdmin(admin.ModelAdmin):
    list_display = (
        "name", "key", "module_type", "version", "system_enabled",
        "visible_to_weddings", "sort_order",
    )
    list_filter = ("module_type", "system_enabled", "visible_to_weddings")
    search_fields = ("name", "key", "description")
    filter_horizontal = ("dependencies",)
    ordering = ("sort_order", "name")

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.is_core:
            return ("key", "module_type")
        return ()


@admin.register(ServicePackage)
class ServicePackageAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "is_default", "updated_at")
    list_filter = ("is_active", "is_default")
    search_fields = ("name", "slug")
    filter_horizontal = ("modules",)


@admin.register(WeddingModuleProfile)
class WeddingModuleProfileAdmin(admin.ModelAdmin):
    list_display = ("wedding", "package", "updated_at")
    list_select_related = ("wedding", "package")
    search_fields = ("wedding__name", "wedding__public_id")


@admin.register(WeddingModuleSetting)
class WeddingModuleSettingAdmin(admin.ModelAdmin):
    list_display = ("wedding", "module", "enabled", "updated_by", "updated_at")
    list_filter = ("enabled", "module")
    list_select_related = ("wedding", "module", "updated_by")
    search_fields = ("wedding__name", "wedding__public_id", "module__name", "module__key")
