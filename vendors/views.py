from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from budgeting.services import ensure_budget_foundation
from staffing.access import PERM_PLANNER, get_wedding_for_user

from .forms import VendorForm, VendorQuoteForm
from .models import Vendor, VendorQuote
from .services import approve_quote, can_owner_review, reject_quote


def _vendor_wedding(request):
    wedding = get_wedding_for_user(request.user, PERM_PLANNER)
    if wedding is None:
        raise Http404("Vendor workspace not available")
    ensure_budget_foundation(wedding)
    return wedding


@login_required
def dashboard(request):
    wedding = _vendor_wedding(request)
    vendors = Vendor.objects.filter(wedding=wedding).select_related("category").order_by("name")
    quotes = (
        VendorQuote.objects.filter(wedding=wedding)
        .select_related("vendor", "category", "reviewed_by", "approved_budget_item")
        .order_by("-updated_at")
    )
    counts = {
        "vendors": vendors.filter(status=Vendor.Status.ACTIVE).count(),
        "draft": quotes.filter(status=VendorQuote.Status.DRAFT).count(),
        "proposed": quotes.filter(status=VendorQuote.Status.PROPOSED).count(),
        "approved": quotes.filter(status=VendorQuote.Status.APPROVED).count(),
        "rejected": quotes.filter(status=VendorQuote.Status.REJECTED).count(),
    }
    return render(
        request,
        "vendors/dashboard.html",
        {
            "wedding": wedding,
            "vendors": vendors,
            "quotes": quotes,
            "counts": counts,
            "can_review": can_owner_review(request.user, wedding),
        },
    )


@login_required
def vendor_form(request, pk=None):
    wedding = _vendor_wedding(request)
    instance = get_object_or_404(Vendor, pk=pk, wedding=wedding) if pk else None
    form = VendorForm(request.POST or None, instance=instance, wedding=wedding)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        if not item.created_by_id:
            item.created_by = request.user
        item.save()
        messages.success(request, f"Vendor '{item.name}' saved.")
        return redirect("vendors:dashboard")
    return render(request, "vendors/form.html", {"wedding": wedding, "form": form, "kind": "vendor", "editing": bool(instance)})


@login_required
def quote_form(request, pk=None):
    wedding = _vendor_wedding(request)
    instance = get_object_or_404(VendorQuote, pk=pk, wedding=wedding) if pk else None
    if instance and instance.status not in {VendorQuote.Status.DRAFT, VendorQuote.Status.REJECTED, VendorQuote.Status.WITHDRAWN}:
        messages.warning(request, "Proposed or approved quotes are locked. Withdraw/reject before editing.")
        return redirect("vendors:dashboard")
    form = VendorQuoteForm(request.POST or None, instance=instance, wedding=wedding)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        if not item.created_by_id:
            item.created_by = request.user
        item.status = VendorQuote.Status.DRAFT
        item.proposed_at = None
        item.reviewed_at = None
        item.reviewed_by = None
        item.rejection_reason = ""
        item.save()
        messages.success(request, "Vendor quote saved as draft.")
        return redirect("vendors:dashboard")
    return render(request, "vendors/form.html", {"wedding": wedding, "form": form, "kind": "quote", "editing": bool(instance)})


@login_required
@require_POST
def quote_action(request, pk):
    wedding = _vendor_wedding(request)
    quote = get_object_or_404(VendorQuote.objects.select_related("vendor", "wedding"), pk=pk, wedding=wedding)
    action = request.POST.get("action", "").strip()

    try:
        if action == "propose":
            if quote.status not in {VendorQuote.Status.DRAFT, VendorQuote.Status.REJECTED, VendorQuote.Status.WITHDRAWN}:
                return HttpResponseBadRequest("Only draft/rejected/withdrawn quotes can be proposed")
            quote.status = VendorQuote.Status.PROPOSED
            quote.proposed_at = timezone.now()
            quote.reviewed_at = None
            quote.reviewed_by = None
            quote.rejection_reason = ""
            quote.save(update_fields=["status", "proposed_at", "reviewed_at", "reviewed_by", "rejection_reason", "updated_at"])
            messages.success(request, f"{quote.vendor.name} quote sent to the Wedding Owner for review.")
        elif action == "withdraw":
            if quote.status != VendorQuote.Status.PROPOSED:
                return HttpResponseBadRequest("Only proposed quotes can be withdrawn")
            quote.status = VendorQuote.Status.WITHDRAWN
            quote.save(update_fields=["status", "updated_at"])
            messages.success(request, "Proposal withdrawn. It can be edited and proposed again.")
        elif action == "approve":
            approve_quote(quote, request.user)
            messages.success(request, "Quote approved and added to the Planner Budget / Financial Summary.")
        elif action == "reject":
            reject_quote(quote, request.user, request.POST.get("reason", ""))
            messages.success(request, "Quote rejected. It did not enter the committed budget.")
        else:
            return HttpResponseBadRequest("Unknown action")
    except PermissionError as exc:
        messages.error(request, str(exc))
    except ValueError as exc:
        messages.error(request, str(exc))

    return redirect("vendors:dashboard")
