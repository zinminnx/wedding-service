from django import forms

from .models import WeddingEventSettings


class WeddingEventSettingsForm(forms.ModelForm):
    class Meta:
        model = WeddingEventSettings
        fields = [
            "calendar_enabled",
            "calendar_title",
            "calendar_description",
            "event_duration_minutes",
            "reminder_1_minutes",
            "reminder_2_minutes",
            "reminder_3_minutes",
            "venue_enabled",
            "smart_map_enabled",
            "show_google_maps",
            "show_apple_maps",
            "show_address",
            "show_landmark",
            "show_location_note",
        ]
        widgets = {
            "calendar_description": forms.Textarea(attrs={"rows": 4}),
            "event_duration_minutes": forms.NumberInput(attrs={"min": 15, "max": 1440, "step": 15}),
            "reminder_1_minutes": forms.NumberInput(attrs={"min": 0}),
            "reminder_2_minutes": forms.NumberInput(attrs={"min": 0}),
            "reminder_3_minutes": forms.NumberInput(attrs={"min": 0}),
        }

    def clean_event_duration_minutes(self):
        value = self.cleaned_data.get("event_duration_minutes") or 240
        if value < 15 or value > 1440:
            raise forms.ValidationError("Event duration must be between 15 and 1440 minutes.")
        return value
