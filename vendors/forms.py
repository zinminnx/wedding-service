from django import forms

from budgeting.models import BudgetCategory

from .models import Vendor, VendorQuote


class VendorForm(forms.ModelForm):
    class Meta:
        model = Vendor
        fields = [
            "name",
            "category",
            "contact_person",
            "phone",
            "email",
            "website",
            "address",
            "status",
            "notes",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Golden Lens Studio"}),
            "contact_person": forms.TextInput(attrs={"placeholder": "Contact person"}),
            "phone": forms.TextInput(attrs={"placeholder": "09xxxxxxxxx"}),
            "email": forms.EmailInput(attrs={"placeholder": "hello@example.com"}),
            "website": forms.URLInput(attrs={"placeholder": "https://..."}),
            "address": forms.TextInput(attrs={"placeholder": "Vendor address"}),
            "notes": forms.Textarea(attrs={"rows": 4, "placeholder": "Optional notes..."}),
        }

    def __init__(self, *args, wedding=None, **kwargs):
        self.wedding = wedding
        super().__init__(*args, **kwargs)
        self.fields["category"].required = False
        self.fields["category"].queryset = BudgetCategory.objects.filter(
            wedding=wedding, is_active=True
        ).order_by("sort_order", "name") if wedding else BudgetCategory.objects.none()

    def save(self, commit=True):
        item = super().save(commit=False)
        item.wedding = self.wedding
        if commit:
            item.save()
        return item


class VendorQuoteForm(forms.ModelForm):
    class Meta:
        model = VendorQuote
        fields = [
            "vendor",
            "category",
            "title",
            "comparison_group",
            "quoted_amount",
            "deposit_amount",
            "final_amount",
            "valid_until",
            "notes",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "e.g. Full-day wedding photography"}),
            "comparison_group": forms.TextInput(attrs={"placeholder": "e.g. Photographer"}),
            "quoted_amount": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
            "deposit_amount": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
            "final_amount": forms.NumberInput(attrs={"min": "0", "step": "0.01", "placeholder": "Optional until finalized"}),
            "valid_until": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 4, "placeholder": "Package details, inclusions, exclusions..."}),
        }

    def __init__(self, *args, wedding=None, **kwargs):
        self.wedding = wedding
        super().__init__(*args, **kwargs)
        self.fields["vendor"].queryset = Vendor.objects.filter(
            wedding=wedding, status=Vendor.Status.ACTIVE
        ).order_by("name") if wedding else Vendor.objects.none()
        self.fields["category"].queryset = BudgetCategory.objects.filter(
            wedding=wedding, is_active=True
        ).order_by("sort_order", "name") if wedding else BudgetCategory.objects.none()

    def clean_quoted_amount(self):
        value = self.cleaned_data.get("quoted_amount")
        if value is None or value <= 0:
            raise forms.ValidationError("Quoted amount must be greater than zero.")
        return value

    def save(self, commit=True):
        item = super().save(commit=False)
        item.wedding = self.wedding
        if commit:
            item.save()
        return item
