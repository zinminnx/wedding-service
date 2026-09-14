from datetime import timedelta, timezone as dt_timezone
from urllib.parse import quote, urlencode

from django.urls import reverse


ICS_ESCAPE = str.maketrans({"\\": "\\\\", ";": "\\;", ",": "\\,", "\n": "\\n", "\r": ""})


def ensure_settings(wedding):
    from .models import WeddingEventSettings

    settings_obj, _ = WeddingEventSettings.objects.get_or_create(wedding=wedding)
    return settings_obj


def _event_times(wedding, settings_obj):
    start = wedding.wedding_date
    if start is None:
        return None, None
    if start.tzinfo is None:
        start = start.replace(tzinfo=dt_timezone.utc)
    end = start + timedelta(minutes=settings_obj.event_duration_minutes or 240)
    return start, end


def _utc_stamp(value):
    return value.astimezone(dt_timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def location_text(wedding):
    parts = [wedding.wedding_location, wedding.venue_full_address, wedding.venue_landmark]
    return ", ".join(part.strip() for part in parts if part and part.strip())


def build_google_calendar_url(request, invitation, settings_obj):
    start, end = _event_times(invitation.wedding, settings_obj)
    if start is None:
        return ""
    details = settings_obj.calendar_description.strip()
    invite_url = request.build_absolute_uri(reverse("invitations:detail", kwargs={"token": invitation.token}))
    if invite_url:
        details = (details + "\n\n" if details else "") + f"Invitation: {invite_url}"
    query = urlencode(
        {
            "action": "TEMPLATE",
            "text": settings_obj.effective_title,
            "dates": f"{_utc_stamp(start)}/{_utc_stamp(end)}",
            "details": details,
            "location": location_text(invitation.wedding),
        }
    )
    return f"https://calendar.google.com/calendar/render?{query}"


def build_map_urls(wedding):
    venue_name = (wedding.wedding_location or "").strip()
    google_override = (wedding.google_maps_url or "").strip()

    if wedding.venue_latitude is not None and wedding.venue_longitude is not None:
        coords = f"{wedding.venue_latitude},{wedding.venue_longitude}"
        google = google_override or f"https://www.google.com/maps/search/?api=1&query={quote(coords)}"
        apple = f"https://maps.apple.com/?q={quote(venue_name or 'Wedding Venue')}&ll={quote(coords)}"
        return google, apple

    query = location_text(wedding)
    google = google_override
    if not google and query:
        google = f"https://www.google.com/maps/search/?api=1&query={quote(query)}"
    apple = f"https://maps.apple.com/?q={quote(query)}" if query else ""
    return google, apple


def build_ics(request, invitation, settings_obj):
    start, end = _event_times(invitation.wedding, settings_obj)
    if start is None:
        return ""

    invite_url = request.build_absolute_uri(reverse("invitations:detail", kwargs={"token": invitation.token}))
    description = settings_obj.calendar_description.strip()
    if invite_url:
        description = (description + "\n\n" if description else "") + f"Invitation: {invite_url}"

    def esc(value):
        return (value or "").translate(ICS_ESCAPE)

    alarms = []
    for minutes in [settings_obj.reminder_1_minutes, settings_obj.reminder_2_minutes, settings_obj.reminder_3_minutes]:
        if minutes and minutes > 0:
            alarms.extend(
                [
                    "BEGIN:VALARM",
                    f"TRIGGER:-PT{int(minutes)}M",
                    "ACTION:DISPLAY",
                    f"DESCRIPTION:{esc(settings_obj.effective_title)}",
                    "END:VALARM",
                ]
            )

    uid = f"everafter-{invitation.wedding.public_id}-{invitation.pk}@everafter"
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//EverAfter//Wedding Calendar//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTART:{_utc_stamp(start)}",
        f"DTEND:{_utc_stamp(end)}",
        f"SUMMARY:{esc(settings_obj.effective_title)}",
        f"DESCRIPTION:{esc(description)}",
        f"LOCATION:{esc(location_text(invitation.wedding))}",
        f"URL:{esc(invite_url)}",
        *alarms,
        "END:VEVENT",
        "END:VCALENDAR",
        "",
    ]
    return "\r\n".join(lines)
