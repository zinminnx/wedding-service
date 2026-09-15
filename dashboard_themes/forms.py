from django import forms
from django.utils.text import slugify

from .models import DashboardTheme, UserDashboardPreference


class ThemePreferenceForm(forms.Form):
    theme_id = forms.IntegerField(min_value=1)
    density = forms.ChoiceField(choices=UserDashboardPreference.Density.choices)


class DashboardThemeForm(forms.ModelForm):
    class Meta:
        model = DashboardTheme
        fields = [
            "name",
            "key",
            "description",
            "is_active",
            "is_default",
            "sort_order",
            "sidebar_bg",
            "sidebar_text",
            "content_bg",
            "surface_bg",
            "accent",
            "text_color",
            "muted_color",
            "border_color",
            "heading_font",
            "body_font",
            "radius_px",
        ]
        widgets = {
            "description": forms.TextInput(attrs={"placeholder": "Short description"}),
            "sidebar_bg": forms.TextInput(attrs={"type": "color"}),
            "sidebar_text": forms.TextInput(attrs={"type": "color"}),
            "content_bg": forms.TextInput(attrs={"type": "color"}),
            "surface_bg": forms.TextInput(attrs={"type": "color"}),
            "accent": forms.TextInput(attrs={"type": "color"}),
            "text_color": forms.TextInput(attrs={"type": "color"}),
            "muted_color": forms.TextInput(attrs={"type": "color"}),
            "border_color": forms.TextInput(attrs={"type": "color"}),
            "radius_px": forms.NumberInput(attrs={"min": "0", "max": "40"}),
        }

    def clean_key(self):
        key = slugify(self.cleaned_data.get("key") or "")
        if not key:
            raise forms.ValidationError("Theme key is required.")
        return key

    def clean_radius_px(self):
        value = self.cleaned_data.get("radius_px")
        if value is None:
            return 14
        if value > 40:
            raise forms.ValidationError("Radius must be 40px or less.")
        return value
