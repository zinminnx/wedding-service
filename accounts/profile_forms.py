from django import forms

from .models import User


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "phone")
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "ea-profile-input", "autocomplete": "given-name"}),
            "last_name": forms.TextInput(attrs={"class": "ea-profile-input", "autocomplete": "family-name"}),
            "email": forms.EmailInput(attrs={"class": "ea-profile-input", "autocomplete": "email"}),
            "phone": forms.TextInput(attrs={"class": "ea-profile-input", "autocomplete": "tel"}),
        }

    def clean_phone(self):
        value = (self.cleaned_data.get("phone") or "").strip()
        return value or None
