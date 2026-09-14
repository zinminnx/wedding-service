from django import forms

from .models import BudgetCategory, BudgetItem, WeddingBudgetSettings


class WeddingBudgetSettingsForm(forms.ModelForm):
    class Meta:
        model = WeddingBudgetSettings
        fields = ["total_budget", "currency"]
        widgets = {
            "total_budget": forms.NumberInput(attrs={"min": "0", "step": "0.01", "placeholder": "e.g. 20000000"}),
            "currency": forms.TextInput(attrs={"maxlength": 8, "placeholder": "MMK"}),
        }

    def clean_currency(self):
        value = (self.cleaned_data.get("currency") or "MMK").strip().upper()
        return value or "MMK"


class BudgetItemForm(forms.ModelForm):
    new_category = forms.CharField(
        required=False,
        max_length=100,
        label="New category",
        help_text="Optional. If filled, this category is used instead of the selected category.",
    )

    class Meta:
        model = BudgetItem
        fields = [
            "title",
            "category",
            "status",
            "visibility",
            "estimated_amount",
            "committed_amount",
            "paid_amount",
            "final_actual_amount",
            "notes",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "e.g. Wedding venue"}),
            "visibility": forms.Select(),
            "estimated_amount": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
            "committed_amount": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
            "paid_amount": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
            "final_actual_amount": forms.NumberInput(attrs={"min": "0", "step": "0.01", "placeholder": "Leave blank until final"}),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": "Optional notes..."}),
        }

    def __init__(self, *args, wedding=None, **kwargs):
        self.wedding = wedding
        super().__init__(*args, **kwargs)
        self.fields["category"].required = False
        if wedding:
            self.fields["category"].queryset = BudgetCategory.objects.filter(
                wedding=wedding,
                is_active=True,
            ).order_by("sort_order", "name")
        else:
            self.fields["category"].queryset = BudgetCategory.objects.none()

    def clean(self):
        cleaned = super().clean()
        category = cleaned.get("category")
        new_category = (cleaned.get("new_category") or "").strip()
        if not category and not new_category:
            self.add_error("category", "Choose a category or enter a new category.")
        if category and self.wedding and category.wedding_id != self.wedding.id:
            self.add_error("category", "This category does not belong to the selected wedding.")
        return cleaned

    def save(self, commit=True):
        item = super().save(commit=False)
        item.wedding = self.wedding
        item.source = BudgetItem.Source.COUPLE
        new_category = (self.cleaned_data.get("new_category") or "").strip()
        if new_category:
            category, _ = BudgetCategory.objects.get_or_create(
                wedding=self.wedding,
                name=new_category,
                defaults={"sort_order": 500},
            )
            item.category = category
        if commit:
            item.save()
        return item
