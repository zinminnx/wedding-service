from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models


ZERO = Decimal("0.00")


class WeddingBudgetSettings(models.Model):
    wedding = models.OneToOneField(
        "weddings.Wedding",
        on_delete=models.CASCADE,
        related_name="budget_settings",
    )
    total_budget = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    currency = models.CharField(max_length=8, default="MMK")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Wedding budget settings"
        verbose_name_plural = "Wedding budget settings"

    def clean(self):
        if self.total_budget is not None and self.total_budget < 0:
            raise ValidationError({"total_budget": "Total budget cannot be negative."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.wedding.name} budget"


class BudgetCategory(models.Model):
    wedding = models.ForeignKey(
        "weddings.Wedding",
        on_delete=models.CASCADE,
        related_name="budget_categories",
    )
    name = models.CharField(max_length=100)
    sort_order = models.PositiveSmallIntegerField(default=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["wedding", "name"],
                name="unique_budget_category_per_wedding",
            )
        ]

    def __str__(self):
        return self.name


class BudgetItem(models.Model):
    class Source(models.TextChoices):
        COUPLE = "COUPLE", "Couple Budget"
        PLANNER = "PLANNER", "Planner Budget"

    class Status(models.TextChoices):
        PLANNED = "PLANNED", "Planned"
        COMMITTED = "COMMITTED", "Committed"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        COMPLETE = "COMPLETE", "Complete"
        CANCELLED = "CANCELLED", "Cancelled"

    class Visibility(models.TextChoices):
        PRIVATE = "PRIVATE", "Private to Owner / Manager"
        SHARED = "SHARED", "Shared with Planner"

    wedding = models.ForeignKey(
        "weddings.Wedding",
        on_delete=models.CASCADE,
        related_name="budget_items",
    )
    category = models.ForeignKey(
        BudgetCategory,
        on_delete=models.PROTECT,
        related_name="items",
    )
    title = models.CharField(max_length=160)
    source = models.CharField(
        max_length=16,
        choices=Source.choices,
        default=Source.COUPLE,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNED,
        db_index=True,
    )
    visibility = models.CharField(
        max_length=16,
        choices=Visibility.choices,
        default=Visibility.PRIVATE,
        db_index=True,
        help_text="Private Couple expenses are hidden from Wedding Planner accounts.",
    )
    estimated_amount = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    committed_amount = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    final_actual_amount = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        null=True,
        blank=True,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category__sort_order", "category__name", "title"]
        indexes = [
            models.Index(fields=["wedding", "source"], name="budget_wed_source_idx"),
            models.Index(fields=["wedding", "status"], name="budget_wed_status_idx"),
            models.Index(fields=["wedding", "visibility"], name="budget_wed_vis_idx"),
        ]

    def clean(self):
        errors = {}
        if self.category_id and self.wedding_id and self.category.wedding_id != self.wedding_id:
            errors["category"] = "Budget category must belong to the same wedding."
        for field in ("estimated_amount", "committed_amount", "paid_amount", "final_actual_amount"):
            value = getattr(self, field, None)
            if value is not None and value < 0:
                errors[field] = "Amount cannot be negative."
        if self.source == self.Source.PLANNER and self.visibility != self.Visibility.SHARED:
            self.visibility = self.Visibility.SHARED
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def expected_amount(self):
        if self.status == self.Status.CANCELLED:
            return ZERO
        if self.final_actual_amount is not None:
            return self.final_actual_amount
        if self.committed_amount > ZERO:
            return self.committed_amount
        return self.estimated_amount

    @property
    def outstanding_amount(self):
        if self.status == self.Status.CANCELLED:
            return ZERO
        target = self.final_actual_amount if self.final_actual_amount is not None else self.committed_amount
        if target <= ZERO:
            return ZERO
        return max(target - self.paid_amount, ZERO)

    @property
    def variance_amount(self):
        return self.expected_amount - self.estimated_amount

    def __str__(self):
        return f"{self.title} - {self.wedding.name}"
