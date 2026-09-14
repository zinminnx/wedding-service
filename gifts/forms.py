from django import forms
from django.db.models import Q

from payment_providers.models import PaymentMethodProviderLink, PaymentProvider

from .models import GiftPaymentMethod, GiftSettings, ReturnGiftInventory


class GiftSettingsForm(forms.ModelForm):
    class Meta:
        model = GiftSettings
        fields = [
            "accept_monetary_gift",
            "accept_physical_gift",
            "allow_no_gift",
            "return_gift_mode",
            "return_gift_name",
            "custom_return_gift_quantity",
            "return_gift_requires_checkin",
            "return_gift_allow_staff_override",
        ]
        widgets = {
            "return_gift_name": forms.TextInput(attrs={"placeholder": "e.g. Wedding souvenir"}),
            "custom_return_gift_quantity": forms.NumberInput(attrs={"min": 0, "max": 50}),
        }


class ProviderChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.name} · {obj.get_provider_type_display()}"


class GiftPaymentMethodForm(forms.ModelForm):
    provider = ProviderChoiceField(
        queryset=PaymentProvider.objects.none(),
        empty_label="Choose an approved provider",
        help_text="Provider names and logos are managed by Main Admin.",
    )

    class Meta:
        model = GiftPaymentMethod
        fields = [
            "provider",
            "account_name",
            "phone_number",
            "account_number",
            "qr_image",
            "is_enabled",
        ]
        widgets = {
            "account_name": forms.TextInput(attrs={"placeholder": "Account holder name"}),
            "phone_number": forms.TextInput(attrs={"placeholder": "09xxxxxxxxx"}),
            "account_number": forms.TextInput(attrs={"placeholder": "Bank account number"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        active = PaymentProvider.objects.filter(status=PaymentProvider.Status.ACTIVE)
        current_provider = None
        if self.instance and self.instance.pk:
            link = PaymentMethodProviderLink.objects.filter(
                payment_method=self.instance
            ).select_related("provider").first()
            if link:
                current_provider = link.provider
                self.fields["provider"].initial = current_provider

        if current_provider:
            self.fields["provider"].queryset = PaymentProvider.objects.filter(
                Q(status=PaymentProvider.Status.ACTIVE) | Q(pk=current_provider.pk)
            ).order_by("provider_type", "sort_order", "name")
        else:
            self.fields["provider"].queryset = active.order_by(
                "provider_type", "sort_order", "name"
            )

    def clean_qr_image(self):
        file = self.cleaned_data.get("qr_image")
        if not file or not hasattr(file, "size"):
            return file
        if file.size > 5 * 1024 * 1024:
            raise forms.ValidationError("QR image must be 5 MB or smaller.")
        content_type = getattr(file, "content_type", "")
        if content_type and not content_type.startswith("image/"):
            raise forms.ValidationError("Please upload an image file.")
        return file

    def clean(self):
        cleaned = super().clean()
        provider = cleaned.get("provider")
        phone = (cleaned.get("phone_number") or "").strip()
        account_no = (cleaned.get("account_number") or "").strip()
        qr = cleaned.get("qr_image")

        if provider is None:
            return cleaned

        existing_link = None
        if self.instance and self.instance.pk:
            existing_link = PaymentMethodProviderLink.objects.filter(
                payment_method=self.instance,
                provider=provider,
            ).exists()

        if provider.status != PaymentProvider.Status.ACTIVE and not existing_link:
            self.add_error("provider", "This provider is disabled for new payment accounts.")

        if provider.provider_type == PaymentProvider.ProviderType.PAY:
            if not phone and not qr and not (self.instance and self.instance.qr_image):
                self.add_error("phone_number", "For Mobile Pay, add a phone number or QR image.")
        elif provider.provider_type == PaymentProvider.ProviderType.BANK:
            if not account_no:
                self.add_error("account_number", "Bank account number is required.")

        return cleaned

    def save(self, commit=True):
        item = super().save(commit=False)
        provider = self.cleaned_data["provider"]
        item.method_type = provider.provider_type
        item.name = provider.name

        if provider.provider_type == PaymentProvider.ProviderType.BANK:
            item.phone_number = ""
        else:
            item.account_number = ""

        if commit:
            item.save()
            self.save_provider_link(item)
        return item

    def save_provider_link(self, item):
        provider = self.cleaned_data["provider"]
        PaymentMethodProviderLink.objects.update_or_create(
            payment_method=item,
            defaults={"provider": provider},
        )


class ReturnGiftRestockForm(forms.Form):
    quantity = forms.IntegerField(
        min_value=1,
        max_value=100000,
        widget=forms.NumberInput(attrs={"min": 1, "placeholder": "Quantity"}),
    )
    note = forms.CharField(
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={"placeholder": "Optional note, e.g. second delivery"}),
    )


class ReturnGiftSetStockForm(forms.ModelForm):
    class Meta:
        model = ReturnGiftInventory
        fields = ["quantity_on_hand", "low_stock_threshold"]
        widgets = {
            "quantity_on_hand": forms.NumberInput(attrs={"min": 0}),
            "low_stock_threshold": forms.NumberInput(attrs={"min": 0}),
        }
