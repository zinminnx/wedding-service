from django import template

from event_tools.services import build_google_calendar_url, build_map_urls, ensure_settings

register = template.Library()


@register.inclusion_tag("event_tools/invitation_tools.html", takes_context=True)
def event_tools_block(context, wedding, invitation):
    request = context.get("request")
    settings_obj = ensure_settings(wedding)
    google_calendar_url = ""
    if request and settings_obj.calendar_enabled:
        google_calendar_url = build_google_calendar_url(request, invitation, settings_obj)
    google_maps_url, apple_maps_url = build_map_urls(wedding)
    return {
        "request": request,
        "wedding": wedding,
        "invitation": invitation,
        "event_settings": settings_obj,
        "google_calendar_url": google_calendar_url,
        "google_maps_url": google_maps_url,
        "apple_maps_url": apple_maps_url,
    }
