from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import WeddingStaffMembership


User = get_user_model()


def _filtered_role_choices(allowed_roles=None):
    choices = list(WeddingStaffMembership.Role.choices)
    if allowed_roles is None:
        return choices
    allowed = set(allowed_roles)
    return [(value, label) for value, label in choices if value in allowed]


class StaffCreateForm(forms.Form):
    username = forms.CharField(max_length=150)
    email = forms.EmailField(required=False)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    phone = forms.CharField(max_length=40, required=False)
    role = forms.ChoiceField(choices=WeddingStaffMembership.Role.choices)
    password = forms.CharField(
        required=False,
        min_length=8,
        widget=forms.PasswordInput(render_value=False),
        help_text="Required only when creating a brand-new account.",
    )

    existing_user = None

    def __init__(self, *args, allowed_roles=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].choices = _filtered_role_choices(allowed_roles)

    def clean(self):
        cleaned = super().clean()
        username = (cleaned.get("username") or "").strip()
        email = (cleaned.get("email") or "").strip()

        matches = User.objects.filter(Q(username__iexact=username))
        if email:
            matches = User.objects.filter(Q(username__iexact=username) | Q(email__iexact=email))
        users = list(matches.distinct()[:2])
        if len(users) > 1:
            raise forms.ValidationError("Username and email match different existing accounts.")

        self.existing_user = users[0] if users else None
        if self.existing_user is None and not cleaned.get("password"):
            self.add_error("password", "Password is required for a new staff account.")
        return cleaned


class StaffMembershipForm(forms.ModelForm):
    class Meta:
        model = WeddingStaffMembership
        fields = ["role", "status"]

    def __init__(self, *args, allowed_roles=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].choices = _filtered_role_choices(allowed_roles)
