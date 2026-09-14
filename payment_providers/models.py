import os
import uuid

from django.db import models


def provider_logo_upload_to(instance, filename):
    ext = os.path.splitext(filename)[1].lower() or ".img"
    return f"payment_providers/{instance.key}/{uuid.uuid4().hex}{ext}"


class PaymentProvider(models.Model):
    class ProviderType(models.TextChoices):
        BANK = "BANK", "Bank"
        PAY = "PAY", "Mobile Pay"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        DISABLED = "DISABLED", "Disabled"

    key = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=120)
    short_name = models.CharField(max_length=60, blank=True)
    provider_type = models.CharField(max_length=12, choices=ProviderType.choices, db_index=True)
    logo = models.FileField(upload_to=provider_logo_upload_to, blank=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["provider_type", "sort_order", "name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider_type", "name"],
                name="unique_payment_provider_name_per_type",
            )
        ]

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE

    @property
    def display_name(self):
        return self.short_name or self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Keep the legacy GiftPaymentMethod snapshot fields synchronized so
        # existing invitation templates and exports still show standardized names.
        from gifts.models import GiftPaymentMethod

        GiftPaymentMethod.objects.filter(
            provider_link__provider=self
        ).update(name=self.name, method_type=self.provider_type)

    def __str__(self):
        return f"{self.name} ({self.get_provider_type_display()})"


class PaymentMethodProviderLink(models.Model):
    payment_method = models.OneToOneField(
        "gifts.GiftPaymentMethod",
        on_delete=models.CASCADE,
        related_name="provider_link",
    )
    provider = models.ForeignKey(
        PaymentProvider,
        on_delete=models.PROTECT,
        related_name="payment_accounts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["payment_method_id"]

    def __str__(self):
        return f"{self.payment_method} -> {self.provider}"
