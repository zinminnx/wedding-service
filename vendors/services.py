from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from budgeting.models import BudgetItem

from .models import VendorQuote


ZERO = Decimal("0.00")


def can_owner_review(user, wedding):
    return bool(
        getattr(user, "is_authenticated", False)
        and (getattr(user, "is_superuser", False) or wedding.owner_id == user.id)
    )


def _audit(quote, user, action, message):
    try:
        from financial_docs.services import log_financial_event
        log_financial_event(
            wedding=quote.wedding,
            actor=user,
            action=action,
            entity_type="VENDOR_QUOTE",
            entity_id=str(quote.pk),
            message=message,
        )
    except Exception:
        # Financial audit must never break an approved/rejected vendor decision.
        pass


@transaction.atomic
def approve_quote(quote, user):
    quote = (
        VendorQuote.objects.select_for_update()
        .select_related("wedding", "vendor", "category", "approved_budget_item")
        .get(pk=quote.pk)
    )
    if quote.status != VendorQuote.Status.PROPOSED:
        raise ValueError("Only proposed quotes can be approved.")
    if not can_owner_review(user, quote.wedding):
        raise PermissionError("Only the Wedding Owner can approve planner estimates.")

    budget_item = quote.approved_budget_item
    if budget_item is None:
        budget_item = BudgetItem(
            wedding=quote.wedding,
            category=quote.category,
            title=f"{quote.vendor.name} - {quote.title}",
            source=BudgetItem.Source.PLANNER,
            visibility=BudgetItem.Visibility.SHARED,
            status=BudgetItem.Status.COMMITTED,
            estimated_amount=quote.quoted_amount,
            committed_amount=quote.committed_amount,
            paid_amount=ZERO,
            notes=f"Approved planner quote #{quote.pk}. Deposit term: {quote.deposit_amount}",
        )
    else:
        budget_item.category = quote.category
        budget_item.title = f"{quote.vendor.name} - {quote.title}"
        budget_item.visibility = BudgetItem.Visibility.SHARED
        budget_item.status = BudgetItem.Status.COMMITTED
        budget_item.estimated_amount = quote.quoted_amount
        budget_item.committed_amount = quote.committed_amount
    budget_item.save()

    quote.status = VendorQuote.Status.APPROVED
    quote.approved_budget_item = budget_item
    quote.reviewed_by = user
    quote.reviewed_at = timezone.now()
    quote.rejection_reason = ""
    quote.save(update_fields=[
        "status", "approved_budget_item", "reviewed_by", "reviewed_at",
        "rejection_reason", "updated_at",
    ])

    group = quote.comparison_group.strip()
    if group:
        VendorQuote.objects.filter(
            wedding=quote.wedding,
            comparison_group__iexact=group,
            status=VendorQuote.Status.PROPOSED,
        ).exclude(pk=quote.pk).update(
            status=VendorQuote.Status.REJECTED,
            reviewed_by=user,
            reviewed_at=timezone.now(),
            rejection_reason="Another option in this comparison group was approved.",
        )
    _audit(quote, user, "VENDOR_QUOTE_APPROVED", f"Approved vendor quote: {quote.vendor.name} - {quote.title}.")
    return quote


@transaction.atomic
def reject_quote(quote, user, reason=""):
    quote = VendorQuote.objects.select_for_update().select_related("wedding", "vendor").get(pk=quote.pk)
    if quote.status != VendorQuote.Status.PROPOSED:
        raise ValueError("Only proposed quotes can be rejected.")
    if not can_owner_review(user, quote.wedding):
        raise PermissionError("Only the Wedding Owner can reject planner estimates.")
    quote.status = VendorQuote.Status.REJECTED
    quote.reviewed_by = user
    quote.reviewed_at = timezone.now()
    quote.rejection_reason = (reason or "").strip()[:255]
    quote.save(update_fields=["status", "reviewed_by", "reviewed_at", "rejection_reason", "updated_at"])
    _audit(quote, user, "VENDOR_QUOTE_REJECTED", f"Rejected vendor quote: {quote.vendor.name} - {quote.title}.")
    return quote
