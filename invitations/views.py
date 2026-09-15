from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from guests.models import Guest
from rsvp.models import RSVP
from gifts.models import GiftPaymentMethod, GiftSettings, GuestGiftDeclaration
from invitation_themes.hero_storage import hero_image_response, published_hero_for_wedding
from staffing.access import (
    PERM_MANAGE_INVITATIONS,
    PERM_VIEW_INVITATIONS,
    get_wedding_for_user,
)

from .models import Invitation


def invitation_detail(request, token):
    try:
        invitation = Invitation.objects.select_related("wedding", "guest").get(token=token)
    except Invitation.DoesNotExist:
        raise Http404("Invitation not found")

    if invitation.status in [Invitation.Status.REVOKED, Invitation.Status.EXPIRED]:
        raise Http404("Invitation unavailable")

    if request.method == "GET":
        now = timezone.now()
        if invitation.first_opened_at is None:
            invitation.first_opened_at = now
        invitation.last_opened_at = now
        invitation.open_count += 1
        if invitation.status in [Invitation.Status.DRAFT, Invitation.Status.READY, Invitation.Status.SENT]:
            invitation.status = Invitation.Status.OPENED
        invitation.save(update_fields=["first_opened_at", "last_opened_at", "open_count", "status", "updated_at"])

    current_rsvp = RSVP.objects.filter(invitation=invitation).first()
    gift_settings, _ = GiftSettings.objects.get_or_create(wedding=invitation.wedding)
    payment_methods = GiftPaymentMethod.objects.filter(
        wedding=invitation.wedding,
        is_enabled=True,
    ).order_by("sort_order", "id")
    gift_declaration = GuestGiftDeclaration.objects.select_related("payment_method_record").filter(invitation=invitation).first()

    rsvp_saved = False
    rsvp_error = ""
    gift_saved = False
    gift_error = ""

    if request.method == "POST":
        form_type = request.POST.get("form_type", "rsvp").strip()

        if form_type == "gift":
            gift_choice = request.POST.get("gift_choice", "").strip()
            payment_method_id = request.POST.get("payment_method_id", "").strip()
            amount_raw = request.POST.get("amount", "").strip()
            payment_reference = request.POST.get("payment_reference", "").strip()
            notes = request.POST.get("gift_notes", "").strip()
            selected_method = None

            if gift_choice not in GuestGiftDeclaration.GiftChoice.values:
                gift_error = "Please choose a gift option."
            elif gift_choice == GuestGiftDeclaration.GiftChoice.DIGITAL:
                if not payment_method_id.isdigit():
                    gift_error = "Please select the payment method you used."
                else:
                    selected_method = GiftPaymentMethod.objects.filter(
                        pk=int(payment_method_id),
                        wedding=invitation.wedding,
                        is_enabled=True,
                    ).first()
                    if selected_method is None:
                        gift_error = "That payment method is not available."

            amount = None
            if not gift_error and amount_raw:
                try:
                    amount = Decimal(amount_raw)
                    if amount < 0:
                        raise InvalidOperation
                except (InvalidOperation, ValueError):
                    gift_error = "Please enter a valid amount or leave it blank."

            if not gift_error:
                if gift_declaration is None:
                    gift_declaration = GuestGiftDeclaration(
                        wedding=invitation.wedding,
                        guest=invitation.guest,
                        invitation=invitation,
                    )

                gift_declaration.gift_choice = gift_choice
                gift_declaration.payment_method_record = selected_method
                gift_declaration.amount = amount
                gift_declaration.payment_reference = payment_reference
                gift_declaration.notes = notes
                if gift_choice == GuestGiftDeclaration.GiftChoice.DIGITAL:
                    gift_declaration.payment_status = GuestGiftDeclaration.PaymentStatus.GUEST_SENT
                else:
                    gift_declaration.payment_status = GuestGiftDeclaration.PaymentStatus.NOT_REQUIRED
                gift_declaration.save()
                gift_saved = True

        else:
            response = request.POST.get("response", "").strip()
            notes = request.POST.get("notes", "").strip()
            try:
                adults = int(request.POST.get("attending_adults", 0) or 0)
                children = int(request.POST.get("attending_children", 0) or 0)
            except ValueError:
                adults = 0
                children = 0

            if response not in RSVP.Response.values:
                rsvp_error = "Please choose an RSVP response."
            else:
                if response != RSVP.Response.ATTENDING:
                    adults = 0
                    children = 0
                if response == RSVP.Response.ATTENDING and adults + children == 0:
                    adults = 1
                if adults + children > invitation.guest.allowed_party_size:
                    rsvp_error = f"Your invitation allows up to {invitation.guest.allowed_party_size} guest(s)."
                else:
                    if current_rsvp is None:
                        current_rsvp = RSVP(
                            invitation=invitation,
                            wedding=invitation.wedding,
                            guest=invitation.guest,
                        )
                    current_rsvp.response = response
                    current_rsvp.attending_adults = adults
                    current_rsvp.attending_children = children
                    current_rsvp.notes = notes
                    current_rsvp.responded_at = timezone.now()
                    try:
                        current_rsvp.save()
                    except ValidationError as exc:
                        rsvp_error = " ".join(exc.messages)
                    else:
                        rsvp_saved = True

    return render(
        request,
        "invitations/detail.html",
        {
            "invitation": invitation,
            "wedding": invitation.wedding,
            "guest": invitation.guest,
            "rsvp": current_rsvp,
            "rsvp_saved": rsvp_saved,
            "rsvp_error": rsvp_error,
            "gift_settings": gift_settings,
            "payment_methods": payment_methods,
            "gift_declaration": gift_declaration,
            "gift_saved": gift_saved,
            "gift_error": gift_error,
        },
    )



def invitation_hero_image(request, token):
    invitation = (
        Invitation.objects.select_related("wedding")
        .filter(token=token)
        .first()
    )
    if invitation is None or invitation.status in [Invitation.Status.REVOKED, Invitation.Status.EXPIRED]:
        raise Http404("Invitation unavailable")
    record = published_hero_for_wedding(invitation.wedding)
    if record is None:
        raise Http404("Cover photo not found")
    return hero_image_response(record, cache_control="private, max-age=3600")


def _owned_invitation(user, invitation_id):
    wedding = get_wedding_for_user(user, PERM_MANAGE_INVITATIONS)
    if not wedding:
        raise Http404("Wedding not found")
    return get_object_or_404(
        Invitation.objects.select_related("guest", "wedding"),
        pk=invitation_id,
        wedding=wedding,
    )


@login_required
def invitation_list(request):
    wedding = get_wedding_for_user(request.user, PERM_VIEW_INVITATIONS)
    rows = []
    counts = {
        "guests": 0,
        "generated": 0,
        "opened": 0,
        "responded": 0,
        "missing": 0,
    }

    if wedding:
        guests = list(
            Guest.objects.filter(wedding=wedding)
            .select_related("group")
            .order_by("name")
        )
        invitations = list(
            Invitation.objects.filter(wedding=wedding)
            .select_related("guest")
            .order_by("guest__name")
        )
        invitation_by_guest = {item.guest_id: item for item in invitations}

        rsvps = list(
            RSVP.objects.filter(wedding=wedding)
            .select_related("invitation")
        )
        rsvp_by_invitation = {item.invitation_id: item for item in rsvps}

        q = request.GET.get("q", "").strip().lower()
        status = request.GET.get("status", "").strip()

        for guest in guests:
            invitation = invitation_by_guest.get(guest.id)
            rsvp = rsvp_by_invitation.get(invitation.id) if invitation else None

            if q:
                haystack = " ".join(
                    [
                        guest.name or "",
                        guest.phone or "",
                        guest.email or "",
                        guest.public_id or "",
                    ]
                ).lower()
                if q not in haystack:
                    continue

            if status == "MISSING" and invitation:
                continue
            if status and status != "MISSING":
                if not invitation or invitation.status != status:
                    continue

            rows.append(
                {
                    "guest": guest,
                    "invitation": invitation,
                    "rsvp": rsvp,
                }
            )

        counts["guests"] = len(guests)
        counts["generated"] = len(invitations)
        counts["opened"] = sum(1 for item in invitations if item.open_count > 0)
        counts["responded"] = len(rsvps)
        counts["missing"] = max(len(guests) - len(invitations), 0)

    return render(
        request,
        "invitations/list.html",
        {
            "wedding": wedding,
            "rows": rows,
            "counts": counts,
            "status_choices": Invitation.Status.choices,
        },
    )


@login_required
def generate_missing_invitations(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    wedding = get_wedding_for_user(request.user, PERM_MANAGE_INVITATIONS)
    if not wedding:
        messages.info(request, "Create your wedding first.")
        return redirect("weddings:overview")

    created = 0
    for guest in Guest.objects.filter(wedding=wedding, status=Guest.Status.ACTIVE):
        _, was_created = Invitation.objects.get_or_create(
            wedding=wedding,
            guest=guest,
            defaults={"status": Invitation.Status.READY},
        )
        if was_created:
            created += 1

    if created:
        messages.success(request, f"{created} invitation(s) generated.")
    else:
        messages.info(request, "All active guests already have invitations.")

    return redirect("invitations:list")


@login_required
def generate_guest_invitation(request, guest_public_id):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    wedding = get_wedding_for_user(request.user, PERM_MANAGE_INVITATIONS)
    if not wedding:
        raise Http404("Wedding not found")

    guest = get_object_or_404(
        Guest,
        wedding=wedding,
        public_id=guest_public_id,
    )
    invitation, created = Invitation.objects.get_or_create(
        wedding=wedding,
        guest=guest,
        defaults={"status": Invitation.Status.READY},
    )

    if created:
        messages.success(request, f"Invitation generated for {guest.name}.")
    else:
        messages.info(request, f"{guest.name} already has an invitation.")

    return redirect("invitations:list")


@login_required
def invitation_action(request, invitation_id):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    invitation = _owned_invitation(request.user, invitation_id)
    action = request.POST.get("action", "").strip()

    if action == "mark_sent":
        invitation.status = Invitation.Status.SENT
        invitation.sent_at = timezone.now()
        invitation.save(update_fields=["status", "sent_at", "updated_at"])
        messages.success(request, f"{invitation.guest.name} marked as sent.")
    elif action == "revoke":
        invitation.status = Invitation.Status.REVOKED
        invitation.revoked_at = timezone.now()
        invitation.save(update_fields=["status", "revoked_at", "updated_at"])
        messages.success(request, f"{invitation.guest.name}'s invitation was revoked.")
    elif action == "restore":
        invitation.status = Invitation.Status.READY
        invitation.revoked_at = None
        invitation.save(update_fields=["status", "revoked_at", "updated_at"])
        messages.success(request, f"{invitation.guest.name}'s invitation is active again.")
    else:
        return HttpResponseBadRequest("Unknown action")

    return redirect("invitations:list")
