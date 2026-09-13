from django import forms
from django.utils import timezone

from .models import Wedding


class WeddingForm(forms.ModelForm):
    wedding_date = forms.DateTimeField(
        required=False,
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(
            format="%Y-%m-%dT%H:%M",
            attrs={"type": "datetime-local"},
        ),
    )
    expire_date = forms.DateTimeField(
        required=False,
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(
            format="%Y-%m-%dT%H:%M",
            attrs={"type": "datetime-local"},
        ),
    )

    class Meta:
        model = Wedding
        fields = [
            "name",
            "slug",
            "bride_name",
            "groom_name",
            "start_date",
            "wedding_date",
            "expire_date",
            "status",
            "timezone",
            "wedding_location",
            "google_maps_url",
            "guest_limit",
            "photo_limit",
            "print_limit",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Aung & Su Wedding"}),
            "slug": forms.TextInput(attrs={"placeholder": "aung-su-wedding"}),
            "bride_name": forms.TextInput(attrs={"placeholder": "Bride name"}),
            "groom_name": forms.TextInput(attrs={"placeholder": "Groom name"}),
            "start_date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "timezone": forms.TextInput(attrs={"placeholder": "Asia/Yangon"}),
            "wedding_location": forms.TextInput(attrs={"placeholder": "e.g. Novotel Yangon Max, Yangon"}),
            "google_maps_url": forms.URLInput(attrs={"placeholder": "https://maps.app.goo.gl/..."}),
            "guest_limit": forms.NumberInput(attrs={"min": 1}),
            "photo_limit": forms.NumberInput(attrs={"min": 0}),
            "print_limit": forms.NumberInput(attrs={"min": 0}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].choices = [
            (Wedding.Status.DRAFT, "Draft"),
            (Wedding.Status.ACTIVE, "Active"),
        ]

        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "premium-input")

    def clean(self):
        cleaned = super().clean()
        start_date = cleaned.get("start_date")
        wedding_date = cleaned.get("wedding_date")
        expire_date = cleaned.get("expire_date")

        if start_date and wedding_date:
            wedding_local_date = timezone.localtime(wedding_date).date()
            if start_date > wedding_local_date:
                self.add_error("start_date", "Start date cannot be after the wedding date.")

        if wedding_date and expire_date and expire_date <= wedding_date:
            self.add_error("expire_date", "Expire date must be after the wedding date.")

        return cleaned
