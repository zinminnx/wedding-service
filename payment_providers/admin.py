from django import forms
from django.contrib import admin
from django.utils.html import format_html

from .models import PaymentMethodProviderLink, PaymentProvider


class PaymentProviderAdminForm(forms.ModelForm):
    class Meta:
        model = PaymentProvider
        fields = "__all__"

    def clean_logo(self):
        file = self.cleaned_data.get("logo")
        if not file or not hasattr(file, "size"):
            return file
        if file.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Provider logo must be 5 MB or smaller.")
        content_type = getattr(file, "content_type", "")
        if content_type and not content_type.startswith("image/"):
            raise forms.ValidationError("Provider logo must be an image file.")
        return file

    def clean(self):
        cleaned = super().clean()
        if self.instance and self.instance.pk:
            old = PaymentProvider.objects.filter(pk=self.instance.pk).only("provider_type").first()
            new_type = cleaned.get("provider_type")
            if old and new_type and old.provider_type != new_type and self.instance.payment_accounts.exists():
                self.add_error(
                    "provider_type",
                    "Provider type cannot be changed after wedding accounts are linked. Create a new provider instead.",
                )
        return cleaned


@admin.register(PaymentProvider)
class PaymentProviderAdmin(admin.ModelAdmin):
    form = PaymentProviderAdminForm
    list_display = (
        "logo_preview",
        "name",
        "short_name",
        "provider_type",
        "status",
        "sort_order",
        "linked_accounts",
    )
    list_filter = ("provider_type", "status")
    search_fields = ("name", "short_name", "key")
    list_editable = ("status", "sort_order")
    ordering = ("provider_type", "sort_order", "name")
    readonly_fields = ("logo_preview_large", "created_at", "updated_at")
    fieldsets = (
        ("Provider", {"fields": ("provider_type", "name", "short_name", "key")}),
        ("Branding", {"fields": ("logo", "logo_preview_large")}),
        ("Availability", {"fields": ("status", "sort_order")}),
        ("System", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="Logo")
    def logo_preview(self, obj):
        if not obj.logo:
            return "—"
        return format_html(
            '<img src="{}" alt="" style="width:34px;height:34px;object-fit:contain;border-radius:8px;background:#fff;border:1px solid #ddd;padding:3px;">',
            obj.logo.url,
        )

    @admin.display(description="Logo preview")
    def logo_preview_large(self, obj):
        if not obj or not obj.logo:
            return "No logo uploaded"
        return format_html(
            '<img src="{}" alt="" style="max-width:180px;max-height:100px;object-fit:contain;background:#fff;border:1px solid #ddd;border-radius:12px;padding:10px;">',
            obj.logo.url,
        )

    @admin.display(description="Wedding accounts")
    def linked_accounts(self, obj):
        return obj.payment_accounts.count()

    def has_delete_permission(self, request, obj=None):
        if obj and obj.payment_accounts.exists():
            return False
        return super().has_delete_permission(request, obj)


@admin.register(PaymentMethodProviderLink)
class PaymentMethodProviderLinkAdmin(admin.ModelAdmin):
    list_display = ("payment_method", "provider", "updated_at")
    list_filter = ("provider__provider_type", "provider")
    search_fields = (
        "payment_method__wedding__name",
        "payment_method__account_name",
        "provider__name",
    )
    readonly_fields = ("created_at", "updated_at")
