from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from guests.models import Guest
from invitations.models import Invitation
from rsvp.models import RSVP
from staffing.access import (
    PERM_MANAGE_WEDDING,
    PERM_VIEW_DASHBOARD,
    accessible_weddings,
    can_create_wedding,
    get_wedding_for_user,
    set_active_wedding,
)

from .forms import WeddingForm


def _dashboard_stats(wedding):
    stats = {
        "guests": 0,
        "party_total": 0,
        "invites": 0,
        "opened": 0,
        "rsvp_attending": 0,
        "rsvp_people": 0,
        "rsvp_pending": 0,
    }
    recent_guests = Guest.objects.none()
    recent_invites = Invitation.objects.none()

    if wedding:
        guests = Guest.objects.filter(wedding=wedding)
        invites = Invitation.objects.filter(wedding=wedding)
        attending = RSVP.objects.filter(
            wedding=wedding,
            response=RSVP.Response.ATTENDING,
        )
        rsvp_people = (
            attending.aggregate(total=Sum("attending_adults"))["total"] or 0
        ) + (
            attending.aggregate(total=Sum("attending_children"))["total"] or 0
        )
        responded = RSVP.objects.filter(wedding=wedding).count()

        stats = {
            "guests": guests.count(),
            "party_total": guests.aggregate(total=Sum("allowed_party_size"))["total"] or 0,
            "invites": invites.count(),
            "opened": invites.filter(status=Invitation.Status.OPENED).count(),
            "rsvp_attending": attending.count(),
            "rsvp_people": rsvp_people,
            "rsvp_pending": max(invites.count() - responded, 0),
        }
        recent_guests = guests.order_by("-created_at")[:5]
        recent_invites = invites.select_related("guest").order_by("-updated_at")[:5]

    return stats, recent_guests, recent_invites


@login_required
def dashboard(request):
    wedding = get_wedding_for_user(request.user, PERM_VIEW_DASHBOARD)
    stats, recent_guests, recent_invites = _dashboard_stats(wedding)

    return render(
        request,
        "dashboard/home.html",
        {
            "wedding": wedding,
            "stats": stats,
            "recent_guests": recent_guests,
            "recent_invites": recent_invites,
            "can_create_wedding": can_create_wedding(request.user),
        },
    )


@login_required
def wedding_list(request):
    wedding = get_wedding_for_user(request.user, PERM_VIEW_DASHBOARD)
    weddings = accessible_weddings(request.user).order_by("-created_at")
    return render(
        request,
        "dashboard/wedding_list.html",
        {
            "wedding": wedding,
            "weddings": weddings,
            "can_create_wedding": can_create_wedding(request.user),
        },
    )


def _save_wedding_form(request, wedding=None, *, creating=False):
    form = WeddingForm(request.POST or None, instance=wedding)
    if request.method != "POST" or not form.is_valid():
        return form, None

    saved_wedding = form.save(commit=False)
    if creating:
        saved_wedding.owner = request.user

    action = request.POST.get("action", "save")
    if action == "draft":
        saved_wedding.status = saved_wedding.Status.DRAFT

    saved_wedding.save()
    form.save_m2m()
    set_active_wedding(request.user, saved_wedding)
    return form, action


@login_required
def wedding_overview(request):
    wedding = get_wedding_for_user(request.user, PERM_MANAGE_WEDDING)
    selected_wedding = get_wedding_for_user(request.user)

    if wedding is None and selected_wedding is not None:
        messages.error(request, "Your role does not allow editing this wedding's settings.")
        return redirect("weddings:dashboard")

    creating = wedding is None
    if creating and not can_create_wedding(request.user):
        messages.error(request, "Your account is not allowed to create a wedding workspace.")
        return redirect("weddings:dashboard")

    form, action = _save_wedding_form(request, wedding, creating=creating)
    if action:
        if action == "continue":
            messages.success(request, "Wedding details saved. You can add guests next.")
            return redirect("guests:list")
        messages.success(request, "Wedding details saved successfully.")
        return redirect("weddings:overview")

    return render(
        request,
        "dashboard/wedding_overview.html",
        {
            "wedding": wedding,
            "form": form,
            "creating": creating,
        },
    )


@login_required
def wedding_create(request):
    if not can_create_wedding(request.user):
        messages.error(request, "Your account is not allowed to create another wedding workspace.")
        return redirect("weddings:list")

    form, action = _save_wedding_form(request, None, creating=True)
    if action:
        if action == "continue":
            messages.success(request, "New wedding created. You can add guests next.")
            return redirect("guests:list")
        messages.success(request, "New wedding created and selected as your current workspace.")
        return redirect("weddings:overview")

    return render(
        request,
        "dashboard/wedding_overview.html",
        {
            "wedding": None,
            "form": form,
            "creating": True,
        },
    )


@login_required
@require_POST
def switch_wedding(request, public_id):
    wedding = get_object_or_404(accessible_weddings(request.user), public_id=public_id)
    set_active_wedding(request.user, wedding)
    messages.success(request, f"Switched to {wedding.name}.")

    destination = request.POST.get("destination", "dashboard")
    if destination == "details":
        return redirect("weddings:overview")
    return redirect("weddings:dashboard")
