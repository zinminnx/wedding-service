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

    def __str__(self):
        return self.username