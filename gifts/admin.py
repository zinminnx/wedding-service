from django.contrib import admin

from .models import (
    GiftPaymentMethod,
    GiftSettings,
    GuestGiftDeclaration,
    ReturnGiftInventory,
    ReturnGiftMovement,
)


@admin.register(GiftSettings)
class GiftSettingsAdmin(admin.ModelAdmin):
    list_display = ("wedding", "return_gift_mode", "return_gift_name", "updated_at")
    search_fields = ("wedding__name", "wedding__public_id")


@admin.register(GiftPaymentMethod)
class GiftPaymentMethodAdmin(admin.ModelAdmin):
    list_display = ("name", "wedding", "method_type", "account_name", "is_enabled", "sort_order")
    list_filter = ("method_type", "is_enabled", "wedding")
    search_fields = ("name", "account_name", "phone_number", "account_number", "wedding__name")


@admin.register(GuestGiftDeclaration)
class GuestGiftDeclarationAdmin(admin.ModelAdmin):
    list_display = ("guest", "wedding", "gift_choice", "payment_method_label", "payment_status", "payment_reviewed_at", "payment_reviewed_by", "updated_at")
    list_filter = ("gift_choice", "payment_status", "wedding")
    search_fields = ("guest__name", "guest__phone", "payment_reference")


@admin.register(ReturnGiftInventory)
class ReturnGiftInventoryAdmin(admin.ModelAdmin):
    list_display = ("wedding", "quantity_on_hand", "low_stock_threshold", "updated_at")
    search_fields = ("wedding__name", "wedding__public_id")


@admin.register(ReturnGiftMovement)
class ReturnGiftMovementAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "wedding",
        "movement_type",
        "quantity_delta",
        "quantity_after",
        "guest",
        "created_by",
    )
    list_filter = ("movement_type", "wedding")
    search_fields = ("guest__name", "guest__public_id", "note", "wedding__name")
    readonly_fields = ("created_at",)
