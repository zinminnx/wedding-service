import re

from django import forms
from django.db.models import Sum

from .models import Guest, GuestGroup


def _normalize_phone(value):
    return "".join(re.findall(r"\d+", value or ""))


def _normalize_email(value):
    return (value or "").strip().lower()


def _normalize_name(value):
    return " ".join((value or "").strip().lower().split())


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
        self.duplicate_warnings = []
        self.duplicate_matches = []
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

        self._build_duplicate_warnings(cleaned)
        return cleaned

    def _build_duplicate_warnings(self, cleaned):
        name = _normalize_name(cleaned.get("name"))
        phone = _normalize_phone(cleaned.get("phone"))
        email = _normalize_email(cleaned.get("email"))
        selected_group = cleaned.get("group")
        new_group_name = (cleaned.get("new_group") or "").strip()

        intended_group_id = selected_group.id if selected_group else None
        intended_group_name = selected_group.name if selected_group else "No group"
        if new_group_name:
            existing_group = GuestGroup.objects.filter(
                wedding=self.wedding,
                name__iexact=new_group_name,
            ).first()
            intended_group_id = existing_group.id if existing_group else None
            intended_group_name = new_group_name

        candidates = Guest.objects.filter(wedding=self.wedding).select_related("group")
        if self.instance and self.instance.pk:
            candidates = candidates.exclude(pk=self.instance.pk)

        phone_matches = []
        email_matches = []
        identity_matches = []
        group_identity_matches = []

        for candidate in candidates:
            candidate_name = _normalize_name(candidate.name)
            candidate_phone = _normalize_phone(candidate.phone)
            candidate_email = _normalize_email(candidate.email)

            same_phone = bool(phone and candidate_phone and phone == candidate_phone)
            same_email = bool(email and candidate_email and email == candidate_email)
            same_identity = bool(name and phone and candidate_name == name and same_phone)
            same_group_identity = bool(
                same_identity
                and intended_group_id is not None
                and candidate.group_id == intended_group_id
            )

            if same_phone:
                phone_matches.append(candidate)
            if same_email:
                email_matches.append(candidate)
            if same_identity:
                identity_matches.append(candidate)
            if same_group_identity:
                group_identity_matches.append(candidate)

        def names(items):
            return ", ".join(item.name for item in items[:4]) + ("…" if len(items) > 4 else "")

        warnings = []
        if group_identity_matches:
            warnings.append(
                f"Possible duplicate guest: same name, phone and group ({intended_group_name}) already exists: {names(group_identity_matches)}."
            )
        elif identity_matches:
            warnings.append(
                f"Strong duplicate warning: the same name and phone already exists: {names(identity_matches)}."
            )

        if phone_matches:
            warnings.append(f"This phone number is already used by: {names(phone_matches)}.")
        if email_matches:
            warnings.append(f"This email address is already used by: {names(email_matches)}.")

        # Keep warnings informational: duplicates are allowed after explicit confirmation.
        self.duplicate_warnings = warnings
        seen = set()
        matches = []
        for item in group_identity_matches + identity_matches + phone_matches + email_matches:
            if item.pk not in seen:
                seen.add(item.pk)
                matches.append(item)
        self.duplicate_matches = matches[:6]

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
