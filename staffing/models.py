from django.conf import settings
from django.db import models


class WeddingStaffMembership(models.Model):
    class Role(models.TextChoices):
        WEDDING_MANAGER = "WEDDING_MANAGER", "Wedding Manager"
        RECEPTION_STAFF = "RECEPTION_STAFF", "Reception Staff"
        PHOTO_STAFF = "PHOTO_STAFF", "Photo Staff"
        PRINT_STAFF = "PRINT_STAFF", "Print Staff"
        VIEWER = "VIEWER", "Viewer"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"

    wedding = models.ForeignKey(
        "weddings.Wedding",
        on_delete=models.CASCADE,
        related_name="staff_memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wedding_memberships",
    )
    role = models.CharField(max_length=32, choices=Role.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_wedding_staff_memberships",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["role", "user__username"]
        constraints = [
            models.UniqueConstraint(
                fields=["wedding", "user"],
                name="unique_wedding_staff_membership",
            )
        ]
        indexes = [
            models.Index(fields=["wedding", "status"]),
            models.Index(fields=["user", "status"]),
        ]

    def __str__(self):
        return f"{self.wedding} - {self.user} ({self.get_role_display()})"
