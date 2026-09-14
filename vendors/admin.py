from django.contrib import admin

from .models import Vendor, VendorQuote


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ("name", "wedding", "category", "status", "phone", "updated_at")
    list_filter = ("status", "wedding", "category")
    search_fields = ("name", "contact_person", "phone", "email", "wedding__name")


@admin.register(VendorQuote)
class VendorQuoteAdmin(admin.ModelAdmin):
    list_display = ("title", "vendor", "wedding", "quoted_amount", "status", "comparison_group", "updated_at")
    list_filter = ("status", "wedding", "category")
    search_fields = ("title", "vendor__name", "comparison_group", "wedding__name")
    readonly_fields = ("proposed_at", "reviewed_at", "reviewed_by", "approved_budget_item")
