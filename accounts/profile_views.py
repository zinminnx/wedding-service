from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import redirect, render

from staffing.access import access_summary, get_wedding_for_user

from .profile_forms import ProfileForm


def _profile_context(request):
    wedding = get_wedding_for_user(request.user)
    access = access_summary(request.user, wedding) if wedding else {
        "role": None,
        "role_label": "No active wedding",
        "can_create_wedding": False,
    }
    return {
        "wedding": wedding,
        "access": access,
        "global_role_label": request.user.get_role_display(),
        "can_manage_roles": bool(request.user.is_superuser or (wedding and wedding.owner_id == request.user.id)),
    }


@login_required
def profile(request):
    context = _profile_context(request)
    return render(request, "accounts/profile.html", context)


@login_required
def profile_edit(request):
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated.")
            return redirect("accounts:profile")
    else:
        form = ProfileForm(instance=request.user)

    context = _profile_context(request)
    context["form"] = form
    return render(request, "accounts/profile_edit.html", context)


@login_required
def password_change(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Your password has been changed successfully.")
            return redirect("accounts:profile")
    else:
        form = PasswordChangeForm(request.user)

    for field in form.fields.values():
        existing = field.widget.attrs.get("class", "")
        field.widget.attrs["class"] = (existing + " ea-profile-input").strip()

    context = _profile_context(request)
    context["form"] = form
    return render(request, "accounts/password_change.html", context)
