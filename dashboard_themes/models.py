from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models


hex_color = RegexValidator(
    regex=r"^#[0-9A-Fa-f]{6}$",
    message="Use a 6-digit hex color such as #0F172A.",
)


class DashboardTheme(models.Model):
    key = models.SlugField(max_length=64, unique=True)
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    is_default = models.BooleanField(default=False, db_index=True)
    sort_order = models.PositiveSmallIntegerField(default=100)

    sidebar_bg = models.CharField(max_length=7, default="#111827", validators=[hex_color])
    sidebar_text = models.CharField(max_length=7, default="#F8FAFC", validators=[hex_color])
    content_bg = models.CharField(max_length=7, default="#F7F3EA", validators=[hex_color])
    surface_bg = models.CharField(max_length=7, default="#FFFFFF", validators=[hex_color])
    accent = models.CharField(max_length=7, default="#C9A35D", validators=[hex_color])
    text_color = models.CharField(max_length=7, default="#1F2937", validators=[hex_color])
    muted_color = models.CharField(max_length=7, default="#6B7280", validators=[hex_color])
    border_color = models.CharField(max_length=7, default="#E5E0D8", validators=[hex_color])
    heading_font = models.CharField(max_length=120, default="Georgia, serif")
    body_font = models.CharField(max_length=120, default="Arial, sans-serif")
    radius_px = models.PositiveSmallIntegerField(default=14)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]

    def save(self, *args, **kwargs):
        if self.is_default:
            self.is_active = True
        super().save(*args, **kwargs)
        if self.is_default:
            DashboardTheme.objects.exclude(pk=self.pk).filter(is_default=True).update(is_default=False)

    def __str__(self):
        return self.name


class UserDashboardPreference(models.Model):
    class Density(models.TextChoices):
        COMFORTABLE = "COMFORTABLE", "Comfortable"
        COMPACT = "COMPACT", "Compact"
        SPACIOUS = "SPACIOUS", "Spacious"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dashboard_preference",
    )
    theme = models.ForeignKey(
        DashboardTheme,
        on_delete=models.PROTECT,
        related_name="user_preferences",
        null=True,
        blank=True,
    )
    density = models.CharField(
        max_length=16,
        choices=Density.choices,
        default=Density.COMFORTABLE,
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} dashboard preference"
