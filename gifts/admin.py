from django.contrib import admin

from .models import GiftPaymentMethod, GiftSettings, GuestGiftDeclaration


@admin.register(GiftSettings)
class GiftSettingsAdmin(admin.ModelAdmin):
    list_display = ("wedding", "accept_monetary_gift", "accept_physical_gift", "return_gift_mode", "return_gift_stock")
    list_filter = ("accept_monetary_gift", "accept_physical_gift", "return_gift_mode")


@admin.register(GiftPaymentMethod)
class GiftPaymentMethodAdmin(admin.ModelAdmin):
    list_display = ("name", "wedding", "method_type", "account_name", "is_enabled", "sort_order")
    list_filter = ("method_type", "is_enabled", "wedding")
    search_fields = ("name", "account_name", "phone_number", "account_number")


@admin.register(GuestGiftDeclaration)
class GuestGiftDeclarationAdmin(admin.ModelAdmin):
    list_display = ("guest", "wedding", "gift_choice", "payment_method_label", "payment_status", "amount", "updated_at")
    list_filter = ("gift_choice", "payment_status", "wedding")
    search_fields = ("guest__name", "guest__phone", "payment_method", "payment_reference")
