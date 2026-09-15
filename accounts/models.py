from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
        ADMIN = "ADMIN", "Admin"
        WEDDING_OWNER = "WEDDING_OWNER", "Wedding Owner"
        WEDDING_MANAGER = "WEDDING_MANAGER", "Wedding Manager"
        RECEPTION_STAFF = "RECEPTION_STAFF", "Reception Staff"
        PHOTO_STAFF = "PHOTO_STAFF", "Photo Staff"
        PRINT_STAFF = "PRINT_STAFF", "Print Staff"
        VIEWER = "VIEWER", "Viewer"

    role = models.CharField(
        max_length=30,
        choices=Role.choices,
        default=Role.VIEWER,
    )

    phone = models.CharField(
        max_length=30,
        unique=True,
        null=True,
        blank=True,
    )

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = self.Role.SUPER_ADMIN

        super().save(*args, **kwargs)

    @property
    def has_profile_image(self):
        try:
            asset = self.profile_image_asset
        except Exception:
            return False
        return bool(getattr(asset, "remote_item_id", ""))

    def __str__(self):
        return self.username

class ProfileImageAsset(models.Model):
    """OneDrive metadata for a user's profile photo. No original file is stored on the VPS."""
    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="profile_image_asset",
    )
    drive_id = models.CharField(max_length=180)
    remote_item_id = models.CharField(max_length=255, db_index=True)
    remote_path = models.CharField(max_length=700)
    remote_web_url = models.URLField(max_length=1000, blank=True)
    mime_type = models.CharField(max_length=120, blank=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    sha256 = models.CharField(max_length=64, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user_id"]

    def __str__(self):
        return f"Profile image - {self.user.username}"
