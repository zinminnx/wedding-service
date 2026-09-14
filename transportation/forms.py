from django import forms

from .models import WeddingTransportationSettings


class WeddingTransportationSettingsForm(forms.ModelForm):
    class Meta:
        model = WeddingTransportationSettings
        fields = [
            "guide_enabled",
            "bus_guide_enabled",
            "provider",
            "transport_note",
            "fallback_message",
        ]
        widgets = {
            "transport_note": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Optional travel note, parking note, shuttle note, taxi instruction...",
                }
            ),
            "fallback_message": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_fallback_message(self):
        value = (self.cleaned_data.get("fallback_message") or "").strip()
        return value or "Bus route information is temporarily unavailable. Please use the map and venue details above."
