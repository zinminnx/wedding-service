from django import forms
from django.db.models import Sum

from .models import Guest, GuestGroup


class GuestForm(forms.ModelForm):
    new_group = forms.CharField(
        required=False,
        max_length=100,
        label="New group (optional)",
        help_text="Type a new group name only if it is not already in the list.",
    )

    class Meta:
        model = Guest
        fields = [
            "name",
            "phone",
            "email",
            "group",
            "allowed_party_size",
            "status",
            "notes",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Ko Aung Min"}),
            "phone": forms.TextInput(attrs={"placeholder": "09xxxxxxxxx"}),
            "email": forms.EmailInput(attrs={"placeholder": "guest@example.com"}),
            "allowed_party_size": forms.NumberInput(attrs={"min": 1, "max": 50}),
            "notes": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Optional note for reception staff...",
                }
            ),
        }

    def __init__(self, *args, wedding=None, **kwargs):
        self.wedding = wedding
        super().__init__(*args, **kwargs)

        if wedding:
            self.fields["group"].queryset = GuestGroup.objects.filter(
                wedding=wedding
            ).order_by("name")
        else:
            self.fields["group"].queryset = GuestGroup.objects.none()

        self.fields["group"].required = False
        self.fields["group"].empty_label = "No group"

    def clean_allowed_party_size(self):
        size = self.cleaned_data.get("allowed_party_size") or 1
        if size < 1:
            raise forms.ValidationError("Party size must be at least 1.")
        return size

    def clean(self):
        cleaned = super().clean()
        if not self.wedding:
            return cleaned

        group = cleaned.get("group")
        if group and group.wedding_id != self.wedding.id:
            self.add_error("group", "This group does not belong to this wedding.")

        party_size = cleaned.get("allowed_party_size") or 1
        guest_limit = self.wedding.guest_limit or 0

        if guest_limit > 0:
            current = Guest.objects.filter(wedding=self.wedding)
            if self.instance and self.instance.pk:
                current = current.exclude(pk=self.instance.pk)

            used = current.aggregate(total=Sum("allowed_party_size"))["total"] or 0
            if used + party_size > guest_limit:
                self.add_error(
                    "allowed_party_size",
                    f"This would exceed the wedding guest limit of {guest_limit}. "
                    f"Currently allocated: {used}.",
                )

        return cleaned

    def save(self, commit=True):
        guest = super().save(commit=False)
        guest.wedding = self.wedding

        new_group_name = (self.cleaned_data.get("new_group") or "").strip()
        if new_group_name:
            group, _ = GuestGroup.objects.get_or_create(
                wedding=self.wedding,
                name=new_group_name,
            )
            guest.group = group

        if commit:
            guest.save()

        return guest
