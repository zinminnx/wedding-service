from .models import DashboardTheme, UserDashboardPreference


def system_theme_admin(user):
    if not getattr(user, "is_authenticated", False):
        return False
    role = getattr(user, "role", "")
    return bool(user.is_superuser or role in {"SUPER_ADMIN", "ADMIN"})


def default_theme():
    return (
        DashboardTheme.objects.filter(is_active=True, is_default=True).first()
        or DashboardTheme.objects.filter(is_active=True).order_by("sort_order", "name").first()
        or DashboardTheme.objects.order_by("sort_order", "name").first()
    )


def theme_for_user(user):
    if not getattr(user, "is_authenticated", False):
        return None, UserDashboardPreference.Density.COMFORTABLE
    preference = (
        UserDashboardPreference.objects.select_related("theme")
        .filter(user=user)
        .first()
    )
    if preference and preference.theme_id:
        # Existing users keep a disabled theme until they actively switch.
        return preference.theme, preference.density
    return default_theme(), (
        preference.density if preference else UserDashboardPreference.Density.COMFORTABLE
    )
