from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from invitations.models import Invitation
from staffing.access import PERM_MANAGE_WEDDING, get_wedding_for_user

from .forms import WeddingEventSettingsForm
from .services import build_ics, ensure_settings


@login_required
def settings_view(request):
    wedding = get_wedding_for_user(request.user, PERM_MANAGE_WEDDING)
    if wedding is None:
        raise Http404("Wedding not found")

    settings_obj = ensure_settings(wedding)
    if request.method == "POST":
        form = WeddingEventSettingsForm(request.POST, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Calendar and invitation venue display settings updated.")
            return redirect("event_tools:settings")
    else:
        form = WeddingEventSettingsForm(instance=settings_obj)

    return render(
        request,
        "event_tools/settings.html",
        {"wedding": wedding, "form": form, "event_settings": settings_obj},
    )


def calendar_ics(request, token):
    invitation = get_object_or_404(
        Invitation.objects.select_related("wedding", "guest"), token=token
    )
    if invitation.status in [Invitation.Status.REVOKED, Invitation.Status.EXPIRED]:
        raise Http404("Invitation unavailable")
    settings_obj = ensure_settings(invitation.wedding)
    if not settings_obj.calendar_enabled or invitation.wedding.wedding_date is None:
        raise Http404("Calendar event unavailable")

    body = build_ics(request, invitation, settings_obj)
    response = HttpResponse(body, content_type="text/calendar; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{invitation.wedding.slug}-wedding.ics"'
    return response
