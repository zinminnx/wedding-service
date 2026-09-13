from django import template

from staffing.access import access_summary


register = template.Library()


@register.simple_tag
def wedding_access(user, wedding):
    return access_summary(user, wedding)
