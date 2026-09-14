import os
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
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

    # Kept as a compatibility total. From v9 onward, the live quantity is stored
    # in ReturnGiftInventory.quantity_on_hand and every change is ledgered.
    return_gift_stock = models.PositiveIntegerField(default=0)
    custom_return_gift_quantity = models.PositiveSmallIntegerField(default=1)
    return_gift_requires_checkin = models.BooleanField(default=True)
    return_gift_allow_staff_override = models.BooleanField(default=True)

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
    payment_method = models.CharField(max_length=120, blank=True, default="")
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    payment_reference = models.CharField(max_length=120, blank=True)
    payment_status = models.CharField(
        max_length=16,
        choices=PaymentStatus.choices,
        default=PaymentStatus.NOT_REQUIRED,
        db_index=True,
    )
    payment_reviewed_at = models.DateTimeField(null=True, blank=True)
    payment_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_guest_gift_declarations",
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
            self.payment_reviewed_at = None
            self.payment_reviewed_by = None
        else:
            if self.payment_method_record_id:
                self.payment_method = self.payment_method_record.name
            if self.payment_status == self.PaymentStatus.NOT_REQUIRED:
                self.payment_status = self.PaymentStatus.GUEST_SENT
            if self.payment_status == self.PaymentStatus.GUEST_SENT:
                self.payment_reviewed_at = None
                self.payment_reviewed_by = None
        super().save(*args, **kwargs)

    @property
    def payment_method_label(self):
        if self.payment_method_record_id:
            return self.payment_method_record.name
        return self.payment_method or "—"

    def __str__(self):
        return f"{self.guest.name} - {self.get_gift_choice_display()}"


class ReturnGiftInventory(models.Model):
    wedding = models.OneToOneField(
        "weddings.Wedding",
        on_delete=models.CASCADE,
        related_name="return_gift_inventory",
    )
    quantity_on_hand = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=10)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Return gift inventories"

    @property
    def is_low_stock(self):
        return self.quantity_on_hand <= self.low_stock_threshold

    def __str__(self):
        return f"{self.wedding.name}: {self.quantity_on_hand} on hand"


class ReturnGiftMovement(models.Model):
    class MovementType(models.TextChoices):
        OPENING = "OPENING", "Opening balance"
        RESTOCK = "RESTOCK", "Stock added"
        SET_STOCK = "SET_STOCK", "Stock corrected"
        ISSUE = "ISSUE", "Issued to guest"
        RETURN = "RETURN", "Returned to stock"

    wedding = models.ForeignKey(
        "weddings.Wedding",
        on_delete=models.CASCADE,
        related_name="return_gift_movements",
    )
    inventory = models.ForeignKey(
        ReturnGiftInventory,
        on_delete=models.CASCADE,
        related_name="movements",
    )
    guest = models.ForeignKey(
        "guests.Guest",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="return_gift_movements",
    )
    checkin = models.ForeignKey(
        "checkins.CheckIn",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="return_gift_movements",
    )
    movement_type = models.CharField(max_length=16, choices=MovementType.choices)
    quantity_delta = models.IntegerField()
    quantity_after = models.PositiveIntegerField()
    note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="return_gift_inventory_actions",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["wedding", "created_at"], name="returngift_wed_time_idx"),
        ]

    def clean(self):
        errors = {}
        if self.inventory_id and self.wedding_id and self.inventory.wedding_id != self.wedding_id:
            errors["inventory"] = "Inventory must belong to the same wedding."
        if self.guest_id and self.wedding_id and self.guest.wedding_id != self.wedding_id:
            errors["guest"] = "Guest must belong to the same wedding."
        if self.checkin_id and self.wedding_id and self.checkin.wedding_id != self.wedding_id:
            errors["checkin"] = "Check-in must belong to the same wedding."
        if self.quantity_delta == 0:
            errors["quantity_delta"] = "Inventory movement cannot be zero."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        sign = "+" if self.quantity_delta > 0 else ""
        return f"{self.get_movement_type_display()} {sign}{self.quantity_delta}"
