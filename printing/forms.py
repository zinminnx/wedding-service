from django import forms

from photos.models import WeddingPhoto

from .models import PrintJob, WeddingPrintSettings


class PrintJobForm(forms.ModelForm):
    class Meta:
        model = PrintJob
        fields = ["photo", "copies", "paper_size", "fit_mode", "notes"]
        widgets = {
            "copies": forms.NumberInput(attrs={"min": "1", "max": "99", "step": "1"}),
            "notes": forms.TextInput(attrs={"maxlength": "255", "placeholder": "Optional print note..."}),
        }

    def __init__(self, *args, wedding=None, **kwargs):
        self.wedding = wedding
        super().__init__(*args, **kwargs)
        if wedding:
            self.fields["photo"].queryset = WeddingPhoto.objects.filter(
                wedding=wedding,
                status=WeddingPhoto.Status.APPROVED,
            ).order_by("-created_at")
        else:
            self.fields["photo"].queryset = WeddingPhoto.objects.none()
        self.fields["photo"].label_from_instance = lambda photo: (
            f"{photo.public_id} - {photo.guest.name if photo.guest_id and photo.guest else photo.get_source_display()}"
        )

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        if photo and self.wedding and photo.wedding_id != self.wedding.id:
            raise forms.ValidationError("This photo does not belong to the selected wedding.")
        if photo and photo.status != WeddingPhoto.Status.APPROVED:
            raise forms.ValidationError("Only approved photos can be printed.")
        return photo

    def save(self, commit=True):
        job = super().save(commit=False)
        job.wedding = self.wedding
        if commit:
            job.save()
        return job


class WeddingPrintSettingsForm(forms.ModelForm):
    class Meta:
        model = WeddingPrintSettings
        fields = ["queue_enabled", "queue_paused", "default_copies", "default_paper_size"]
        widgets = {
            "default_copies": forms.NumberInput(attrs={"min": "1", "max": "99", "step": "1"}),
        }
