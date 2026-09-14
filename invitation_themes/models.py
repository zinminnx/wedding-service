import re
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .sections import REQUIRED_THEME_SECTIONS


def preview_upload_to(instance, filename):
    suffix = Path(filename).suffix.lower()
    if len(suffix) > 10:
        suffix = ""
    return f"invitation-themes/{instance.key}/preview{suffix}"


class InvitationTheme(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"
        DISABLED = "DISABLED", "Disabled"

    class Category(models.TextChoices):
        CLASSIC = "CLASSIC", "Classic"
        MODERN = "MODERN", "Modern"
        FLORAL = "FLORAL", "Floral"
        LUXURY = "LUXURY", "Luxury"
        ROMANTIC = "ROMANTIC", "Romantic"
        PHOTO = "PHOTO", "Photo"
        TRADITIONAL = "TRADITIONAL", "Traditional"
        EDITORIAL = "EDITORIAL", "Editorial"
        ROYAL = "ROYAL", "Royal"
        ELEGANT = "ELEGANT", "Elegant"

    name = models.CharField(max_length=120)
    key = models.SlugField(max_length=64, unique=True)
    category = models.CharField(max_length=24, choices=Category.choices, default=Category.CLASSIC)
    description = models.TextField(blank=True)
    preview_image = models.FileField(upload_to=preview_upload_to, blank=True, null=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT, db_index=True)
    visible = models.BooleanField(default=False)
    featured = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=100)
    is_default = models.BooleanField(default=False)
    version = models.CharField(max_length=32, default="1.0")
    layout_key = models.SlugField(max_length=64, default="classic")
    config = models.JSONField(default=dict, blank=True)
    allowed_customization = models.JSONField(default=list, blank=True)
    supported_sections = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        indexes = [
            models.Index(fields=["status", "visible", "sort_order"], name="invtheme_status_vis_idx"),
        ]

    def clean(self):
        super().clean()
        if self.status == self.Status.PUBLISHED:
            missing = REQUIRED_THEME_SECTIONS.difference(set(self.supported_sections or []))
            if missing:
                raise ValidationError({
                    "supported_sections": "Published themes must support: " + ", ".join(sorted(missing))
                })
        accent = (self.config or {}).get("accent")
        if accent and not re.fullmatch(r"#[0-9A-Fa-f]{6}", str(accent)):
            raise ValidationError({"config": "Theme accent must be a six-digit hex color."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        if self.is_default:
            InvitationTheme.objects.exclude(pk=self.pk).filter(is_default=True).update(is_default=False)

    def __str__(self):
        return f"{self.name} v{self.version}"


class WeddingInvitationDesign(models.Model):
    wedding = models.OneToOneField(
        "weddings.Wedding",
        on_delete=models.CASCADE,
        related_name="invitation_design",
    )
    draft_theme = models.ForeignKey(
        InvitationTheme,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="draft_wedding_designs",
    )
    published_theme = models.ForeignKey(
        InvitationTheme,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="published_wedding_designs",
    )
    draft_customization = models.JSONField(default=dict, blank=True)
    published_customization = models.JSONField(default=dict, blank=True)
    draft_sections = models.JSONField(default=list, blank=True)
    published_sections = models.JSONField(default=list, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_invitation_designs",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Wedding invitation design"
        verbose_name_plural = "Wedding invitation designs"

    def __str__(self):
        return f"Invitation design - {self.wedding}"
