from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from .access import PERM_MANAGE_STAFF, get_wedding_for_user
from .forms import StaffCreateForm, StaffMembershipForm
from .models import WeddingStaffMembership


User = get_user_model()


def _staff_admin_wedding(request):
    wedding = get_wedding_for_user(request.user, PERM_MANAGE_STAFF)
    if wedding is None:
        messages.error(request, "You do not have permission to manage staff for this wedding.")
    return wedding


@login_required
def staff_list(request):
    wedding = _staff_admin_wedding(request)
    if wedding is None:
        return redirect("weddings:dashboard")

    memberships = (
        WeddingStaffMembership.objects.filter(wedding=wedding)
        .select_related("user", "created_by")
        .order_by("role", "user__username")
    )
    counts = {
        "active": memberships.filter(status=WeddingStaffMembership.Status.ACTIVE).count(),
        "managers": memberships.filter(
            status=WeddingStaffMembership.Status.ACTIVE,
            role=WeddingStaffMembership.Role.WEDDING_MANAGER,
        ).count(),
        "reception": memberships.filter(
            status=WeddingStaffMembership.Status.ACTIVE,
            role=WeddingStaffMembership.Role.RECEPTION_STAFF,
        ).count(),
    }
    return render(
        request,
        "staffing/list.html",
        {"wedding": wedding, "memberships": memberships, "counts": counts},
    )


@login_required
def staff_add(request):
    wedding = _staff_admin_wedding(request)
    if wedding is None:
        return redirect("weddings:dashboard")

    if request.method == "POST":
        form = StaffCreateForm(request.POST)
        if form.is_valid():
            existing_user = form.existing_user
            if existing_user and existing_user.pk == wedding.owner_id:
                form.add_error(None, "The wedding owner already has full access and cannot be added as staff.")
            elif existing_user and WeddingStaffMembership.objects.filter(wedding=wedding, user=existing_user).exists():
                form.add_error(None, "This account is already assigned to this wedding. Edit the existing staff record instead.")
            else:
                with transaction.atomic():
                    if existing_user:
                        user = existing_user
                        created_account = False
                    else:
                        user = User.objects.create_user(
                            username=form.cleaned_data["username"].strip(),
                            email=(form.cleaned_data.get("email") or "").strip(),
                            password=form.cleaned_data["password"],
                            first_name=(form.cleaned_data.get("first_name") or "").strip(),
                            last_name=(form.cleaned_data.get("last_name") or "").strip(),
                        )
                        phone = (form.cleaned_data.get("phone") or "").strip()
                        if phone and hasattr(user, "phone"):
                            user.phone = phone
                            user.save(update_fields=["phone"])
                        created_account = True

                    WeddingStaffMembership.objects.create(
                        wedding=wedding,
                        user=user,
                        role=form.cleaned_data["role"],
                        status=WeddingStaffMembership.Status.ACTIVE,
                        created_by=request.user,
                    )

                if created_account:
                    messages.success(
                        request,
                        f"Staff account '{user.username}' created and added to {wedding.name}. Share the login credentials securely.",
                    )
                else:
                    messages.success(request, f"Existing account '{user.username}' added to {wedding.name}.")
                return redirect("staffing:list")
    else:
        form = StaffCreateForm()

    return render(request, "staffing/form.html", {"wedding": wedding, "form": form, "editing": False})


@login_required
def staff_edit(request, membership_id):
    wedding = _staff_admin_wedding(request)
    if wedding is None:
        return redirect("weddings:dashboard")

    membership = get_object_or_404(
        WeddingStaffMembership.objects.select_related("user"),
        pk=membership_id,
        wedding=wedding,
    )

    if request.method == "POST":
        form = StaffMembershipForm(request.POST, instance=membership)
        if form.is_valid():
            if membership.user_id == request.user.id and form.cleaned_data["status"] == WeddingStaffMembership.Status.INACTIVE:
                form.add_error("status", "You cannot deactivate your own staff membership.")
            else:
                form.save()
                messages.success(request, f"Access updated for {membership.user.username}.")
                return redirect("staffing:list")
    else:
        form = StaffMembershipForm(instance=membership)

    return render(
        request,
        "staffing/form.html",
        {"wedding": wedding, "form": form, "editing": True, "membership": membership},
    )


@login_required
def staff_disable(request, membership_id):
    if request.method != "POST":
        return redirect("staffing:list")
    wedding = _staff_admin_wedding(request)
    if wedding is None:
        return redirect("weddings:dashboard")

    membership = get_object_or_404(WeddingStaffMembership, pk=membership_id, wedding=wedding)
    if membership.user_id == request.user.id:
        messages.error(request, "You cannot deactivate your own staff membership.")
    else:
        membership.status = WeddingStaffMembership.Status.INACTIVE
        membership.save(update_fields=["status", "updated_at"])
        messages.success(request, "Staff access deactivated. The user account was not deleted.")
    return redirect("staffing:list")
