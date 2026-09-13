import qrcode
import qrcode.image.svg

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from gifts.models import GiftSettings
from invitations.models import Invitation
from weddings.models import Wedding

from .models import CheckIn


def _wedding_for_user(user):
    qs = Wedding.objects.all()
    if not user.is_superuser:
        qs = qs.filter(owner=user)
    return qs.order_by("-created_at").first()


def _owned_invitation(user, qr_token):
    wedding = _wedding_for_user(user)
    if not wedding:
        raise Http404("Wedding not found")
    return get_object_or_404(
        Invitation.objects.select_related("wedding", "guest"),
        qr_token=qr_token,
        wedding=wedding,
    )


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
    wedding = _wedding_for_user(request.user)
    rows = []
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
        counts = {
            "invitations": Invitation.objects.filter(wedding=wedding).count(),
            "checked_in_people": checked_in_people,
            "checked_in_parties": CheckIn.objects.filter(wedding=wedding, checked_in_count__gt=0).count(),
            "return_gifts": issued,
        }
    else:
        counts = {"invitations": 0, "checked_in_people": 0, "checked_in_parties": 0, "return_gifts": 0}

    return render(
        request,
        "checkins/dashboard.html",
        {
            "wedding": wedding,
            "rows": rows,
            "counts": counts,
            "q": q,
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

    issued_total = (
        CheckIn.objects.filter(wedding=invitation.wedding).aggregate(total=Sum("return_gift_quantity"))["total"] or 0
    )
    remaining_stock = max(gift_settings.return_gift_stock - issued_total, 0)

    if gift_settings.return_gift_mode == GiftSettings.ReturnGiftMode.NONE:
        eligible_return_gift_qty = 0
    elif gift_settings.return_gift_mode == GiftSettings.ReturnGiftMode.PER_ATTENDEE:
        eligible_return_gift_qty = checkin.checked_in_count
    elif gift_settings.return_gift_mode == GiftSettings.ReturnGiftMode.CUSTOM:
        eligible_return_gift_qty = gift_settings.custom_return_gift_quantity
    else:
        eligible_return_gift_qty = 1

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
            if checkin.checked_in_count < 1:
                messages.error(request, "Check the guest in before issuing the return gift.")
            elif checkin.return_gift_quantity > 0:
                messages.info(request, "Return gift has already been issued for this invitation.")
            else:
                if gift_settings.return_gift_mode == GiftSettings.ReturnGiftMode.PER_ATTENDEE:
                    quantity = checkin.checked_in_count
                elif gift_settings.return_gift_mode == GiftSettings.ReturnGiftMode.CUSTOM:
                    quantity = gift_settings.custom_return_gift_quantity
                elif gift_settings.return_gift_mode == GiftSettings.ReturnGiftMode.NONE:
                    quantity = 0
                else:
                    quantity = 1

                if quantity < 1:
                    messages.info(request, "Return gifts are disabled for this wedding.")
                elif quantity > remaining_stock:
                    messages.error(request, f"Not enough return gift stock. Remaining: {remaining_stock}.")
                else:
                    checkin.return_gift_quantity = quantity
                    checkin.return_gift_issued_at = timezone.now()
                    checkin.return_gift_issued_by = request.user
                    checkin.save()
                    messages.success(request, f"Return gift issued: {quantity}.")
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
            "remaining_stock": remaining_stock,
            "eligible_return_gift_qty": eligible_return_gift_qty,
            "rsvp": rsvp,
            "blocked": False,
        },
    )
