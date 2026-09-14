from dataclasses import dataclass

from django.db.models import Prefetch

from .models import FeatureModule, ServicePackage, WeddingModuleProfile, WeddingModuleSetting


OWNER_ROLES = {"SUPER_ADMIN", "ADMIN", "WEDDING_OWNER"}


@dataclass
class ModuleState:
    module: FeatureModule
    system_allowed: bool
    package_allowed: bool
    wedding_enabled: bool
    role_allowed: bool
    dependencies_ok: bool
    available: bool
    package: ServicePackage | None
    dependency_names: list[str]
    blocked_reason: str = ""


def get_package_for_wedding(wedding):
    if not wedding:
        return None
    profile = (
        WeddingModuleProfile.objects.select_related("package")
        .filter(wedding=wedding)
        .first()
    )
    if profile and profile.package_id:
        return profile.package
    return ServicePackage.objects.filter(is_active=True, is_default=True).first()


def get_user_role(user, wedding):
    if not user or not getattr(user, "is_authenticated", False) or not wedding:
        return None
    if getattr(user, "is_superuser", False):
        return "SUPER_ADMIN"
    if wedding.owner_id == user.id:
        return "WEDDING_OWNER"
    try:
        from staffing.access import get_user_wedding_role
        return get_user_wedding_role(user, wedding)
    except Exception:
        return getattr(user, "role", None)


def _package_allows(module, package):
    if module.is_core:
        return True
    if package is None:
        # Backward-compatible fallback for existing weddings without a package profile.
        return True
    return package.modules.filter(pk=module.pk).exists()


def _wedding_enabled(module, wedding):
    if module.is_core or not wedding:
        return True
    setting = WeddingModuleSetting.objects.filter(wedding=wedding, module=module).only("enabled").first()
    return True if setting is None else setting.enabled


def _role_allows(module, user, wedding, check_role=True):
    if not check_role or not module.allowed_roles:
        return True
    role = get_user_role(user, wedding)
    # Platform admins and the Wedding Owner are authority roles. They must not
    # be blocked simply because a module's operational role allow-list only
    # names staff roles. Package/system/wedding/dependency gates still apply.
    if role in OWNER_ROLES:
        return True
    return role in set(module.allowed_roles)


def _dependency_base_available(module, wedding, package, visited=None):
    visited = set() if visited is None else visited
    if module.pk in visited:
        return True
    visited.add(module.pk)
    for dependency in module.dependencies.all():
        if not (dependency.is_core or dependency.system_enabled):
            return False
        if not _package_allows(dependency, package):
            return False
        if not _wedding_enabled(dependency, wedding):
            return False
        if not _dependency_base_available(dependency, wedding, package, visited):
            return False
    return True


def module_state(module_key, user=None, wedding=None, check_role=True):
    module = (
        FeatureModule.objects.prefetch_related("dependencies")
        .filter(key=module_key)
        .first()
    )
    if module is None:
        return None

    package = get_package_for_wedding(wedding)
    system_allowed = module.is_core or module.system_enabled
    package_allowed = _package_allows(module, package)
    wedding_enabled = _wedding_enabled(module, wedding)
    role_allowed = _role_allows(module, user, wedding, check_role=check_role)
    dependencies_ok = _dependency_base_available(module, wedding, package)
    available = all((system_allowed, package_allowed, wedding_enabled, role_allowed, dependencies_ok))

    reason = ""
    if not system_allowed:
        reason = "Disabled by Main Admin"
    elif not package_allowed:
        reason = "Not included in this package"
    elif not wedding_enabled:
        reason = "Disabled for this wedding"
    elif not dependencies_ok:
        reason = "Required module is unavailable"
    elif not role_allowed:
        reason = "Your role does not allow this module"

    return ModuleState(
        module=module,
        system_allowed=system_allowed,
        package_allowed=package_allowed,
        wedding_enabled=wedding_enabled,
        role_allowed=role_allowed,
        dependencies_ok=dependencies_ok,
        available=available,
        package=package,
        dependency_names=list(module.dependencies.values_list("name", flat=True)),
        blocked_reason=reason,
    )


def module_available(module_key, user=None, wedding=None, check_role=True):
    state = module_state(module_key, user=user, wedding=wedding, check_role=check_role)
    return bool(state and state.available)


def enabled_module_keys(user, wedding):
    if not wedding:
        return set()
    cache_key = f"_everafter_module_keys_{getattr(user, 'pk', 'public')}"
    cached = getattr(wedding, cache_key, None)
    if cached is not None:
        return cached

    keys = set()
    modules = FeatureModule.objects.filter(system_enabled=True).prefetch_related("dependencies")
    for module in modules:
        state = module_state(module.key, user=user, wedding=wedding, check_role=True)
        if state and state.available:
            keys.add(module.key)
    setattr(wedding, cache_key, keys)
    return keys


def can_manage_wedding_modules(user, wedding):
    if not user or not getattr(user, "is_authenticated", False) or not wedding:
        return False
    return bool(getattr(user, "is_superuser", False) or wedding.owner_id == user.id)


def active_dependent_modules(module, wedding):
    result = []
    for dependent in module.dependent_modules.filter(system_enabled=True):
        state = module_state(dependent.key, user=None, wedding=wedding, check_role=False)
        if state and state.wedding_enabled and state.package_allowed and state.system_allowed:
            result.append(dependent)
    return result
