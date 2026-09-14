from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from invitations.models import Invitation
from modules.services import module_available
from staffing.access import PERM_MANAGE_WEDDING, get_wedding_for_user

from .forms import WeddingTransportationSettingsForm
from .services import destination_payload, ensure_settings, lookup_routes, map_urls


@login_required
def settings_view(request):
    wedding = get_wedding_for_user(request.user, PERM_MANAGE_WEDDING)
    if wedding is None:
        raise Http404("Wedding not found")
    if not module_available("transportation", user=request.user, wedding=wedding, check_role=True):
        messages.warning(request, "Transportation is not available for this wedding.")
        return redirect("modules:wedding_modules")

    settings_obj = ensure_settings(wedding)
    if request.method == "POST":
        form = WeddingTransportationSettingsForm(request.POST, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Transportation settings updated.")
            return redirect("transportation:settings")
    else:
        form = WeddingTransportationSettingsForm(instance=settings_obj)

    google_maps_url, apple_maps_url = map_urls(wedding)
    return render(
        request,
        "transportation/settings.html",
        {
            "wedding": wedding,
            "form": form,
            "transport_settings": settings_obj,
            "destination": destination_payload(wedding),
            "google_maps_url": google_maps_url,
            "apple_maps_url": apple_maps_url,
        },
    )


def guest_guide(request, token):
    invitation = get_object_or_404(
        Invitation.objects.select_related("wedding", "guest"),
        token=token,
    )
    if invitation.status in [Invitation.Status.REVOKED, Invitation.Status.EXPIRED]:
        raise Http404("Invitation unavailable")
    wedding = invitation.wedding
    if not module_available("transportation", wedding=wedding, check_role=False):
        raise Http404("Transportation guide unavailable")

    settings_obj = ensure_settings(wedding)
    if not settings_obj.guide_enabled or not settings_obj.bus_guide_enabled:
        raise Http404("Bus guide unavailable")

    google_maps_url, apple_maps_url = map_urls(wedding)
    route_result = lookup_routes(wedding, settings_obj=settings_obj)
    return render(
        request,
        "transportation/guest_guide.html",
        {
            "wedding": wedding,
            "guest": invitation.guest,
            "invitation": invitation,
            "transport_settings": settings_obj,
            "destination": destination_payload(wedding),
            "google_maps_url": google_maps_url,
            "apple_maps_url": apple_maps_url,
            "route_result": route_result,
        },
    )
