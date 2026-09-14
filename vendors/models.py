from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


ZERO = Decimal("0.00")


class Vendor(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"

    wedding = models.ForeignKey(
        "weddings.Wedding",
        on_delete=models.CASCADE,
        related_name="vendors",
    )
    name = models.CharField(max_length=180)
    category = models.ForeignKey(
        "budgeting.BudgetCategory",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="vendors",
    )
    contact_person = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_wedding_vendors",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["wedding", "status"], name="vendor_wed_status_idx")]

    def clean(self):
        if self.category_id and self.wedding_id and self.category.wedding_id != self.wedding_id:
            raise ValidationError({"category": "Vendor category must belong to the same wedding."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.wedding.name}"


class VendorQuote(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PROPOSED = "PROPOSED", "Proposed to Owner"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        WITHDRAWN = "WITHDRAWN", "Withdrawn"

    wedding = models.ForeignKey(
        "weddings.Wedding",
        on_delete=models.CASCADE,
        related_name="vendor_quotes",
    )
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name="quotes")
    category = models.ForeignKey(
        "budgeting.BudgetCategory",
        on_delete=models.PROTECT,
        related_name="vendor_quotes",
    )
    title = models.CharField(max_length=180)
    comparison_group = models.CharField(
        max_length=120,
        blank=True,
        help_text="Use the same group name for alternative quotes, e.g. Photographer.",
    )
    quoted_amount = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    deposit_amount = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    final_amount = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT, db_index=True)
    proposed_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_vendor_quotes",
    )
    rejection_reason = models.CharField(max_length=255, blank=True)
    approved_budget_item = models.OneToOneField(
        "budgeting.BudgetItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vendor_quote",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_vendor_quotes",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]
        indexes = [
            models.Index(fields=["wedding", "status"], name="quote_wed_status_idx"),
            models.Index(fields=["wedding", "comparison_group"], name="quote_wed_group_idx"),
        ]

    def clean(self):
        errors = {}
        if self.vendor_id and self.wedding_id and self.vendor.wedding_id != self.wedding_id:
            errors["vendor"] = "Vendor must belong to the same wedding."
        if self.category_id and self.wedding_id and self.category.wedding_id != self.wedding_id:
            errors["category"] = "Budget category must belong to the same wedding."
        for field in ("quoted_amount", "deposit_amount", "final_amount"):
            value = getattr(self, field, None)
            if value is not None and value < ZERO:
                errors[field] = "Amount cannot be negative."
        if self.deposit_amount and self.quoted_amount and self.deposit_amount > self.quoted_amount:
            errors["deposit_amount"] = "Deposit cannot be greater than the quoted amount."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def committed_amount(self):
        return self.final_amount if self.final_amount is not None else self.quoted_amount

    def __str__(self):
        return f"{self.vendor.name}: {self.title}"
