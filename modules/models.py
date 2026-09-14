from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class FeatureModule(models.Model):
    class ModuleType(models.TextChoices):
        CORE = "CORE", "Core"
        OPTIONAL = "OPTIONAL", "Optional"

    key = models.SlugField(max_length=64, unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    version = models.CharField(max_length=32, default="1.0")
    module_type = models.CharField(
        max_length=12,
        choices=ModuleType.choices,
        default=ModuleType.OPTIONAL,
    )
    system_enabled = models.BooleanField(default=True)
    visible_to_weddings = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=100)
    allowed_roles = models.JSONField(default=list, blank=True)
    dependencies = models.ManyToManyField(
        "self",
        symmetrical=False,
        blank=True,
        related_name="dependent_modules",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]

    @property
    def is_core(self):
        return self.module_type == self.ModuleType.CORE

    def clean(self):
        super().clean()
        if self.is_core and not self.system_enabled:
            raise ValidationError({"system_enabled": "Core modules cannot be disabled."})

    def save(self, *args, **kwargs):
        if self.is_core:
            self.system_enabled = True
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ServicePackage(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=64, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    modules = models.ManyToManyField(
        FeatureModule,
        blank=True,
        related_name="service_packages",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_default:
            ServicePackage.objects.exclude(pk=self.pk).filter(is_default=True).update(is_default=False)

    def __str__(self):
        return self.name


class WeddingModuleProfile(models.Model):
    wedding = models.OneToOneField(
        "weddings.Wedding",
        on_delete=models.CASCADE,
        related_name="module_profile",
    )
    package = models.ForeignKey(
        ServicePackage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="wedding_profiles",
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        package_name = self.package.name if self.package_id else "No package"
        return f"{self.wedding} - {package_name}"


class WeddingModuleSetting(models.Model):
    wedding = models.ForeignKey(
        "weddings.Wedding",
        on_delete=models.CASCADE,
        related_name="module_settings",
    )
    module = models.ForeignKey(
        FeatureModule,
        on_delete=models.CASCADE,
        related_name="wedding_settings",
    )
    enabled = models.BooleanField(default=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_wedding_module_settings",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["wedding", "module"],
                name="unique_wedding_module_setting",
            )
        ]
        indexes = [
            models.Index(fields=["wedding", "enabled"], name="wed_module_enabled_idx"),
        ]

    def __str__(self):
        return f"{self.wedding} - {self.module.key}: {'On' if self.enabled else 'Off'}"
