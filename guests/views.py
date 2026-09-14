from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render

from invitations.models import Invitation
from staffing.access import PERM_MANAGE_GUESTS, PERM_VIEW_GUESTS, get_wedding_for_user

from .forms import GuestForm
from .models import Guest, GuestGroup


@login_required
def guest_list(request):
    wedding = get_wedding_for_user(request.user, PERM_VIEW_GUESTS)
    guests = Guest.objects.none()
    groups = GuestGroup.objects.none()
    allocated_seats = 0

    if wedding:
        guests = Guest.objects.filter(wedding=wedding).select_related("group")
        groups = GuestGroup.objects.filter(wedding=wedding).order_by("name")

        q = request.GET.get("q", "").strip()
        group_id = request.GET.get("group", "").strip()
        status = request.GET.get("status", "").strip()

        if q:
            guests = guests.filter(
                Q(name__icontains=q)
                | Q(phone__icontains=q)
                | Q(email__icontains=q)
                | Q(public_id__icontains=q)
            )
        if group_id:
            guests = guests.filter(group_id=group_id)
        if status:
            guests = guests.filter(status=status)

        allocated_seats = (
            Guest.objects.filter(wedding=wedding).aggregate(total=Sum("allowed_party_size"))["total"] or 0
        )

    return render(
        request,
        "guests/list.html",
        {
            "wedding": wedding,
            "guests": guests,
            "groups": groups,
            "allocated_seats": allocated_seats,
        },
    )


def _managed_wedding_or_redirect(request):
    wedding = get_wedding_for_user(request.user, PERM_MANAGE_GUESTS)
    if wedding is None:
        messages.error(request, "Your role does not allow changing the guest list.")
    return wedding


def _duplicate_confirmation_required(request, form):
    return bool(form.duplicate_warnings) and request.POST.get("confirm_duplicate") != "1"


def _guest_form_context(wedding, form, editing, guest=None):
    return {
        "wedding": wedding,
        "form": form,
        "editing": editing,
        "guest": guest,
        "duplicate_warnings": form.duplicate_warnings,
        "duplicate_matches": form.duplicate_matches,
        "duplicate_confirmation_required": bool(form.duplicate_warnings),
    }


@login_required
def guest_create(request):
    wedding = _managed_wedding_or_redirect(request)
    if not wedding:
        return redirect("weddings:dashboard")

    if request.method == "POST":
        form = GuestForm(request.POST, wedding=wedding)
        if form.is_valid():
            if _duplicate_confirmation_required(request, form):
                messages.warning(request, "Possible duplicate found. Review the matches and confirm before saving.")
                return render(request, "guests/form.html", _guest_form_context(wedding, form, False))

            guest = form.save()
            Invitation.objects.get_or_create(
                wedding=wedding,
                guest=guest,
                defaults={"status": Invitation.Status.READY},
            )
            messages.success(request, f"{guest.name} was added and an invitation was prepared.")
            if request.POST.get("action") == "save_add_another":
                return redirect("guests:add")
            return redirect("guests:list")
    else:
        form = GuestForm(wedding=wedding)

    return render(request, "guests/form.html", _guest_form_context(wedding, form, False))


@login_required
def guest_edit(request, public_id):
    wedding = _managed_wedding_or_redirect(request)
    if not wedding:
        return redirect("weddings:dashboard")

    guest = get_object_or_404(Guest, wedding=wedding, public_id=public_id)

    if request.method == "POST":
        form = GuestForm(request.POST, instance=guest, wedding=wedding)
        if form.is_valid():
            if _duplicate_confirmation_required(request, form):
                messages.warning(request, "Possible duplicate found. Review the matches and confirm before saving.")
                return render(request, "guests/form.html", _guest_form_context(wedding, form, True, guest))

            guest = form.save()
            Invitation.objects.get_or_create(
                wedding=wedding,
                guest=guest,
                defaults={"status": Invitation.Status.READY},
            )
            messages.success(request, f"{guest.name} was updated.")
            return redirect("guests:list")
    else:
        form = GuestForm(instance=guest, wedding=wedding)

    return render(request, "guests/form.html", _guest_form_context(wedding, form, True, guest))
