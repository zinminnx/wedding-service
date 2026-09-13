from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import redirect, render

from guests.models import Guest
from invitations.models import Invitation
from rsvp.models import RSVP
from staffing.access import (
    PERM_MANAGE_WEDDING,
    PERM_VIEW_DASHBOARD,
    can_create_wedding,
    get_wedding_for_user,
)

from .forms import WeddingForm


@login_required
def dashboard(request):
    wedding = get_wedding_for_user(request.user, PERM_VIEW_DASHBOARD)

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

    return render(
        request,
        "dashboard/home.html",
        {
            "wedding": wedding,
            "stats": stats,
            "recent_guests": recent_guests,
            "recent_invites": recent_invites,
        },
    )


@login_required
def wedding_overview(request):
    wedding = get_wedding_for_user(request.user, PERM_MANAGE_WEDDING)
    any_wedding = get_wedding_for_user(request.user)

    if wedding is None and any_wedding is not None:
        messages.error(request, "Your role does not allow editing wedding settings.")
        return redirect("weddings:dashboard")

    creating = wedding is None
    if creating and not can_create_wedding(request.user):
        messages.error(request, "Your account is not allowed to create a wedding workspace.")
        return redirect("weddings:dashboard")

    if request.method == "POST":
        form = WeddingForm(request.POST, instance=wedding)
        if form.is_valid():
            wedding = form.save(commit=False)

            if creating:
                wedding.owner = request.user

            action = request.POST.get("action", "save")
            if action == "draft":
                wedding.status = wedding.Status.DRAFT

            wedding.save()
            form.save_m2m()

            if action == "continue":
                messages.success(request, "Wedding details saved. You can add guests next.")
                return redirect("guests:list")

            messages.success(request, "Wedding details saved successfully.")
            return redirect("weddings:overview")
    else:
        form = WeddingForm(instance=wedding)

    return render(
        request,
        "dashboard/wedding_overview.html",
        {
            "wedding": wedding,
            "form": form,
            "creating": creating,
        },
    )
