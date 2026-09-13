from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from invitations.models import Invitation
from staffing.access import PERM_VIEW_RSVP, get_wedding_for_user

from .models import RSVP


@login_required
def rsvp_list(request):
    wedding = get_wedding_for_user(request.user, PERM_VIEW_RSVP)
    invitations = Invitation.objects.none()

    if wedding:
        invitations = (
            Invitation.objects.filter(wedding=wedding)
            .select_related("guest")
            .order_by("guest__name")
        )

    counts = {
        "attending": 0,
        "not_attending": 0,
        "maybe": 0,
        "pending": 0,
    }

    if wedding:
        counts["attending"] = RSVP.objects.filter(
            wedding=wedding,
            response=RSVP.Response.ATTENDING,
        ).count()
        counts["not_attending"] = RSVP.objects.filter(
            wedding=wedding,
            response=RSVP.Response.NOT_ATTENDING,
        ).count()
        counts["maybe"] = RSVP.objects.filter(
            wedding=wedding,
            response=RSVP.Response.MAYBE,
        ).count()
        counts["pending"] = max(invitations.count() - sum(counts.values()), 0)

    return render(
        request,
        "rsvp/list.html",
        {"wedding": wedding, "invitations": invitations, "counts": counts},
    )
