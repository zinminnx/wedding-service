from django import forms
from django.contrib.auth import get_user_model

from staffing.models import WeddingStaffMembership

from .models import PlannerAppointment, PlannerNote, PlannerTask, RunSheetItem


User = get_user_model()


def _team_queryset(wedding):
    if wedding is None:
        return User.objects.none()
    user_ids = list(
        WeddingStaffMembership.objects.filter(
            wedding=wedding,
            status=WeddingStaffMembership.Status.ACTIVE,
        ).values_list("user_id", flat=True)
    )
    user_ids.append(wedding.owner_id)
    return User.objects.filter(pk__in=user_ids).order_by("first_name", "username")


class WeddingTeamFormMixin:
    def __init__(self, *args, wedding=None, **kwargs):
        self.wedding = wedding
        super().__init__(*args, **kwargs)
        if "assigned_to" in self.fields:
            self.fields["assigned_to"].queryset = _team_queryset(wedding)
            self.fields["assigned_to"].required = False
            self.fields["assigned_to"].empty_label = "Unassigned"


class PlannerTaskForm(WeddingTeamFormMixin, forms.ModelForm):
    class Meta:
        model = PlannerTask
        fields = ["title", "kind", "status", "priority", "due_at", "reminder_at", "assigned_to", "description"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "e.g. Confirm ceremony timeline"}),
            "due_at": forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}),
            "reminder_at": forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}),
            "description": forms.Textarea(attrs={"rows": 5, "placeholder": "Instructions, dependencies or notes..."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["due_at"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["reminder_at"].input_formats = ["%Y-%m-%dT%H:%M"]


class PlannerAppointmentForm(WeddingTeamFormMixin, forms.ModelForm):
    class Meta:
        model = PlannerAppointment
        fields = ["title", "starts_at", "ends_at", "location", "assigned_to", "reminder_at", "notes"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "e.g. Venue walkthrough"}),
            "starts_at": forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}),
            "ends_at": forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}),
            "reminder_at": forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}),
            "location": forms.TextInput(attrs={"placeholder": "Venue / office / online"}),
            "notes": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("starts_at", "ends_at", "reminder_at"):
            self.fields[name].input_formats = ["%Y-%m-%dT%H:%M"]


class PlannerNoteForm(forms.ModelForm):
    class Meta:
        model = PlannerNote
        fields = ["title", "body", "is_pinned"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Note title"}),
            "body": forms.Textarea(attrs={"rows": 9, "placeholder": "Planning notes..."}),
        }


class RunSheetItemForm(forms.ModelForm):
    class Meta:
        model = RunSheetItem
        fields = ["scheduled_at", "title", "location", "owner_label", "status", "notes"]
        widgets = {
            "scheduled_at": forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}),
            "title": forms.TextInput(attrs={"placeholder": "e.g. Couple entrance"}),
            "location": forms.TextInput(attrs={"placeholder": "Ballroom / reception / stage"}),
            "owner_label": forms.TextInput(attrs={"placeholder": "MC / Planner / Reception"}),
            "notes": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["scheduled_at"].input_formats = ["%Y-%m-%dT%H:%M"]
