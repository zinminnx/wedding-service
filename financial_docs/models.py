import os
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


def financial_upload_to(instance, filename):
    ext = os.path.splitext(filename)[1].lower() or ".bin"
    wedding_id = instance.wedding.public_id if instance.wedding_id else "unassigned"
    return f"weddings/{wedding_id}/financial/{uuid.uuid4().hex}{ext}"


class FinancialDocument(models.Model):
    class DocumentType(models.TextChoices):
        RECEIPT = "RECEIPT", "Receipt"
        INVOICE = "INVOICE", "Invoice"
        QUOTATION = "QUOTATION", "Quotation"
        CONTRACT = "CONTRACT", "Contract"
        PAYMENT_PROOF = "PAYMENT_PROOF", "Payment Proof"
        OTHER = "OTHER", "Other"

    class Visibility(models.TextChoices):
        PRIVATE = "PRIVATE", "Private to Owner / Manager"
        SHARED = "SHARED", "Shared with Planner"

    wedding = models.ForeignKey(
        "weddings.Wedding",
        on_delete=models.CASCADE,
        related_name="financial_documents",
    )
    budget_item = models.ForeignKey(
        "budgeting.BudgetItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="financial_documents",
    )
    vendor_quote = models.ForeignKey(
        "vendors.VendorQuote",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="financial_documents",
    )
    source_label = models.CharField(max_length=220, blank=True)
    document_type = models.CharField(max_length=24, choices=DocumentType.choices)
    title = models.CharField(max_length=180)
    file = models.FileField(upload_to=financial_upload_to)
    original_name = models.CharField(max_length=255, blank=True)
    file_size = models.PositiveBigIntegerField(default=0)
    visibility = models.CharField(
        max_length=16,
        choices=Visibility.choices,
        default=Visibility.PRIVATE,
        db_index=True,
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_financial_documents",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["wedding", "document_type"], name="findoc_wed_type_idx"),
            models.Index(fields=["wedding", "visibility"], name="findoc_wed_vis_idx"),
        ]

    def clean(self):
        errors = {}
        if self.budget_item_id and self.vendor_quote_id:
            errors["budget_item"] = "Choose either a Budget Item or a Vendor Quote, not both."
        if self.budget_item_id and self.wedding_id and self.budget_item.wedding_id != self.wedding_id:
            errors["budget_item"] = "Budget item must belong to the same wedding."
        if self.vendor_quote_id and self.wedding_id and self.vendor_quote.wedding_id != self.wedding_id:
            errors["vendor_quote"] = "Vendor quote must belong to the same wedding."
        if self.budget_item_id:
            from budgeting.models import BudgetItem
            if self.budget_item.visibility == BudgetItem.Visibility.PRIVATE:
                self.visibility = self.Visibility.PRIVATE
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        if self.file and not self.original_name:
            self.original_name = os.path.basename(getattr(self.file, "name", ""))[:255]
        if self.file:
            try:
                self.file_size = self.file.size
            except (AttributeError, OSError):
                pass
        if not self.source_label:
            if self.budget_item_id:
                self.source_label = self.budget_item.title
            elif self.vendor_quote_id:
                self.source_label = f"{self.vendor_quote.vendor.name} - {self.vendor_quote.title}"
        super().save(*args, **kwargs)

    @property
    def source_display(self):
        if self.budget_item_id:
            return self.budget_item.title
        if self.vendor_quote_id:
            return f"{self.vendor_quote.vendor.name} - {self.vendor_quote.title}"
        return self.source_label or "Archived source"

    def __str__(self):
        return f"{self.get_document_type_display()}: {self.title}"


class FinancialAuditEvent(models.Model):
    wedding = models.ForeignKey(
        "weddings.Wedding",
        on_delete=models.CASCADE,
        related_name="financial_audit_events",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="financial_audit_events",
    )
    action = models.CharField(max_length=64, db_index=True)
    entity_type = models.CharField(max_length=40)
    entity_id = models.CharField(max_length=64, blank=True)
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["wedding", "created_at"], name="finaudit_wed_time_idx")]

    def __str__(self):
        return f"{self.created_at}: {self.action}"
