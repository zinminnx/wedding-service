import re

from django import forms


HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


class InvitationCustomizationForm(forms.Form):
    accent = forms.CharField(
        required=False,
        max_length=7,
        widget=forms.TextInput(attrs={"type": "color"}),
        help_text="Optional accent color override for this wedding.",
    )
    hero_message = forms.CharField(
        required=False,
        max_length=140,
        widget=forms.TextInput(attrs={"placeholder": "A new chapter, together."}),
        help_text="Short message shown under the invitation hero.",
    )

    def __init__(self, *args, theme=None, **kwargs):
        self.theme = theme
        super().__init__(*args, **kwargs)
        allowed = set((theme.allowed_customization if theme else []) or [])
        if "accent" not in allowed:
            self.fields.pop("accent", None)
        if "hero_message" not in allowed:
            self.fields.pop("hero_message", None)

    def clean_accent(self):
        value = (self.cleaned_data.get("accent") or "").strip()
        if value and not HEX_RE.fullmatch(value):
            raise forms.ValidationError("Choose a valid hex color.")
        return value
