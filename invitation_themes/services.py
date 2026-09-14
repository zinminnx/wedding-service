import re
from dataclasses import dataclass

from modules.services import module_available

from .models import InvitationTheme, WeddingInvitationDesign
from .sections import SECTION_MAP, default_section_config, normalize_section_config


HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


@dataclass(frozen=True)
class ResolvedInvitationDesign:
    theme: InvitationTheme
    customization: dict
    is_fallback: bool = False

    @property
    def accent(self):
        custom = (self.customization or {}).get("accent")
        if custom and HEX_RE.fullmatch(str(custom)):
            return custom
        configured = (self.theme.config or {}).get("accent")
        return configured if configured and HEX_RE.fullmatch(str(configured)) else "#B98A45"

    @property
    def hero_message(self):
        value = (self.customization or {}).get("hero_message", "")
        return str(value).strip()[:140] or "A new chapter, together."


def default_theme():
    qs = InvitationTheme.objects.filter(
        status=InvitationTheme.Status.PUBLISHED,
        visible=True,
    )
    return qs.filter(is_default=True).first() or qs.order_by("sort_order", "name").first()


def get_or_create_design(wedding):
    design, _ = WeddingInvitationDesign.objects.get_or_create(wedding=wedding)
    changed = []
    if design.draft_theme_id is None:
        fallback = design.published_theme or default_theme()
        if fallback:
            design.draft_theme = fallback
            changed.append("draft_theme")
    if not design.draft_sections:
        source = design.published_sections or default_section_config()
        supported = design.draft_theme.supported_sections if design.draft_theme_id else None
        design.draft_sections = normalize_section_config(source, supported_sections=supported)
        changed.append("draft_sections")
    if changed:
        changed.append("updated_at")
        design.save(update_fields=changed)
    return design


def resolve_live_design(wedding):
    design = WeddingInvitationDesign.objects.select_related("published_theme").filter(wedding=wedding).first()
    if design and design.published_theme_id:
        # A theme disabled by Main Admin must continue rendering for weddings
        # that had already published it.
        return ResolvedInvitationDesign(
            theme=design.published_theme,
            customization=design.published_customization or {},
            is_fallback=False,
        )
    fallback = default_theme()
    if fallback is None:
        fallback = InvitationTheme(
            name="EverAfter Classic",
            key="ivory-gold-classic",
            layout_key="classic",
            config={"accent": "#B98A45"},
            supported_sections=list(SECTION_MAP),
        )
    return ResolvedInvitationDesign(theme=fallback, customization={}, is_fallback=True)


def selectable_themes():
    return InvitationTheme.objects.filter(
        status=InvitationTheme.Status.PUBLISHED,
        visible=True,
    ).order_by("sort_order", "name")


def can_select_theme(theme):
    return bool(theme and theme.status == InvitationTheme.Status.PUBLISHED and theme.visible)


def can_publish_draft(design):
    theme = design.draft_theme
    if theme is None:
        return False
    if can_select_theme(theme):
        return True
    # Existing weddings using a disabled theme may republish customization for
    # that same theme, but cannot re-select it after moving away.
    return design.published_theme_id == theme.id


def draft_section_config(design):
    theme = design.draft_theme
    supported = theme.supported_sections if theme else None
    source = design.draft_sections or design.published_sections or default_section_config()
    return normalize_section_config(source, supported_sections=supported)


def public_section_state(wedding):
    """Return a safe public section stream for the live invitation.

    Section visibility requires both the published section switch and the
    corresponding runtime module where applicable. This prevents a disabled
    RSVP/Gift/Photo/Check-in module from leaking back into the public invitation.
    """
    design = (
        WeddingInvitationDesign.objects.select_related("published_theme")
        .filter(wedding=wedding)
        .first()
    )
    theme = design.published_theme if design and design.published_theme_id else default_theme()
    supported = theme.supported_sections if theme else None
    source = design.published_sections if design and design.published_sections else default_section_config()
    rows = normalize_section_config(source, supported_sections=supported)

    resolved = []
    for row in rows:
        definition = SECTION_MAP[row["key"]]
        enabled = bool(row["enabled"])
        runtime_module = definition.get("runtime_module")
        if enabled and runtime_module:
            enabled = module_available(runtime_module, wedding=wedding, check_role=False)
        if not enabled:
            continue
        resolved.append({**definition, **row})

    hero = next((item for item in resolved if item["key"] == "hero"), None)
    content = [item for item in resolved if item["key"] != "hero"]
    return {"hero": hero, "content": content, "all": resolved}


def studio_section_rows(design, wedding):
    rows = draft_section_config(design)
    result = []
    for row in rows:
        definition = SECTION_MAP[row["key"]]
        runtime_module = definition.get("runtime_module")
        runtime_available = True
        runtime_reason = ""
        if definition.get("available_now", True) is False:
            runtime_available = False
            runtime_reason = definition.get("availability_note", "Not available yet")
        elif runtime_module and not module_available(runtime_module, wedding=wedding, check_role=False):
            runtime_available = False
            runtime_reason = f"{definition['label']} module is not available for this wedding"
        result.append({
            **definition,
            **row,
            "runtime_available": runtime_available,
            "runtime_reason": runtime_reason,
        })
    return result
