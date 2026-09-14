from collections import defaultdict
from decimal import Decimal

from staffing.access import get_user_wedding_role

from .models import BudgetCategory, BudgetItem, WeddingBudgetSettings


ZERO = Decimal("0.00")
DEFAULT_CATEGORIES = [
    "Venue",
    "Catering",
    "Decoration",
    "Photography",
    "Video",
    "Dress & Attire",
    "Rings",
    "Makeup & Beauty",
    "Entertainment",
    "Invitations & Printing",
    "Transportation",
    "Accommodation",
    "Gifts",
    "Planner Fee",
    "Miscellaneous",
]


def ensure_budget_foundation(wedding):
    settings_obj, _ = WeddingBudgetSettings.objects.get_or_create(wedding=wedding)
    if not BudgetCategory.objects.filter(wedding=wedding).exists():
        BudgetCategory.objects.bulk_create(
            [
                BudgetCategory(wedding=wedding, name=name, sort_order=index * 10)
                for index, name in enumerate(DEFAULT_CATEGORIES, start=1)
            ],
            ignore_conflicts=True,
        )
    return settings_obj


def is_planner_only(user, wedding):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False) or wedding.owner_id == user.id:
        return False
    return get_user_wedding_role(user, wedding) == "WEDDING_PLANNER"


def couple_items(wedding, user=None):
    qs = BudgetItem.objects.filter(
        wedding=wedding,
        source=BudgetItem.Source.COUPLE,
    ).select_related("category")
    if is_planner_only(user, wedding):
        qs = qs.filter(visibility=BudgetItem.Visibility.SHARED)
    return qs.order_by("category__sort_order", "category__name", "title")


def planner_items(wedding):
    return (
        BudgetItem.objects.filter(wedding=wedding, source=BudgetItem.Source.PLANNER)
        .select_related("category")
        .order_by("category__sort_order", "category__name", "title")
    )


def financial_summary(wedding, settings_obj=None, user=None):
    """Financial summary with Planner privacy enforcement.

    Owner/Manager/Super Admin views contain all Couple Budget items plus approved
    Planner Budget items. A Wedding Planner sees only Couple items explicitly marked
    Shared with Planner, plus approved Planner items. Owner-private amounts are not
    included in Planner totals, preventing indirect disclosure through summary cards.
    """
    settings_obj = settings_obj or ensure_budget_foundation(wedding)
    planner_view = is_planner_only(user, wedding)
    couple = list(couple_items(wedding, user=user))
    planner = list(planner_items(wedding))
    all_items = couple + planner

    active_items = [item for item in all_items if item.status != BudgetItem.Status.CANCELLED]
    estimated = sum((item.estimated_amount for item in active_items), ZERO)
    committed = sum((item.committed_amount for item in active_items), ZERO)
    paid = sum((item.paid_amount for item in active_items), ZERO)
    final_actual = sum(
        (item.final_actual_amount for item in active_items if item.final_actual_amount is not None),
        ZERO,
    )
    expected = sum((item.expected_amount for item in all_items), ZERO)
    outstanding = sum((item.outstanding_amount for item in all_items), ZERO)

    if planner_view:
        total_budget = None
        remaining = None
        variance = None
        is_over_budget = False
    else:
        total_budget = settings_obj.total_budget or ZERO
        remaining = total_budget - expected
        variance = expected - total_budget
        is_over_budget = remaining < ZERO

    category_data = defaultdict(lambda: {"estimated": ZERO, "expected": ZERO, "paid": ZERO})
    for item in active_items:
        bucket = category_data[item.category.name]
        bucket["estimated"] += item.estimated_amount
        bucket["expected"] += item.expected_amount
        bucket["paid"] += item.paid_amount

    categories = [
        {
            "name": name,
            "estimated": values["estimated"],
            "expected": values["expected"],
            "paid": values["paid"],
        }
        for name, values in category_data.items()
    ]
    categories.sort(key=lambda row: row["expected"], reverse=True)

    return {
        "total_budget": total_budget,
        "estimated": estimated,
        "committed": committed,
        "paid": paid,
        "final_actual": final_actual,
        "expected": expected,
        "remaining": remaining,
        "outstanding": outstanding,
        "variance": variance,
        "is_over_budget": is_over_budget,
        "is_planner_view": planner_view,
        "items": couple,
        "couple_items": couple,
        "planner_items": planner,
        "categories": categories,
    }
