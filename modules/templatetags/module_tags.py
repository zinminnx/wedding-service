from django import template

from modules.services import can_manage_wedding_modules, enabled_module_keys

register = template.Library()


@register.simple_tag
def wedding_module_keys(user, wedding):
    return enabled_module_keys(user, wedding)


@register.simple_tag
def module_manager(user, wedding):
    return can_manage_wedding_modules(user, wedding)
