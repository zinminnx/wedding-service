from django.db.models import Q

from budgeting.models import BudgetItem
from staffing.access import get_user_wedding_role

from .models import FinancialAuditEvent, FinancialDocument


def is_planner_only(user, wedding):
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False) or wedding.owner_id == user.id:
        return False
    return get_user_wedding_role(user, wedding) == "WEDDING_PLANNER"


def visible_documents(user, wedding):
    qs = FinancialDocument.objects.filter(wedding=wedding).select_related(
        "budget_item", "budget_item__category", "vendor_quote", "vendor_quote__vendor", "created_by"
    )
    if not is_planner_only(user, wedding):
        return qs
    return qs.filter(
        Q(vendor_quote__isnull=False, visibility=FinancialDocument.Visibility.SHARED)
        | Q(
            budget_item__isnull=False,
            visibility=FinancialDocument.Visibility.SHARED,
            budget_item__source=BudgetItem.Source.PLANNER,
        )
        | Q(
            budget_item__isnull=False,
            visibility=FinancialDocument.Visibility.SHARED,
            budget_item__source=BudgetItem.Source.COUPLE,
            budget_item__visibility=BudgetItem.Visibility.SHARED,
        )
    ).distinct()


def log_financial_event(*, wedding, actor, action, entity_type, entity_id="", message=""):
    return FinancialAuditEvent.objects.create(
        wedding=wedding,
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=(action or "FINANCIAL_ACTION")[:64],
        entity_type=(entity_type or "UNKNOWN")[:40],
        entity_id=str(entity_id or "")[:64],
        message=(message or action or "Financial action")[:255],
    )
