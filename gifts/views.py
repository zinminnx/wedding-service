from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render

from staffing.access import PERM_MANAGE_GIFTS, get_wedding_for_user

from .forms import GiftPaymentMethodForm, GiftSettingsForm
from .models import GiftPaymentMethod, GiftSettings, GuestGiftDeclaration


@login_required
def gift_dashboard(request):
    wedding = get_wedding_for_user(request.user, PERM_MANAGE_GIFTS)
    if not wedding:
        messages.info(request, "Create your wedding first.")
        return redirect("weddings:overview")

    settings_obj, _ = GiftSettings.objects.get_or_create(wedding=wedding)
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
                messages.success(request, f"Payment method '{item.name}' saved.")
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

    issued = wedding.checkins.aggregate(total=Sum("return_gift_quantity"))["total"] or 0
    return_gift = {
        "stock": settings_obj.return_gift_stock,
        "issued": issued,
        "remaining": max(settings_obj.return_gift_stock - issued, 0),
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
        declaration.save(update_fields=["payment_status", "updated_at"])
        messages.success(request, f"Gift from {declaration.guest.name} verified.")
    elif action == "reject":
        declaration.payment_status = GuestGiftDeclaration.PaymentStatus.REJECTED
        declaration.save(update_fields=["payment_status", "updated_at"])
        messages.success(request, f"Gift declaration from {declaration.guest.name} rejected.")
    elif action == "reset":
        if declaration.gift_choice == GuestGiftDeclaration.GiftChoice.DIGITAL:
            declaration.payment_status = GuestGiftDeclaration.PaymentStatus.GUEST_SENT
        else:
            declaration.payment_status = GuestGiftDeclaration.PaymentStatus.NOT_REQUIRED
        declaration.save(update_fields=["payment_status", "updated_at"])
        messages.success(request, "Gift verification status reset.")
    else:
        return HttpResponseBadRequest("Unknown action")

    return redirect("gifts:dashboard")
