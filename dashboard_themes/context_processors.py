from .services import system_theme_admin, theme_for_user


def dashboard_theme(request):
    user = getattr(request, "user", None)
    theme, density = theme_for_user(user)
    return {
        "dashboard_visual_theme": theme,
        "dashboard_layout_density": density,
        "dashboard_theme_admin": system_theme_admin(user),
    }
