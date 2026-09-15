from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from staffing.access import access_summary, get_wedding_for_user, is_wedding_owner
from staffing.models import WeddingStaffMembership


User = get_user_model()


def _can_manage_wedding_roles(user, wedding):
    return bool(wedding and is_wedding_owner(user, wedding))


def _role_context(request):
    wedding = get_wedding_for_user(request.user)
    can_manage_global = bool(request.user.is_superuser)
    can_manage_wedding = _can_manage_wedding_roles(request.user, wedding)
    if not (can_manage_global or can_manage_wedding):
        raise PermissionDenied("You do not have permission to manage roles.")

    access = access_summary(request.user, wedding) if wedding else {
        "role": None,
        "role_label": "No active wedding",
        "can_create_wedding": False,
    }

    global_users = []
    if can_manage_global:
        global_users = list(User.objects.all().order_by("username"))

    memberships = []
    if can_manage_wedding:
        memberships = list(
            WeddingStaffMembership.objects.filter(wedding=wedding)
            .select_related("user", "created_by")
            .order_by("role", "user__username")
        )

    return {
        "wedding": wedding,
        "access": access,
        "can_manage_global": can_manage_global,
        "can_manage_wedding": can_manage_wedding,
        "global_users": global_users,
        "global_role_choices": [
            (value, label)
            for value, label in User.Role.choices
            if value != User.Role.SUPER_ADMIN
        ],
        "wedding_memberships": memberships,
        "wedding_role_choices": list(WeddingStaffMembership.Role.choices),
        "wedding_status_choices": list(WeddingStaffMembership.Status.choices),
    }


@login_required
def role_management(request):
    return render(request, "accounts/roles.html", _role_context(request))


@login_required
def global_role_update(request, user_id):
    if request.method != "POST":
        return redirect("accounts:roles")
    if not request.user.is_superuser:
        raise PermissionDenied("Only a Super Admin can change global roles.")

    target = get_object_or_404(User, pk=user_id)
    if target.is_superuser:
        messages.error(request, "Super Admin accounts are locked to the Super Admin global role.")
        return redirect("accounts:roles")

    allowed = {value for value, _label in User.Role.choices if value != User.Role.SUPER_ADMIN}
    role = (request.POST.get("role") or "").strip()
    if role not in allowed:
        messages.error(request, "Invalid global role selection.")
        return redirect("accounts:roles")

    if target.role != role:
        target.role = role
        target.save(update_fields=["role"])
        messages.success(request, f"Global role updated for {target.username}.")
    else:
        messages.info(request, "No global role change was needed.")
    return redirect("accounts:roles")


@login_required
def wedding_role_update(request, membership_id):
    if request.method != "POST":
        return redirect("accounts:roles")

    wedding = get_wedding_for_user(request.user)
    if not _can_manage_wedding_roles(request.user, wedding):
        raise PermissionDenied("Only the wedding owner or a Super Admin can change wedding roles.")

    membership = get_object_or_404(
        WeddingStaffMembership.objects.select_related("user"),
        pk=membership_id,
        wedding=wedding,
    )

    allowed_roles = {value for value, _label in WeddingStaffMembership.Role.choices}
    allowed_statuses = {value for value, _label in WeddingStaffMembership.Status.choices}
    role = (request.POST.get("role") or "").strip()
    status = (request.POST.get("status") or "").strip()

    if role not in allowed_roles:
        messages.error(request, "Invalid wedding role selection.")
        return redirect("accounts:roles")
    if status not in allowed_statuses:
        messages.error(request, "Invalid wedding access status.")
        return redirect("accounts:roles")
    if membership.user_id == request.user.id and status == WeddingStaffMembership.Status.INACTIVE:
        messages.error(request, "You cannot deactivate your own wedding membership here.")
        return redirect("accounts:roles")

    changed = membership.role != role or membership.status != status
    if changed:
        with transaction.atomic():
            membership.role = role
            membership.status = status
            membership.save(update_fields=["role", "status", "updated_at"])
        messages.success(request, f"Wedding access updated for {membership.user.username}.")
    else:
        messages.info(request, "No wedding role change was needed.")
    return redirect("accounts:roles")
