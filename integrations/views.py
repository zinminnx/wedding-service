from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from staffing.access import PERM_MANAGE_WEDDING, get_user_wedding_role, get_wedding_for_user

from .graph import GraphConfigurationError, OneDriveGraphClient, get_graph_config
from .models import StoredObject, WeddingStorageSettings
from .storage import local_storage_summary, wedding_remote_root


def _main_admin(user, wedding):
    return bool(getattr(user, "is_superuser", False) or get_user_wedding_role(user, wedding) == "SUPER_ADMIN")


@login_required
def storage_dashboard(request):
    wedding = get_wedding_for_user(request.user, PERM_MANAGE_WEDDING)
    if not wedding:
        messages.error(request, "Your role does not allow access to storage settings for this wedding.")
        return redirect("weddings:dashboard")

    settings_obj, _ = WeddingStorageSettings.objects.get_or_create(wedding=wedding)
    config = get_graph_config(drive_id_override=settings_obj.onedrive_drive_id)
    can_change_provider = _main_admin(request.user, wedding)

    if request.method == "POST":
        action = request.POST.get("action", "").strip()
        if action == "test_onedrive":
            if not config.complete:
                settings_obj.health_status = WeddingStorageSettings.Health.ERROR
                settings_obj.health_message = "Missing server configuration: " + ", ".join(config.missing)
                settings_obj.last_health_check_at = timezone.now()
                settings_obj.save(update_fields=["health_status", "health_message", "last_health_check_at", "updated_at"])
                messages.error(request, settings_obj.health_message)
            else:
                try:
                    drive = OneDriveGraphClient(config).health_check()
                    label = drive.get("name") or drive.get("driveType") or "Microsoft drive"
                    settings_obj.health_status = WeddingStorageSettings.Health.OK
                    settings_obj.health_message = f"Connected to {label}."
                    messages.success(request, "OneDrive connection test succeeded.")
                except (GraphConfigurationError, Exception) as exc:
                    settings_obj.health_status = WeddingStorageSettings.Health.ERROR
                    settings_obj.health_message = str(exc)[:255]
                    messages.error(request, "OneDrive connection test failed. Check Microsoft Graph configuration.")
                settings_obj.last_health_check_at = timezone.now()
                settings_obj.save(update_fields=["health_status", "health_message", "last_health_check_at", "updated_at"])
            return redirect("integrations:storage_dashboard")

        if action in {"use_local", "use_onedrive"}:
            if not can_change_provider:
                messages.error(request, "Only Main Admin can change the storage provider.")
                return redirect("integrations:storage_dashboard")
            if action == "use_onedrive":
                if not config.complete:
                    messages.error(request, "Configure Microsoft Graph server credentials before enabling OneDrive.")
                    return redirect("integrations:storage_dashboard")
                if settings_obj.health_status != WeddingStorageSettings.Health.OK:
                    messages.error(request, "Run a successful OneDrive connection test before enabling it.")
                    return redirect("integrations:storage_dashboard")
                settings_obj.provider = WeddingStorageSettings.Provider.ONEDRIVE
            else:
                settings_obj.provider = WeddingStorageSettings.Provider.LOCAL
            settings_obj.save(update_fields=["provider", "updated_at"])
            messages.success(request, f"Storage provider set to {settings_obj.get_provider_display()} for future integrated writes.")
            return redirect("integrations:storage_dashboard")

    object_qs = StoredObject.objects.filter(wedding=wedding)
    counts = {
        "total": object_qs.count(),
        "available": object_qs.filter(status=StoredObject.Status.AVAILABLE).count(),
        "failed": object_qs.filter(status=StoredObject.Status.FAILED).count(),
        "onedrive": object_qs.filter(backend=StoredObject.Backend.ONEDRIVE).count(),
        "local": object_qs.filter(backend=StoredObject.Backend.LOCAL).count(),
    }

    return render(
        request,
        "integrations/storage_dashboard.html",
        {
            "wedding": wedding,
            "settings_obj": settings_obj,
            "graph_configured": config.complete,
            "graph_missing": config.missing,
            "remote_root": wedding_remote_root(wedding, settings_obj),
            "local_summary": local_storage_summary(),
            "counts": counts,
            "recent_objects": object_qs[:10],
            "can_change_provider": can_change_provider,
        },
    )
