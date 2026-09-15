"""Canonical invitation section registry for EverVow.

The registry is intentionally code-owned. Wedding owners store only section keys,
enabled state and order. Theme markup remains shared and controlled by the platform.
"""

SECTION_DEFINITIONS = (
    {
        "key": "hero",
        "label": "Hero",
        "description": "Couple names, wedding date and the main visual introduction.",
        "template": "invitation_themes/sections/hero.html",
        "default_enabled": True,
        "fixed_first": True,
    },
    {
        "key": "story",
        "label": "Couple Story",
        "description": "A short couple-focused introduction block.",
        "template": "invitation_themes/sections/story.html",
        "default_enabled": False,
    },
    {
        "key": "event",
        "label": "Event Details",
        "description": "Date, time and invitation party size.",
        "template": "invitation_themes/sections/event.html",
        "default_enabled": True,
    },
    {
        "key": "calendar",
        "label": "Calendar",
        "description": "Save-the-date and calendar actions. The functional calendar integration arrives in v10.8.",
        "template": "invitation_themes/sections/calendar.html",
        "default_enabled": False,
        "available_now": False,
        "availability_note": "Calendar integration · v10.8",
    },
    {
        "key": "venue",
        "label": "Venue",
        "description": "Wedding venue and location details.",
        "template": "invitation_themes/sections/venue.html",
        "default_enabled": False,
    },
    {
        "key": "maps",
        "label": "Maps",
        "description": "A direct venue map link using the wedding location already stored in EverVow.",
        "template": "invitation_themes/sections/maps.html",
        "default_enabled": False,
    },
    {
        "key": "transportation",
        "label": "Transportation",
        "description": "Guest travel guidance, smart maps and optional Bus Project route lookup.",
        "template": "invitation_themes/sections/transportation.html",
        "default_enabled": False,
        "runtime_module": "transportation",
    },
    {
        "key": "schedule",
        "label": "Schedule",
        "description": "A simple wedding-day schedule block ready for future planner timeline data.",
        "template": "invitation_themes/sections/schedule.html",
        "default_enabled": False,
    },
    {
        "key": "rsvp",
        "label": "RSVP",
        "description": "Guest attendance response and party count.",
        "template": "invitation_themes/sections/rsvp.html",
        "default_enabled": True,
        "runtime_module": "rsvp",
    },
    {
        "key": "photos",
        "label": "Guest Photos",
        "description": "Guest photo upload entry point.",
        "template": "invitation_themes/sections/photos.html",
        "default_enabled": True,
        "runtime_module": "photos",
    },
    {
        "key": "gift",
        "label": "Gift",
        "description": "Optional gift preference and enabled wedding payment methods.",
        "template": "invitation_themes/sections/gift.html",
        "default_enabled": True,
        "runtime_module": "gifts",
    },
    {
        "key": "entry_pass",
        "label": "Entrance Pass",
        "description": "Secure reception QR entry pass. Personal data is not stored in the QR token.",
        "template": "invitation_themes/sections/entry_pass.html",
        "default_enabled": True,
        "runtime_module": "checkins",
    },
    {
        "key": "gallery",
        "label": "Gallery",
        "description": "Wedding gallery/capture presentation block.",
        "template": "invitation_themes/sections/gallery.html",
        "default_enabled": True,
        "runtime_module": "photos",
    },
)

SECTION_MAP = {item["key"]: item for item in SECTION_DEFINITIONS}
SECTION_KEYS = tuple(item["key"] for item in SECTION_DEFINITIONS)
REQUIRED_THEME_SECTIONS = frozenset(SECTION_KEYS)


def default_section_config():
    """Return JSON-safe default state while preserving the legacy public order."""
    return [
        {"key": item["key"], "enabled": bool(item.get("default_enabled", False)), "sort_order": index * 10}
        for index, item in enumerate(SECTION_DEFINITIONS, start=1)
    ]


def normalize_section_config(raw_config, *, supported_sections=None):
    """Normalize untrusted JSON section state against the canonical registry.

    Unknown keys are discarded, missing keys are appended, unavailable future
    sections are forced off, and Hero is always kept in the first position so
    existing theme layouts remain structurally stable.
    """
    supported = set(supported_sections or SECTION_KEYS)
    raw_config = raw_config if isinstance(raw_config, list) else []
    incoming = {}
    incoming_order = []

    for row in raw_config:
        if not isinstance(row, dict):
            continue
        key = str(row.get("key") or "").strip()
        if key not in SECTION_MAP or key in incoming:
            continue
        incoming[key] = row
        incoming_order.append(key)

    for key in SECTION_KEYS:
        if key not in incoming_order:
            incoming_order.append(key)

    # Hero is fixed first for reliable theme structure; every other section can move.
    incoming_order = ["hero"] + [key for key in incoming_order if key != "hero"]

    normalized = []
    for index, key in enumerate(incoming_order, start=1):
        definition = SECTION_MAP[key]
        row = incoming.get(key, {})
        enabled = bool(row.get("enabled", definition.get("default_enabled", False)))
        if key not in supported or definition.get("available_now", True) is False:
            enabled = False
        normalized.append({"key": key, "enabled": enabled, "sort_order": index * 10})
    return normalized
