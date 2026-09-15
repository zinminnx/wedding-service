import csv
from collections import defaultdict
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.utils import timezone

from staffing.access import PERM_MANAGE_WEDDING, get_wedding_for_user, is_wedding_owner

from .models import AuditEvent


RANGE_OPTIONS = {7, 30, 90}


def _range_days(request):
    try:
        value = int(request.GET.get("days", "30"))
    except (TypeError, ValueError):
        value = 30
    return value if value in RANGE_OPTIONS else 30


def _analytics_wedding(request):
    wedding = get_wedding_for_user(request.user, PERM_MANAGE_WEDDING)
    if not wedding:
        raise Http404("Wedding not found")
    return wedding


def _owner_wedding(request):
    wedding = get_wedding_for_user(request.user)
    if not wedding or not is_wedding_owner(request.user, wedding):
        raise Http404("Wedding not found")
    return wedding


def _percent(numerator, denominator):
    if not denominator:
        return 0
    return round((float(numerator or 0) / float(denominator)) * 100, 1)


def _count_by_day(queryset, field, start_date):
    rows = (
        queryset.filter(**{f"{field}__date__gte": start_date})
        .annotate(day=TruncDate(field))
        .values("day")
        .annotate(total=Count("id"))
        .order_by("day")
    )
    return {row["day"]: int(row["total"] or 0) for row in rows}


def _sum_by_day(queryset, field, value_field, start_date):
    rows = (
        queryset.filter(**{f"{field}__date__gte": start_date})
        .annotate(day=TruncDate(field))
        .values("day")
        .annotate(total=Sum(value_field))
        .order_by("day")
    )
    return {row["day"]: int(row["total"] or 0) for row in rows}


def _metrics_for(wedding, days):
    from checkins.models import CheckIn, CheckInEvent
    from gifts.models import GuestGiftDeclaration
    from guests.models import Guest
    from invitations.models import Invitation
    from photos.models import WeddingPhoto
    from rsvp.models import RSVP

    guests = Guest.objects.filter(wedding=wedding)
    invitations = Invitation.objects.filter(wedding=wedding)
    rsvps = RSVP.objects.filter(wedding=wedding)
    checkins = CheckIn.objects.filter(wedding=wedding)
    gifts = GuestGiftDeclaration.objects.filter(wedding=wedding)
    photos = WeddingPhoto.objects.filter(wedding=wedding)

    guest_total = guests.count()
    invitation_total = invitations.count()
    invitation_sent = invitations.filter(status__in=[Invitation.Status.SENT, Invitation.Status.OPENED]).count()
    invitation_opened = invitations.filter(first_opened_at__isnull=False).count()
    rsvp_total = rsvps.count()
    rsvp_attending = rsvps.filter(response=RSVP.Response.ATTENDING).count()
    adult_sum = rsvps.filter(response=RSVP.Response.ATTENDING).aggregate(v=Sum("attending_adults"))["v"] or 0
    child_sum = rsvps.filter(response=RSVP.Response.ATTENDING).aggregate(v=Sum("attending_children"))["v"] or 0
    expected_people = int(adult_sum) + int(child_sum)
    checked_people = int(checkins.aggregate(v=Sum("checked_in_count"))["v"] or 0)
    checked_parties = checkins.filter(checked_in_count__gt=0).count()

    gift_verified = gifts.filter(payment_status=GuestGiftDeclaration.PaymentStatus.VERIFIED).count()
    gift_pending = gifts.filter(payment_status=GuestGiftDeclaration.PaymentStatus.GUEST_SENT).count()
    gift_physical = gifts.filter(gift_choice=GuestGiftDeclaration.GiftChoice.PHYSICAL).count()

    photo_total = photos.count()
    photo_approved = photos.filter(status=WeddingPhoto.Status.APPROVED).count()
    photo_pending = photos.filter(status=WeddingPhoto.Status.PENDING).count()

    print_total = print_queued = print_printed = 0
    try:
        from printing.models import PrintJob

        print_qs = PrintJob.objects.filter(wedding=wedding)
        print_total = print_qs.count()
        print_queued = print_qs.filter(status__in=[PrintJob.Status.QUEUED, PrintJob.Status.CLAIMED, PrintJob.Status.PRINTING]).count()
        print_printed = print_qs.filter(status=PrintJob.Status.PRINTED).count()
    except Exception:
        pass

    planner_open = 0
    try:
        from planner.models import PlannerTask

        planner_open = PlannerTask.objects.filter(wedding=wedding).exclude(status__in=["DONE", "CANCELLED"]).count()
    except Exception:
        pass

    today = timezone.localdate()
    visible_days = min(days, 30)
    start_date = today - timedelta(days=visible_days - 1)
    rsvp_daily = _count_by_day(rsvps, "responded_at", start_date)
    photo_daily = _count_by_day(photos, "created_at", start_date)
    checkin_daily = _sum_by_day(
        CheckInEvent.objects.filter(wedding=wedding, action__in=[CheckInEvent.Action.ARRIVAL, CheckInEvent.Action.OVERRIDE], quantity_delta__gt=0),
        "created_at",
        "quantity_delta",
        start_date,
    )
    audit_daily = _count_by_day(AuditEvent.objects.filter(wedding=wedding), "created_at", start_date)

    activity = []
    max_value = 1
    for offset in range(visible_days):
        day = start_date + timedelta(days=offset)
        row = {
            "day": day,
            "rsvp": rsvp_daily.get(day, 0),
            "photos": photo_daily.get(day, 0),
            "checkins": checkin_daily.get(day, 0),
            "actions": audit_daily.get(day, 0),
        }
        max_value = max(max_value, row["rsvp"], row["photos"], row["checkins"], row["actions"])
        activity.append(row)
    for row in activity:
        row["rsvp_width"] = round(row["rsvp"] * 100 / max_value, 1)
        row["photos_width"] = round(row["photos"] * 100 / max_value, 1)
        row["checkins_width"] = round(row["checkins"] * 100 / max_value, 1)
        row["actions_width"] = round(row["actions"] * 100 / max_value, 1)

    return {
        "guest_total": guest_total,
        "invitation_total": invitation_total,
        "invitation_sent": invitation_sent,
        "invitation_opened": invitation_opened,
        "invitation_open_rate": _percent(invitation_opened, invitation_sent),
        "rsvp_total": rsvp_total,
        "rsvp_attending": rsvp_attending,
        "rsvp_response_rate": _percent(rsvp_total, invitation_total),
        "expected_people": expected_people,
        "checked_people": checked_people,
        "checked_parties": checked_parties,
        "attendance_rate": _percent(checked_people, expected_people),
        "gift_verified": gift_verified,
        "gift_pending": gift_pending,
        "gift_physical": gift_physical,
        "photo_total": photo_total,
        "photo_approved": photo_approved,
        "photo_pending": photo_pending,
        "print_total": print_total,
        "print_queued": print_queued,
        "print_printed": print_printed,
        "planner_open": planner_open,
        "activity": activity,
    }


def _filtered_audit(request, wedding):
    qs = AuditEvent.objects.filter(wedding=wedding).select_related("actor")
    days_value = request.GET.get("days", "30")
    if days_value != "all":
        try:
            days = int(days_value)
        except (TypeError, ValueError):
            days = 30
        if days not in RANGE_OPTIONS:
            days = 30
        start = timezone.now() - timedelta(days=days)
        qs = qs.filter(created_at__gte=start)

    category = (request.GET.get("category") or "").strip().upper()
    if category in AuditEvent.Category.values:
        qs = qs.filter(category=category)
    else:
        category = ""

    actor = (request.GET.get("actor") or "").strip()
    if actor:
        qs = qs.filter(Q(actor__username__icontains=actor) | Q(actor_label__icontains=actor))

    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(
            Q(public_id__icontains=q)
            | Q(action__icontains=q)
            | Q(message__icontains=q)
            | Q(entity_type__icontains=q)
            | Q(entity_id__icontains=q)
            | Q(actor_label__icontains=q)
        )
    return qs, {"days_filter": days_value, "category_filter": category, "actor_filter": actor, "q": q}


@login_required
def analytics_dashboard(request):
    wedding = _analytics_wedding(request)
    days = _range_days(request)
    metrics = _metrics_for(wedding, days)
    recent_events = AuditEvent.objects.filter(wedding=wedding).select_related("actor")[:12]
    return render(
        request,
        "audit_analytics/dashboard.html",
        {
            "wedding": wedding,
            "days": days,
            "metrics": metrics,
            "recent_events": recent_events,
            "can_view_audit": is_wedding_owner(request.user, wedding),
        },
    )


@login_required
def analytics_export(request):
    wedding = _analytics_wedding(request)
    days = _range_days(request)
    metrics = _metrics_for(wedding, days)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{wedding.slug}-analytics.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(["Wedding", wedding.name])
    writer.writerow(["Range days", days])
    writer.writerow([])
    writer.writerow(["Metric", "Value"])
    labels = [
        ("Guests", "guest_total"),
        ("Invitations sent", "invitation_sent"),
        ("Invitations opened", "invitation_opened"),
        ("Invitation open rate %", "invitation_open_rate"),
        ("RSVP responses", "rsvp_total"),
        ("RSVP response rate %", "rsvp_response_rate"),
        ("Expected attendees", "expected_people"),
        ("Checked-in attendees", "checked_people"),
        ("Attendance rate %", "attendance_rate"),
        ("Verified digital gifts", "gift_verified"),
        ("Pending gift reviews", "gift_pending"),
        ("Approved photos", "photo_approved"),
        ("Pending photos", "photo_pending"),
        ("Printed jobs", "print_printed"),
        ("Active print jobs", "print_queued"),
        ("Open planner tasks", "planner_open"),
    ]
    for label, key in labels:
        writer.writerow([label, metrics[key]])
    return response


@login_required
def audit_trail(request):
    wedding = _owner_wedding(request)
    qs, filters = _filtered_audit(request, wedding)
    category_counts = dict(
        AuditEvent.objects.filter(wedding=wedding)
        .values_list("category")
        .annotate(total=Count("id"))
    )
    context = {
        "wedding": wedding,
        "events": qs[:250],
        "category_choices": AuditEvent.Category.choices,
        "category_counts": category_counts,
        **filters,
    }
    return render(request, "audit_analytics/audit.html", context)


@login_required
def audit_export(request):
    wedding = _owner_wedding(request)
    qs, _ = _filtered_audit(request, wedding)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{wedding.slug}-audit.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(["Time", "Audit ID", "Category", "Actor", "Role", "Action", "Entity", "Message", "Source"])
    for event in qs[:10000]:
        entity = ":".join(part for part in [event.entity_type, event.entity_id] if part)
        writer.writerow([
            timezone.localtime(event.created_at).isoformat(),
            event.public_id,
            event.category,
            event.actor_label,
            event.actor_role,
            event.action,
            entity,
            event.message,
            event.source,
        ])
    return response
