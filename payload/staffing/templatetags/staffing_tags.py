from django import template

from staffing.access import access_summary, accessible_weddings


register = template.Library()


@register.simple_tag
def wedding_access(user, wedding):
    return access_summary(user, wedding)


@register.simple_tag
def wedding_choices(user):
    return accessible_weddings(user).order_by("-created_at")
