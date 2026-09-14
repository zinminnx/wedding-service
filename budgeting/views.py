from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from staffing.access import PERM_MANAGE_WEDDING, PERM_PLANNER, get_wedding_for_user

from .forms import BudgetItemForm, WeddingBudgetSettingsForm
from .models import BudgetItem
from .services import ensure_budget_foundation, financial_summary, is_planner_only


def _view_budget_wedding(request):
    wedding = get_wedding_for_user(request.user, PERM_MANAGE_WEDDING)
    if wedding is None:
        wedding = get_wedding_for_user(request.user, PERM_PLANNER)
    if wedding is None:
        raise Http404("Wedding budget not available for your role.")
    return wedding


def _manage_budget_wedding(request):
    wedding = get_wedding_for_user(request.user, PERM_MANAGE_WEDDING)
    if wedding is None:
        raise Http404("Your role cannot modify the Couple Budget.")
    return wedding


def _audit(wedding, user, action, entity_type, entity_id, message):
    from financial_docs.services import log_financial_event

    log_financial_event(
        wedding=wedding,
        actor=user,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        message=message,
    )


@login_required
def dashboard(request):
    wedding = _view_budget_wedding(request)
    settings_obj = ensure_budget_foundation(wedding)
    planner_view = is_planner_only(request.user, wedding)

    if request.method == "POST":
        if planner_view:
            return HttpResponseBadRequest("Wedding Planner accounts cannot change the Couple Budget target.")
        form_type = request.POST.get("form_type", "settings")
        if form_type != "settings":
            return HttpResponseBadRequest("Unknown form")
        settings_form = WeddingBudgetSettingsForm(request.POST, instance=settings_obj)
        if settings_form.is_valid():
            settings_form.save()
            _audit(wedding, request.user, "BUDGET_TARGET_UPDATED", "BUDGET_SETTINGS", settings_obj.pk, "Wedding budget target updated.")
            messages.success(request, "Wedding budget target updated.")
            return redirect("budgeting:dashboard")
    else:
        settings_form = WeddingBudgetSettingsForm(instance=settings_obj)

    summary = financial_summary(wedding, settings_obj, user=request.user)
    return render(
        request,
        "budgeting/dashboard.html",
        {
            "wedding": wedding,
            "settings_obj": settings_obj,
            "settings_form": settings_form,
            "summary": summary,
            "items": summary["items"],
            "category_summary": summary["categories"],
            "can_manage_couple_budget": not planner_view,
        },
    )


@login_required
def item_create(request):
    wedding = _manage_budget_wedding(request)
    ensure_budget_foundation(wedding)
    if request.method == "POST":
        form = BudgetItemForm(request.POST, wedding=wedding)
        if form.is_valid():
            item = form.save()
            _audit(wedding, request.user, "BUDGET_ITEM_CREATED", "BUDGET_ITEM", item.pk, f"Budget item created: {item.title} ({item.get_visibility_display()}).")
            messages.success(request, f"Budget item '{item.title}' added.")
            return redirect("budgeting:dashboard")
    else:
        form = BudgetItemForm(wedding=wedding)
    return render(request, "budgeting/item_form.html", {"wedding": wedding, "form": form, "editing": False})


@login_required
def item_edit(request, item_id):
    wedding = _manage_budget_wedding(request)
    item = get_object_or_404(
        BudgetItem.objects.select_related("category"),
        pk=item_id,
        wedding=wedding,
        source=BudgetItem.Source.COUPLE,
    )
    old_visibility = item.visibility
    if request.method == "POST":
        form = BudgetItemForm(request.POST, instance=item, wedding=wedding)
        if form.is_valid():
            item = form.save()
            suffix = ""
            if old_visibility != item.visibility:
                suffix = f" Privacy changed to {item.get_visibility_display()}."
            _audit(wedding, request.user, "BUDGET_ITEM_UPDATED", "BUDGET_ITEM", item.pk, f"Budget item updated: {item.title}.{suffix}")
            messages.success(request, f"Budget item '{item.title}' updated.")
            return redirect("budgeting:dashboard")
    else:
        form = BudgetItemForm(instance=item, wedding=wedding)
    return render(
        request,
        "budgeting/item_form.html",
        {"wedding": wedding, "form": form, "editing": True, "item": item},
    )


@login_required
@require_POST
def item_delete(request, item_id):
    wedding = _manage_budget_wedding(request)
    item = get_object_or_404(
        BudgetItem,
        pk=item_id,
        wedding=wedding,
        source=BudgetItem.Source.COUPLE,
    )
    title = item.title
    item_pk = item.pk
    item.delete()
    _audit(wedding, request.user, "BUDGET_ITEM_DELETED", "BUDGET_ITEM", item_pk, f"Budget item removed: {title}.")
    messages.success(request, f"Budget item '{title}' removed.")
    return redirect("budgeting:dashboard")
