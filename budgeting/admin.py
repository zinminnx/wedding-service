from django.contrib import admin

from .models import BudgetCategory, BudgetItem, WeddingBudgetSettings


@admin.register(WeddingBudgetSettings)
class WeddingBudgetSettingsAdmin(admin.ModelAdmin):
    list_display = ("wedding", "total_budget", "currency", "updated_at")
    search_fields = ("wedding__name", "wedding__public_id")


@admin.register(BudgetCategory)
class BudgetCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "wedding", "sort_order", "is_active")
    list_filter = ("is_active", "wedding")
    search_fields = ("name", "wedding__name", "wedding__public_id")


@admin.register(BudgetItem)
class BudgetItemAdmin(admin.ModelAdmin):
    list_display = (
        "title", "wedding", "category", "source", "visibility", "status",
        "estimated_amount", "committed_amount", "paid_amount", "final_actual_amount",
    )
    list_filter = ("source", "visibility", "status", "category", "wedding")
    search_fields = ("title", "notes", "wedding__name", "wedding__public_id")
