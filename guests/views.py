from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render

from invitations.models import Invitation

from weddings.models import Wedding

from .forms import GuestForm
from .models import Guest, GuestGroup


def _wedding_for_user(user):
    qs = Wedding.objects.all()
    if not user.is_superuser:
        qs = qs.filter(owner=user)
    return qs.order_by("-created_at").first()


@login_required
def guest_list(request):
    wedding = _wedding_for_user(request.user)
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
            Guest.objects.filter(wedding=wedding).aggregate(
                total=Sum("allowed_party_size")
            )["total"]
            or 0
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


@login_required
def guest_create(request):
    wedding = _wedding_for_user(request.user)
    if not wedding:
        messages.info(request, "Create your wedding before adding guests.")
        return redirect("weddings:overview")

    if request.method == "POST":
        form = GuestForm(request.POST, wedding=wedding)
        if form.is_valid():
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

    return render(
        request,
        "guests/form.html",
        {
            "wedding": wedding,
            "form": form,
            "editing": False,
        },
    )


@login_required
def guest_edit(request, public_id):
    wedding = _wedding_for_user(request.user)
    if not wedding:
        return redirect("weddings:overview")

    guest = get_object_or_404(Guest, wedding=wedding, public_id=public_id)

    if request.method == "POST":
        form = GuestForm(request.POST, instance=guest, wedding=wedding)
        if form.is_valid():
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

    return render(
        request,
        "guests/form.html",
        {
            "wedding": wedding,
            "form": form,
            "editing": True,
            "guest": guest,
        },
    )
