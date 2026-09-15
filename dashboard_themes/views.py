from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render

from modules.models import FeatureModule

from .forms import DashboardThemeForm, ThemePreferenceForm
from .models import DashboardTheme, UserDashboardPreference
from .services import default_theme, system_theme_admin, theme_for_user


def _feature_enabled():
    module = FeatureModule.objects.filter(key="dashboard_themes").only("system_enabled").first()
    return bool(module is None or module.system_enabled)


def _require_feature():
    if not _feature_enabled():
        raise Http404("Dashboard themes are disabled")


def _require_theme_admin(user):
    if not system_theme_admin(user):
        raise Http404("Page not found")


@login_required
def gallery(request):
    _require_feature()
    current_theme, current_density = theme_for_user(request.user)

    if request.method == "POST":
        form = ThemePreferenceForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Choose a valid theme and layout density.")
            return redirect("dashboard_themes:gallery")
        theme = get_object_or_404(
            DashboardTheme,
            pk=form.cleaned_data["theme_id"],
            is_active=True,
        )
        preference, _ = UserDashboardPreference.objects.get_or_create(user=request.user)
        preference.theme = theme
        preference.density = form.cleaned_data["density"]
        preference.save(update_fields=["theme", "density", "updated_at"])
        messages.success(request, f"Dashboard appearance changed to {theme.name}.")
        return redirect("dashboard_themes:gallery")

    themes = list(DashboardTheme.objects.filter(is_active=True).order_by("sort_order", "name"))
    if current_theme and not current_theme.is_active and all(item.pk != current_theme.pk for item in themes):
        themes.insert(0, current_theme)

    return render(
        request,
        "dashboard_themes/gallery.html",
        {
            "themes": themes,
            "current_theme": current_theme,
            "current_density": current_density,
            "density_choices": UserDashboardPreference.Density.choices,
        },
    )


@login_required
def manage(request):
    _require_feature()
    _require_theme_admin(request.user)
    return render(
        request,
        "dashboard_themes/manage.html",
        {
            "themes": DashboardTheme.objects.all().order_by("sort_order", "name"),
            "default_theme": default_theme(),
        },
    )


@login_required
def theme_create(request):
    _require_feature()
    _require_theme_admin(request.user)
    form = DashboardThemeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        theme = form.save()
        messages.success(request, f"Theme {theme.name} created.")
        return redirect("dashboard_themes:manage")
    return render(request, "dashboard_themes/form.html", {"form": form, "editing": False})


@login_required
def theme_edit(request, pk):
    _require_feature()
    _require_theme_admin(request.user)
    theme = get_object_or_404(DashboardTheme, pk=pk)
    form = DashboardThemeForm(request.POST or None, instance=theme)
    if request.method == "POST" and form.is_valid():
        theme = form.save()
        messages.success(request, f"Theme {theme.name} updated.")
        return redirect("dashboard_themes:manage")
    return render(request, "dashboard_themes/form.html", {"form": form, "editing": True, "theme": theme})


@login_required
def theme_action(request, pk):
    _require_feature()
    _require_theme_admin(request.user)
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    theme = get_object_or_404(DashboardTheme, pk=pk)
    action = (request.POST.get("action") or "").strip().lower()

    if action == "activate":
        theme.is_active = True
        theme.save(update_fields=["is_active", "updated_at"])
        messages.success(request, f"{theme.name} is available for selection.")
    elif action == "deactivate":
        if theme.is_default:
            messages.error(request, "The default theme cannot be disabled. Set another default first.")
        else:
            theme.is_active = False
            theme.save(update_fields=["is_active", "updated_at"])
            messages.success(request, f"{theme.name} is hidden from new selections. Existing users keep it until they switch.")
    elif action == "default":
        theme.is_active = True
        theme.is_default = True
        theme.save()
        messages.success(request, f"{theme.name} is now the default dashboard theme.")
    else:
        return HttpResponseBadRequest("Unknown action")
    return redirect("dashboard_themes:manage")
