import os
import uuid

from django.db import models


def gift_qr_upload_to(instance, filename):
    ext = os.path.splitext(filename)[1].lower() or ".img"
    wedding_id = instance.wedding.public_id if instance.wedding_id else "unassigned"
    return f"weddings/{wedding_id}/gift_qr/{uuid.uuid4().hex}{ext}"


class GiftSettings(models.Model):
    class ReturnGiftMode(models.TextChoices):
        NONE = "NONE", "No return gift"
        PER_INVITATION = "PER_INVITATION", "One per invitation"
        PER_ATTENDEE = "PER_ATTENDEE", "One per checked-in guest"
        CUSTOM = "CUSTOM", "Custom quantity"

    wedding = models.OneToOneField(
        "weddings.Wedding",
        on_delete=models.CASCADE,
        related_name="gift_settings",
    )

    accept_monetary_gift = models.BooleanField(default=True)
    accept_physical_gift = models.BooleanField(default=True)
    allow_no_gift = models.BooleanField(default=True)

    # Legacy v6 fields retained so upgrading does not destroy existing data.
    # The v6.2 UI uses GiftPaymentMethod instead.
    kbzpay_enabled = models.BooleanField(default=False)
    kbzpay_account_name = models.CharField(max_length=120, blank=True)
    kbzpay_qr = models.FileField(upload_to=gift_qr_upload_to, blank=True)
    ayapay_enabled = models.BooleanField(default=False)
    ayapay_account_name = models.CharField(max_length=120, blank=True)
    ayapay_qr = models.FileField(upload_to=gift_qr_upload_to, blank=True)

    return_gift_mode = models.CharField(
        max_length=24,
        choices=ReturnGiftMode.choices,
        default=ReturnGiftMode.PER_INVITATION,
    )
    return_gift_name = models.CharField(max_length=120, blank=True)
    return_gift_stock = models.PositiveIntegerField(default=0)
    custom_return_gift_quantity = models.PositiveSmallIntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Gift settings - {self.wedding.name}"


class GiftPaymentMethod(models.Model):
    class MethodType(models.TextChoices):
        PAY = "PAY", "Mobile Pay"
        BANK = "BANK", "Bank Account"

    wedding = models.ForeignKey(
        "weddings.Wedding",
        on_delete=models.CASCADE,
        related_name="gift_payment_methods",
    )
    method_type = models.CharField(max_length=12, choices=MethodType.choices)
    name = models.CharField(max_length=80, help_text="e.g. KBZPay, Wave Pay, AYA Bank")
    account_name = models.CharField(max_length=120)
    phone_number = models.CharField(max_length=40, blank=True)
    account_number = models.CharField(max_length=80, blank=True)
    qr_image = models.FileField(upload_to=gift_qr_upload_to, blank=True)
    is_enabled = models.BooleanField(default=True, db_index=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["wedding", "name"],
                name="unique_gift_payment_method_name_per_wedding",
            )
        ]

    def __str__(self):
        return f"{self.name} - {self.wedding.name}"


class GuestGiftDeclaration(models.Model):
    class GiftChoice(models.TextChoices):
        NONE = "NONE", "No gift"
        DIGITAL = "DIGITAL", "Digital gift"
        PHYSICAL = "PHYSICAL", "Physical gift"

    class PaymentStatus(models.TextChoices):
        NOT_REQUIRED = "NOT_REQUIRED", "Not required"
        GUEST_SENT = "GUEST_SENT", "Guest says sent"
        VERIFIED = "VERIFIED", "Verified"
        REJECTED = "REJECTED", "Rejected"

    wedding = models.ForeignKey(
        "weddings.Wedding",
        on_delete=models.CASCADE,
        related_name="gift_declarations",
    )
    guest = models.OneToOneField(
        "guests.Guest",
        on_delete=models.CASCADE,
        related_name="gift_declaration",
    )
    invitation = models.OneToOneField(
        "invitations.Invitation",
        on_delete=models.CASCADE,
        related_name="gift_declaration",
    )

    gift_choice = models.CharField(
        max_length=16,
        choices=GiftChoice.choices,
        default=GiftChoice.NONE,
    )
    payment_method_record = models.ForeignKey(
        GiftPaymentMethod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="declarations",
    )
    # Snapshot/legacy label. Existing v6 values remain valid.
    payment_method = models.CharField(max_length=120, blank=True, default="")
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    payment_reference = models.CharField(max_length=120, blank=True)
    payment_status = models.CharField(
        max_length=16,
        choices=PaymentStatus.choices,
        default=PaymentStatus.NOT_REQUIRED,
        db_index=True,
    )
    notes = models.CharField(max_length=255, blank=True)

    declared_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(
                fields=["wedding", "payment_status"],
                name="gift_wedding_status_idx",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.gift_choice != self.GiftChoice.DIGITAL:
            self.payment_method_record = None
            self.payment_method = ""
            self.amount = None
            self.payment_reference = ""
            self.payment_status = self.PaymentStatus.NOT_REQUIRED
        else:
            if self.payment_method_record_id:
                self.payment_method = self.payment_method_record.name
            if self.payment_status == self.PaymentStatus.NOT_REQUIRED:
                self.payment_status = self.PaymentStatus.GUEST_SENT
        super().save(*args, **kwargs)

    @property
    def payment_method_label(self):
        if self.payment_method_record_id:
            return self.payment_method_record.name
        return self.payment_method or "—"

    def __str__(self):
        return f"{self.guest.name} - {self.get_gift_choice_display()}"
