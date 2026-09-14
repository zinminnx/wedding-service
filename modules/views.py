from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from staffing.access import get_wedding_for_user

from .models import FeatureModule, WeddingModuleProfile, WeddingModuleSetting
from .services import (
    active_dependent_modules,
    can_manage_wedding_modules,
    get_package_for_wedding,
    module_state,
)


def _current_wedding_or_redirect(request):
    wedding = get_wedding_for_user(request.user)
    if wedding is None:
        messages.info(request, "Create or select a wedding first.")
        return None, redirect("weddings:list")
    if not can_manage_wedding_modules(request.user, wedding):
        messages.error(request, "Only the Wedding Owner can change wedding modules.")
        return None, redirect("weddings:dashboard")
    return wedding, None


@login_required
def wedding_modules(request):
    wedding, response = _current_wedding_or_redirect(request)
    if response:
        return response

    package = get_package_for_wedding(wedding)
    cards = []
    modules = FeatureModule.objects.filter(visible_to_weddings=True).prefetch_related("dependencies")
    for feature in modules:
        state = module_state(feature.key, user=request.user, wedding=wedding)
        if state is None:
            continue
        dependents = active_dependent_modules(feature, wedding) if not feature.is_core else []
        cards.append({
            "feature": feature,
            "state": state,
            "dependents": dependents,
        })

    return render(
        request,
        "modules/wedding_modules.html",
        {
            "wedding": wedding,
            "package": package,
            "module_cards": cards,
        },
    )


@login_required
@require_POST
def toggle_wedding_module(request, module_key):
    wedding, response = _current_wedding_or_redirect(request)
    if response:
        return response

    feature = get_object_or_404(FeatureModule, key=module_key)
    if feature.is_core:
        messages.error(request, f"{feature.name} is a core module and cannot be disabled.")
        return redirect("modules:wedding_modules")

    desired_enabled = request.POST.get("enabled") == "1"
    state = module_state(feature.key, user=request.user, wedding=wedding, check_role=False)
    if desired_enabled:
        if not state.system_allowed:
            messages.error(request, f"{feature.name} is disabled by Main Admin.")
            return redirect("modules:wedding_modules")
        if not state.package_allowed:
            messages.error(request, f"{feature.name} is not included in this wedding package.")
            return redirect("modules:wedding_modules")
        if not state.dependencies_ok:
            messages.error(request, f"Enable the required modules before enabling {feature.name}.")
            return redirect("modules:wedding_modules")
    else:
        dependents = active_dependent_modules(feature, wedding)
        if dependents:
            names = ", ".join(item.name for item in dependents)
            messages.error(request, f"Cannot disable {feature.name}; currently required by: {names}.")
            return redirect("modules:wedding_modules")

    WeddingModuleSetting.objects.update_or_create(
        wedding=wedding,
        module=feature,
        defaults={"enabled": desired_enabled, "updated_by": request.user},
    )
    action = "enabled" if desired_enabled else "disabled"
    messages.success(request, f"{feature.name} has been {action} for {wedding.name}.")
    return redirect("modules:wedding_modules")
