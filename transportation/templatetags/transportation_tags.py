from django import template
from django.urls import reverse

from modules.services import module_available
from transportation.services import destination_payload, ensure_settings, map_urls

register = template.Library()


@register.inclusion_tag("transportation/invitation_block.html", takes_context=True)
def transportation_block(context, wedding, invitation):
    if not module_available("transportation", wedding=wedding, check_role=False):
        return {"enabled": False}

    settings_obj = ensure_settings(wedding)
    if not settings_obj.guide_enabled:
        return {"enabled": False}

    google_maps_url, apple_maps_url = map_urls(wedding)
    destination = destination_payload(wedding)
    bus_guide_url = ""
    if settings_obj.bus_guide_enabled:
        bus_guide_url = reverse("transportation:guest_guide", kwargs={"token": invitation.token})

    return {
        "enabled": True,
        "request": context.get("request"),
        "wedding": wedding,
        "invitation": invitation,
        "transport_settings": settings_obj,
        "destination": destination,
        "google_maps_url": google_maps_url,
        "apple_maps_url": apple_maps_url,
        "bus_guide_url": bus_guide_url,
    }
