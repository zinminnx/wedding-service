from django import template

from invitation_themes.services import public_section_state, resolve_live_design


register = template.Library()


@register.simple_tag
def invitation_live_design(wedding):
    return resolve_live_design(wedding)


@register.simple_tag
def invitation_live_sections(wedding):
    return public_section_state(wedding)
