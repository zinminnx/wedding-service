from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from invitations.models import Invitation
from weddings.models import Wedding

from .models import RSVP


def _wedding_for_user(user):
    qs = Wedding.objects.all()
    if not user.is_superuser:
        qs = qs.filter(owner=user)
    return qs.order_by("-created_at").first()


@login_required
def rsvp_list(request):
    wedding = _wedding_for_user(request.user)
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
        {
            "wedding": wedding,
            "invitations": invitations,
            "counts": counts,
        },
    )
