from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from staffing.access import PERM_MANAGE_GIFTS, get_wedding_for_user

from .forms import (
    GiftPaymentMethodForm,
    GiftSettingsForm,
    ReturnGiftRestockForm,
    ReturnGiftSetStockForm,
)
from .models import (
    GiftPaymentMethod,
    GiftSettings,
    GuestGiftDeclaration,
    ReturnGiftInventory,
    ReturnGiftMovement,
)
from .reporting import build_payment_report_context, payment_report_csv_response


def _ensure_inventory(wedding, settings_obj=None):
    settings_obj = settings_obj or GiftSettings.objects.get_or_create(wedding=wedding)[0]
    current_issued = wedding.checkins.aggregate(total=Sum("return_gift_quantity"))["total"] or 0
    default_on_hand = max(settings_obj.return_gift_stock - current_issued, 0)
    inventory, created = ReturnGiftInventory.objects.get_or_create(
        wedding=wedding,
        defaults={"quantity_on_hand": default_on_hand},
    )
    if created and default_on_hand:
        ReturnGiftMovement.objects.create(
            wedding=wedding,
            inventory=inventory,
            movement_type=ReturnGiftMovement.MovementType.OPENING,
            quantity_delta=default_on_hand,
            quantity_after=default_on_hand,
            note="Opening balance created during v9 upgrade.",
        )
    return inventory


@login_required
def gift_dashboard(request):
    wedding = get_wedding_for_user(request.user, PERM_MANAGE_GIFTS)
    if not wedding:
        messages.info(request, "Create your wedding first.")
        return redirect("weddings:overview")

    settings_obj, _ = GiftSettings.objects.get_or_create(wedding=wedding)
    inventory = _ensure_inventory(wedding, settings_obj)
    edit_method = None
    edit_id = request.GET.get("edit", "").strip()
    if edit_id.isdigit():
        edit_method = GiftPaymentMethod.objects.filter(pk=int(edit_id), wedding=wedding).first()

    if request.method == "POST":
        form_type = request.POST.get("form_type", "settings")
        if form_type == "settings":
            form = GiftSettingsForm(request.POST, instance=settings_obj)
            payment_form = GiftPaymentMethodForm(instance=edit_method)
            if form.is_valid():
                form.save()
                messages.success(request, "Gift settings saved.")
                return redirect("gifts:dashboard")
        elif form_type == "payment_method":
            form = GiftSettingsForm(instance=settings_obj)
            method_id = request.POST.get("method_id", "").strip()
            method_obj = None
            if method_id.isdigit():
                method_obj = get_object_or_404(GiftPaymentMethod, pk=int(method_id), wedding=wedding)
            payment_form = GiftPaymentMethodForm(request.POST, request.FILES, instance=method_obj)
            if payment_form.is_valid():
                item = payment_form.save(commit=False)
                item.wedding = wedding
                item.save()
                payment_form.save_provider_link(item)
                messages.success(request, f"Payment account for '{item.name}' saved.")
                return redirect("gifts:dashboard")
        else:
            form = GiftSettingsForm(instance=settings_obj)
            payment_form = GiftPaymentMethodForm(instance=edit_method)
    else:
        form = GiftSettingsForm(instance=settings_obj)
        payment_form = GiftPaymentMethodForm(instance=edit_method)

    payment_methods = GiftPaymentMethod.objects.filter(wedding=wedding).order_by("sort_order", "id")
    declarations = (
        GuestGiftDeclaration.objects.filter(wedding=wedding)
        .select_related("guest", "invitation", "payment_method_record")
        .order_by("-updated_at")
    )

    counts = {
        "total": declarations.count(),
        "digital": declarations.filter(gift_choice=GuestGiftDeclaration.GiftChoice.DIGITAL).count(),
        "physical": declarations.filter(gift_choice=GuestGiftDeclaration.GiftChoice.PHYSICAL).count(),
        "none": declarations.filter(gift_choice=GuestGiftDeclaration.GiftChoice.NONE).count(),
        "guest_sent": declarations.filter(payment_status=GuestGiftDeclaration.PaymentStatus.GUEST_SENT).count(),
        "verified": declarations.filter(payment_status=GuestGiftDeclaration.PaymentStatus.VERIFIED).count(),
    }

    current_issued = wedding.checkins.aggregate(total=Sum("return_gift_quantity"))["total"] or 0
    recent_movements = (
        ReturnGiftMovement.objects.filter(wedding=wedding)
        .select_related("guest", "created_by")[:6]
    )
    return_gift = {
        "stock": inventory.quantity_on_hand,
        "issued": current_issued,
        "low": inventory.is_low_stock,
        "threshold": inventory.low_stock_threshold,
    }

    return render(
        request,
        "gifts/dashboard.html",
        {
            "wedding": wedding,
            "settings_obj": settings_obj,
            "form": form,
            "payment_form": payment_form,
            "payment_methods": payment_methods,
            "edit_method": edit_method,
            "declarations": declarations,
            "counts": counts,
            "return_gift": return_gift,
            "recent_movements": recent_movements,
        },
    )


@login_required
def payment_report(request):
    wedding = get_wedding_for_user(request.user, PERM_MANAGE_GIFTS)
    if not wedding:
        raise Http404("Wedding not found")
    return render(
        request,
        "gifts/reports.html",
        build_payment_report_context(request, wedding),
    )


@login_required
def payment_report_csv(request):
    wedding = get_wedding_for_user(request.user, PERM_MANAGE_GIFTS)
    if not wedding:
        raise Http404("Wedding not found")
    return payment_report_csv_response(request, wedding)


@login_required
def return_gift_inventory(request):
    wedding = get_wedding_for_user(request.user, PERM_MANAGE_GIFTS)
    if not wedding:
        raise Http404("Wedding not found")

    settings_obj, _ = GiftSettings.objects.get_or_create(wedding=wedding)
    inventory = _ensure_inventory(wedding, settings_obj)
    restock_form = ReturnGiftRestockForm()
    set_stock_form = ReturnGiftSetStockForm(instance=inventory)

    if request.method == "POST":
        action = request.POST.get("action", "").strip()

        if action == "restock":
            restock_form = ReturnGiftRestockForm(request.POST)
            if restock_form.is_valid():
                quantity = restock_form.cleaned_data["quantity"]
                note = restock_form.cleaned_data["note"]
                with transaction.atomic():
                    locked = ReturnGiftInventory.objects.select_for_update().get(pk=inventory.pk)
                    locked.quantity_on_hand += quantity
                    locked.save(update_fields=["quantity_on_hand", "updated_at"])
                    GiftSettings.objects.filter(pk=settings_obj.pk).update(
                        return_gift_stock=settings_obj.return_gift_stock + quantity
                    )
                    ReturnGiftMovement.objects.create(
                        wedding=wedding,
                        inventory=locked,
                        movement_type=ReturnGiftMovement.MovementType.RESTOCK,
                        quantity_delta=quantity,
                        quantity_after=locked.quantity_on_hand,
                        note=note,
                        created_by=request.user,
                    )
                messages.success(request, f"Added {quantity} return gift(s) to stock.")
                return redirect("gifts:inventory")

        elif action == "set_stock":
            set_stock_form = ReturnGiftSetStockForm(request.POST, instance=inventory)
            if set_stock_form.is_valid():
                new_quantity = set_stock_form.cleaned_data["quantity_on_hand"]
                new_threshold = set_stock_form.cleaned_data["low_stock_threshold"]
                with transaction.atomic():
                    locked = ReturnGiftInventory.objects.select_for_update().get(pk=inventory.pk)
                    old_quantity = locked.quantity_on_hand
                    delta = new_quantity - old_quantity
                    locked.quantity_on_hand = new_quantity
                    locked.low_stock_threshold = new_threshold
                    locked.save(update_fields=["quantity_on_hand", "low_stock_threshold", "updated_at"])

                    current_issued = wedding.checkins.aggregate(total=Sum("return_gift_quantity"))["total"] or 0
                    GiftSettings.objects.filter(pk=settings_obj.pk).update(
                        return_gift_stock=current_issued + new_quantity
                    )
                    if delta:
                        ReturnGiftMovement.objects.create(
                            wedding=wedding,
                            inventory=locked,
                            movement_type=ReturnGiftMovement.MovementType.SET_STOCK,
                            quantity_delta=delta,
                            quantity_after=new_quantity,
                            note="Manual stock correction.",
                            created_by=request.user,
                        )
                messages.success(request, "Return gift stock settings updated.")
                return redirect("gifts:inventory")
        else:
            return HttpResponseBadRequest("Unknown action")

    movements = (
        ReturnGiftMovement.objects.filter(wedding=wedding)
        .select_related("guest", "checkin", "created_by")[:100]
    )
    current_issued = wedding.checkins.aggregate(total=Sum("return_gift_quantity"))["total"] or 0
    lifetime_issued = -(
        ReturnGiftMovement.objects.filter(
            wedding=wedding,
            movement_type=ReturnGiftMovement.MovementType.ISSUE,
        ).aggregate(total=Sum("quantity_delta"))["total"]
        or 0
    )

    return render(
        request,
        "gifts/inventory.html",
        {
            "wedding": wedding,
            "settings_obj": settings_obj,
            "inventory": inventory,
            "restock_form": restock_form,
            "set_stock_form": set_stock_form,
            "movements": movements,
            "current_issued": current_issued,
            "lifetime_issued": lifetime_issued,
        },
    )


@login_required
def payment_method_action(request, method_id):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    wedding = get_wedding_for_user(request.user, PERM_MANAGE_GIFTS)
    if not wedding:
        raise Http404("Wedding not found")
    item = get_object_or_404(GiftPaymentMethod, pk=method_id, wedding=wedding)
    action = request.POST.get("action", "").strip()

    if action == "toggle":
        item.is_enabled = not item.is_enabled
        item.save(update_fields=["is_enabled", "updated_at"])
        messages.success(request, f"{item.name} {'enabled' if item.is_enabled else 'disabled'}.")
    elif action == "delete":
        name = item.name
        item.delete()
        messages.success(request, f"{name} removed.")
    else:
        return HttpResponseBadRequest("Unknown action")
    return redirect("gifts:dashboard")


@login_required
def declaration_action(request, declaration_id):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    wedding = get_wedding_for_user(request.user, PERM_MANAGE_GIFTS)
    if not wedding:
        raise Http404("Wedding not found")

    declaration = get_object_or_404(GuestGiftDeclaration, pk=declaration_id, wedding=wedding)
    action = request.POST.get("action", "").strip()

    if action == "verify":
        declaration.payment_status = GuestGiftDeclaration.PaymentStatus.VERIFIED
        declaration.payment_reviewed_at = timezone.now()
        declaration.payment_reviewed_by = request.user
        declaration.save(update_fields=["payment_status", "payment_reviewed_at", "payment_reviewed_by", "updated_at"])
        messages.success(request, f"Gift from {declaration.guest.name} verified.")
    elif action == "reject":
        declaration.payment_status = GuestGiftDeclaration.PaymentStatus.REJECTED
        declaration.payment_reviewed_at = timezone.now()
        declaration.payment_reviewed_by = request.user
        declaration.save(update_fields=["payment_status", "payment_reviewed_at", "payment_reviewed_by", "updated_at"])
        messages.success(request, f"Gift declaration from {declaration.guest.name} rejected.")
    elif action == "reset":
        if declaration.gift_choice == GuestGiftDeclaration.GiftChoice.DIGITAL:
            declaration.payment_status = GuestGiftDeclaration.PaymentStatus.GUEST_SENT
        else:
            declaration.payment_status = GuestGiftDeclaration.PaymentStatus.NOT_REQUIRED
        declaration.payment_reviewed_at = None
        declaration.payment_reviewed_by = None
        declaration.save(update_fields=["payment_status", "payment_reviewed_at", "payment_reviewed_by", "updated_at"])
        messages.success(request, "Gift verification status reset.")
    else:
        return HttpResponseBadRequest("Unknown action")

    return redirect("gifts:dashboard")
