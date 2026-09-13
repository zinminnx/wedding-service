from urllib.parse import urlparse

import qrcode
import qrcode.image.svg

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Sum
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from gifts.models import GiftSettings, ReturnGiftInventory, ReturnGiftMovement
from invitations.models import Invitation
from staffing.access import PERM_CHECK_IN, get_wedding_for_user

from .models import CheckIn


def _owned_invitation(user, qr_token):
    wedding = get_wedding_for_user(user, PERM_CHECK_IN)
    if not wedding:
        raise Http404("Wedding not found")
    return get_object_or_404(
        Invitation.objects.select_related("wedding", "guest"),
        qr_token=qr_token,
        wedding=wedding,
    )


def _extract_qr_token(raw_value):
    value = (raw_value or "").strip()
    if not value:
        return ""

    if "/reception/pass/" in value:
        try:
            path = urlparse(value).path
        except ValueError:
            path = value
        marker = "/reception/pass/"
        if marker in path:
            value = path.split(marker, 1)[1].split("/", 1)[0]

    if value and all(ch.isalnum() or ch in "-_" for ch in value):
        return value
    return ""


def _ensure_inventory(wedding, gift_settings):
    issued_total = CheckIn.objects.filter(wedding=wedding).aggregate(total=Sum("return_gift_quantity"))["total"] or 0
    default_on_hand = max(gift_settings.return_gift_stock - issued_total, 0)
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
            note="Opening balance created automatically.",
        )
    return inventory


def _eligible_quantity(gift_settings, checkin):
    if gift_settings.return_gift_mode == GiftSettings.ReturnGiftMode.NONE:
        return 0
    if gift_settings.return_gift_mode == GiftSettings.ReturnGiftMode.PER_ATTENDEE:
        return checkin.checked_in_count
    if gift_settings.return_gift_mode == GiftSettings.ReturnGiftMode.CUSTOM:
        return gift_settings.custom_return_gift_quantity
    return 1


def qr_image(request, qr_token):
    invitation = get_object_or_404(
        Invitation.objects.select_related("wedding"),
        qr_token=qr_token,
    )
    if invitation.status in [Invitation.Status.REVOKED, Invitation.Status.EXPIRED]:
        raise Http404("Invitation unavailable")

    target = request.build_absolute_uri(
        reverse("checkins:scan", kwargs={"qr_token": invitation.qr_token})
    )
    image = qrcode.make(target, image_factory=qrcode.image.svg.SvgPathImage)
    response = HttpResponse(content_type="image/svg+xml")
    image.save(response)
    return response


@login_required
def dashboard(request):
    wedding = get_wedding_for_user(request.user, PERM_CHECK_IN)
    rows = []
    recent_checkins = []
    q = request.GET.get("q", "").strip()

    if wedding:
        invitations = (
            Invitation.objects.filter(wedding=wedding)
            .select_related("guest")
            .order_by("guest__name")
        )
        if q:
            invitations = invitations.filter(
                Q(guest__name__icontains=q)
                | Q(guest__phone__icontains=q)
                | Q(guest__public_id__icontains=q)
            )
        for invitation in invitations[:100]:
            rows.append(
                {
                    "invitation": invitation,
                    "guest": invitation.guest,
                    "checkin": CheckIn.objects.filter(invitation=invitation).first(),
                }
            )

        checked_in_people = (
            CheckIn.objects.filter(wedding=wedding).aggregate(total=Sum("checked_in_count"))["total"] or 0
        )
        issued = (
            CheckIn.objects.filter(wedding=wedding).aggregate(total=Sum("return_gift_quantity"))["total"] or 0
        )
        gift_settings, _ = GiftSettings.objects.get_or_create(wedding=wedding)
        inventory = _ensure_inventory(wedding, gift_settings)
        counts = {
            "invitations": Invitation.objects.filter(wedding=wedding).count(),
            "checked_in_people": checked_in_people,
            "checked_in_parties": CheckIn.objects.filter(wedding=wedding, checked_in_count__gt=0).count(),
            "return_gifts": issued,
            "return_gift_stock": inventory.quantity_on_hand,
            "return_gift_low": inventory.is_low_stock,
        }
        recent_checkins = list(
            CheckIn.objects.filter(wedding=wedding, checked_in_count__gt=0)
            .select_related("guest", "checked_in_by")
            .order_by("-checked_in_at")[:8]
        )
    else:
        counts = {
            "invitations": 0,
            "checked_in_people": 0,
            "checked_in_parties": 0,
            "return_gifts": 0,
            "return_gift_stock": 0,
            "return_gift_low": False,
        }

    return render(
        request,
        "checkins/dashboard.html",
        {
            "wedding": wedding,
            "rows": rows,
            "counts": counts,
            "q": q,
            "recent_checkins": recent_checkins,
        },
    )


@login_required
def camera_scanner(request):
    wedding = get_wedding_for_user(request.user, PERM_CHECK_IN)
    if not wedding:
        raise Http404("Wedding not found")

    if request.method == "POST":
        token = _extract_qr_token(request.POST.get("qr_value"))
        if not token:
            messages.error(request, "That QR value is not a valid EverAfter entrance pass.")
            return redirect("checkins:camera_scanner")

        invitation = Invitation.objects.filter(wedding=wedding, qr_token=token).first()
        if not invitation:
            messages.error(request, "This entrance pass does not belong to the current wedding.")
            return redirect("checkins:camera_scanner")

        return redirect("checkins:scan", qr_token=invitation.qr_token)

    return render(
        request,
        "checkins/scanner.html",
        {
            "wedding": wedding,
            "scan_path_prefix": "/reception/pass/",
        },
    )


@login_required
def scan(request, qr_token):
    invitation = _owned_invitation(request.user, qr_token)
    guest = invitation.guest

    if invitation.status in [Invitation.Status.REVOKED, Invitation.Status.EXPIRED]:
        return render(
            request,
            "checkins/scan.html",
            {
                "wedding": invitation.wedding,
                "invitation": invitation,
                "guest": guest,
                "blocked": True,
            },
        )

    checkin, _ = CheckIn.objects.get_or_create(
        wedding=invitation.wedding,
        guest=guest,
        invitation=invitation,
    )
    gift_settings, _ = GiftSettings.objects.get_or_create(wedding=invitation.wedding)
    inventory = _ensure_inventory(invitation.wedding, gift_settings)
    eligible_return_gift_qty = _eligible_quantity(gift_settings, checkin)

    if request.method == "POST":
        action = request.POST.get("action", "").strip()

        if action == "check_in":
            try:
                count = int(request.POST.get("checked_in_count", 0) or 0)
            except ValueError:
                count = 0
            if count < 1 or count > guest.allowed_party_size:
                messages.error(request, f"Check-in count must be between 1 and {guest.allowed_party_size}.")
            else:
                checkin.checked_in_count = count
                checkin.checked_in_at = timezone.now()
                checkin.checked_in_by = request.user
                checkin.save()
                messages.success(request, f"{guest.name} checked in ({count}).")
            return redirect("checkins:scan", qr_token=qr_token)

        if action == "undo_check_in":
            checkin.checked_in_count = 0
            checkin.checked_in_at = None
            checkin.checked_in_by = None
            checkin.save()
            messages.success(request, f"Check-in for {guest.name} was undone.")
            return redirect("checkins:scan", qr_token=qr_token)

        if action == "issue_return_gift":
            if gift_settings.return_gift_requires_checkin and checkin.checked_in_count < 1:
                messages.error(request, "Check the guest in before issuing the return gift.")
                return redirect("checkins:scan", qr_token=qr_token)

            default_quantity = _eligible_quantity(gift_settings, checkin)
            quantity = default_quantity
            if gift_settings.return_gift_allow_staff_override:
                raw_quantity = request.POST.get("return_gift_quantity", "").strip()
                if raw_quantity:
                    try:
                        quantity = int(raw_quantity)
                    except ValueError:
                        quantity = 0

            if quantity < 1:
                messages.info(request, "No return gift is eligible under the current rule.")
                return redirect("checkins:scan", qr_token=qr_token)
            if quantity > 1000:
                messages.error(request, "Return gift quantity is too large.")
                return redirect("checkins:scan", qr_token=qr_token)

            with transaction.atomic():
                locked_checkin = CheckIn.objects.select_for_update().get(pk=checkin.pk)
                locked_inventory = ReturnGiftInventory.objects.select_for_update().get(pk=inventory.pk)

                if locked_checkin.return_gift_quantity > 0:
                    messages.info(request, "Return gift has already been issued for this invitation.")
                elif quantity > locked_inventory.quantity_on_hand:
                    messages.error(
                        request,
                        f"Not enough return gift stock. Remaining: {locked_inventory.quantity_on_hand}.",
                    )
                else:
                    locked_inventory.quantity_on_hand -= quantity
                    locked_inventory.save(update_fields=["quantity_on_hand", "updated_at"])
                    locked_checkin.return_gift_quantity = quantity
                    locked_checkin.return_gift_issued_at = timezone.now()
                    locked_checkin.return_gift_issued_by = request.user
                    locked_checkin.save()
                    ReturnGiftMovement.objects.create(
                        wedding=invitation.wedding,
                        inventory=locked_inventory,
                        guest=guest,
                        checkin=locked_checkin,
                        movement_type=ReturnGiftMovement.MovementType.ISSUE,
                        quantity_delta=-quantity,
                        quantity_after=locked_inventory.quantity_on_hand,
                        note=f"Issued at reception for {guest.name}.",
                        created_by=request.user,
                    )
                    messages.success(request, f"Return gift issued: {quantity}.")
            return redirect("checkins:scan", qr_token=qr_token)

        if action == "undo_return_gift":
            with transaction.atomic():
                locked_checkin = CheckIn.objects.select_for_update().get(pk=checkin.pk)
                locked_inventory = ReturnGiftInventory.objects.select_for_update().get(pk=inventory.pk)
                quantity = locked_checkin.return_gift_quantity
                if quantity < 1:
                    messages.info(request, "No return gift issue to undo.")
                else:
                    locked_inventory.quantity_on_hand += quantity
                    locked_inventory.save(update_fields=["quantity_on_hand", "updated_at"])
                    locked_checkin.return_gift_quantity = 0
                    locked_checkin.return_gift_issued_at = None
                    locked_checkin.return_gift_issued_by = None
                    locked_checkin.save()
                    ReturnGiftMovement.objects.create(
                        wedding=invitation.wedding,
                        inventory=locked_inventory,
                        guest=guest,
                        checkin=locked_checkin,
                        movement_type=ReturnGiftMovement.MovementType.RETURN,
                        quantity_delta=quantity,
                        quantity_after=locked_inventory.quantity_on_hand,
                        note=f"Return gift issue undone for {guest.name}.",
                        created_by=request.user,
                    )
                    messages.success(request, f"Returned {quantity} gift(s) to stock.")
            return redirect("checkins:scan", qr_token=qr_token)

        return HttpResponseBadRequest("Unknown action")

    try:
        rsvp = guest.rsvp
    except Exception:
        rsvp = None

    return render(
        request,
        "checkins/scan.html",
        {
            "wedding": invitation.wedding,
            "invitation": invitation,
            "guest": guest,
            "checkin": checkin,
            "gift_settings": gift_settings,
            "remaining_stock": inventory.quantity_on_hand,
            "stock_is_low": inventory.is_low_stock,
            "eligible_return_gift_qty": eligible_return_gift_qty,
            "rsvp": rsvp,
            "blocked": False,
        },
    )
