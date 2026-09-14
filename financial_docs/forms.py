from pathlib import Path

from django import forms
from django.db.models import Q

from budgeting.models import BudgetItem
from staffing.access import get_user_wedding_role
from vendors.models import VendorQuote

from .models import FinancialDocument


ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024


def _planner_only(user, wedding):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False) or wedding.owner_id == user.id:
        return False
    return get_user_wedding_role(user, wedding) == "WEDDING_PLANNER"


class _BaseDocumentForm(forms.ModelForm):
    class Meta:
        model = FinancialDocument
        fields = ["document_type", "title", "file", "visibility", "notes"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "e.g. Venue deposit receipt"}),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": "Optional note..."}),
        }

    def __init__(self, *args, wedding=None, user=None, **kwargs):
        self.wedding = wedding
        self.user = user
        super().__init__(*args, **kwargs)
        if _planner_only(user, wedding):
            self.fields["visibility"].choices = [
                (FinancialDocument.Visibility.SHARED, "Shared with Planner"),
            ]
            self.fields["visibility"].initial = FinancialDocument.Visibility.SHARED

    def clean_file(self):
        file = self.cleaned_data.get("file")
        if not file:
            return file
        ext = Path(file.name).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise forms.ValidationError("Upload PDF, PNG, JPG/JPEG or WEBP files only.")
        if getattr(file, "size", 0) > MAX_FILE_SIZE:
            raise forms.ValidationError("Financial document must be 10 MB or smaller.")
        return file

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.wedding = self.wedding
        obj.created_by = self.user
        upload = self.cleaned_data.get("file")
        if upload:
            obj.original_name = Path(upload.name).name[:255]
            obj.file_size = getattr(upload, "size", 0)
        if commit:
            obj.save()
        return obj


class BudgetDocumentForm(_BaseDocumentForm):
    budget_item = forms.ModelChoiceField(queryset=BudgetItem.objects.none(), label="Budget item")

    class Meta(_BaseDocumentForm.Meta):
        fields = ["budget_item", "document_type", "title", "file", "visibility", "notes"]

    def __init__(self, *args, wedding=None, user=None, **kwargs):
        super().__init__(*args, wedding=wedding, user=user, **kwargs)
        qs = BudgetItem.objects.filter(wedding=wedding).select_related("category").order_by("source", "title") if wedding else BudgetItem.objects.none()
        if wedding and _planner_only(user, wedding):
            qs = qs.filter(
                Q(source=BudgetItem.Source.PLANNER)
                | Q(source=BudgetItem.Source.COUPLE, visibility=BudgetItem.Visibility.SHARED)
            )
        self.fields["budget_item"].queryset = qs

    def clean(self):
        cleaned = super().clean()
        item = cleaned.get("budget_item")
        visibility = cleaned.get("visibility")
        if item and item.wedding_id != self.wedding.id:
            self.add_error("budget_item", "Budget item does not belong to this wedding.")
        if item and item.visibility == BudgetItem.Visibility.PRIVATE and visibility == FinancialDocument.Visibility.SHARED:
            self.add_error("visibility", "A document linked to a private Couple expense cannot be shared with Planner.")
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.budget_item = self.cleaned_data["budget_item"]
        obj.vendor_quote = None
        if obj.budget_item.visibility == BudgetItem.Visibility.PRIVATE:
            obj.visibility = FinancialDocument.Visibility.PRIVATE
        if commit:
            obj.save()
        return obj


class VendorDocumentForm(_BaseDocumentForm):
    vendor_quote = forms.ModelChoiceField(queryset=VendorQuote.objects.none(), label="Vendor quote")

    class Meta(_BaseDocumentForm.Meta):
        fields = ["vendor_quote", "document_type", "title", "file", "visibility", "notes"]

    def __init__(self, *args, wedding=None, user=None, **kwargs):
        super().__init__(*args, wedding=wedding, user=user, **kwargs)
        self.fields["vendor_quote"].queryset = (
            VendorQuote.objects.filter(wedding=wedding).select_related("vendor").order_by("-updated_at")
            if wedding else VendorQuote.objects.none()
        )

    def clean_vendor_quote(self):
        quote = self.cleaned_data.get("vendor_quote")
        if quote and quote.wedding_id != self.wedding.id:
            raise forms.ValidationError("Vendor quote does not belong to this wedding.")
        return quote

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.vendor_quote = self.cleaned_data["vendor_quote"]
        obj.budget_item = None
        if commit:
            obj.save()
        return obj
