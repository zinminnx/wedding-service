from django import forms

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


class GiftPaymentMethodForm(forms.ModelForm):
    class Meta:
        model = GiftPaymentMethod
        fields = [
            "method_type",
            "name",
            "account_name",
            "phone_number",
            "account_number",
            "qr_image",
            "is_enabled",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. KBZPay, Wave Pay, AYA Bank"}),
            "account_name": forms.TextInput(attrs={"placeholder": "Account holder name"}),
            "phone_number": forms.TextInput(attrs={"placeholder": "09xxxxxxxxx"}),
            "account_number": forms.TextInput(attrs={"placeholder": "Bank account number"}),
        }

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
        method_type = cleaned.get("method_type")
        phone = (cleaned.get("phone_number") or "").strip()
        account_no = (cleaned.get("account_number") or "").strip()
        qr = cleaned.get("qr_image")

        if method_type == GiftPaymentMethod.MethodType.PAY and not phone and not qr:
            self.add_error("phone_number", "For Mobile Pay, add a phone number or QR image.")
        if method_type == GiftPaymentMethod.MethodType.BANK and not account_no:
            self.add_error("account_number", "Bank account number is required.")
        return cleaned


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
