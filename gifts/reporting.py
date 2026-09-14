import csv
from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date

from payment_providers.models import PaymentProvider

from .models import GuestGiftDeclaration


REPORT_ROW_LIMIT = 250


def _clean_choice(value, allowed):
    value = (value or "").strip()
    return value if value in allowed else ""


def _base_queryset(request, wedding):
    qs = (
        GuestGiftDeclaration.objects.filter(wedding=wedding)
        .select_related(
            "guest",
            "payment_method_record",
            "payment_method_record__provider_link__provider",
            "payment_reviewed_by",
        )
        .order_by("-declared_at", "-id")
    )

    date_from_raw = (request.GET.get("date_from") or "").strip()
    date_to_raw = (request.GET.get("date_to") or "").strip()
    gift_choice = _clean_choice(
        request.GET.get("gift_choice"),
        GuestGiftDeclaration.GiftChoice.values,
    )
    status = _clean_choice(
        request.GET.get("status"),
        GuestGiftDeclaration.PaymentStatus.values,
    )
    provider_type = _clean_choice(
        request.GET.get("provider_type"),
        PaymentProvider.ProviderType.values,
    )
    provider_id = (request.GET.get("provider") or "").strip()
    q = (request.GET.get("q") or "").strip()

    date_from = parse_date(date_from_raw) if date_from_raw else None
    date_to = parse_date(date_to_raw) if date_to_raw else None

    if date_from:
        qs = qs.filter(declared_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(declared_at__date__lte=date_to)
    if gift_choice:
        qs = qs.filter(gift_choice=gift_choice)
    if status:
        qs = qs.filter(payment_status=status)
    if provider_type:
        qs = qs.filter(
            payment_method_record__provider_link__provider__provider_type=provider_type
        )
    if provider_id.isdigit():
        qs = qs.filter(
            payment_method_record__provider_link__provider_id=int(provider_id)
        )
    if q:
        qs = qs.filter(
            Q(guest__name__icontains=q)
            | Q(guest__phone__icontains=q)
            | Q(guest__public_id__icontains=q)
            | Q(payment_reference__icontains=q)
        )

    filters = {
        "date_from": date_from_raw if date_from else "",
        "date_to": date_to_raw if date_to else "",
        "gift_choice": gift_choice,
        "status": status,
        "provider_type": provider_type,
        "provider": provider_id if provider_id.isdigit() else "",
        "q": q,
    }
    return qs, filters


def _sum_amount(qs):
    return qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")


def _provider_for(item):
    if not item.payment_method_record_id:
        return None
    try:
        return item.payment_method_record.provider_link.provider
    except ObjectDoesNotExist:
        return None


def _percentage(part, whole):
    if not whole:
        return 0
    return round((part / whole) * 100, 1)


def build_payment_report_context(request, wedding):
    qs, filters = _base_queryset(request, wedding)
    total_count = qs.count()
    digital = qs.filter(gift_choice=GuestGiftDeclaration.GiftChoice.DIGITAL)
    physical_count = qs.filter(
        gift_choice=GuestGiftDeclaration.GiftChoice.PHYSICAL
    ).count()
    no_gift_count = qs.filter(gift_choice=GuestGiftDeclaration.GiftChoice.NONE).count()
    digital_count = digital.count()

    pending = digital.filter(
        payment_status=GuestGiftDeclaration.PaymentStatus.GUEST_SENT
    )
    verified = digital.filter(
        payment_status=GuestGiftDeclaration.PaymentStatus.VERIFIED
    )
    rejected = digital.filter(
        payment_status=GuestGiftDeclaration.PaymentStatus.REJECTED
    )

    pending_count = pending.count()
    verified_count = verified.count()
    rejected_count = rejected.count()

    provider_summary = list(
        digital.values(
            "payment_method_record__provider_link__provider_id",
            "payment_method_record__provider_link__provider__name",
            "payment_method_record__provider_link__provider__short_name",
            "payment_method_record__provider_link__provider__provider_type",
        )
        .annotate(
            declarations=Count("id"),
            declared_amount=Sum("amount"),
            pending=Count(
                "id",
                filter=Q(
                    payment_status=GuestGiftDeclaration.PaymentStatus.GUEST_SENT
                ),
            ),
            verified=Count(
                "id",
                filter=Q(
                    payment_status=GuestGiftDeclaration.PaymentStatus.VERIFIED
                ),
            ),
            rejected=Count(
                "id",
                filter=Q(
                    payment_status=GuestGiftDeclaration.PaymentStatus.REJECTED
                ),
            ),
        )
        .order_by("-declarations", "payment_method_record__provider_link__provider__name")
    )
    for item in provider_summary:
        if not item["payment_method_record__provider_link__provider_id"]:
            item["provider_name"] = "Legacy / unlinked"
            item["provider_type"] = "—"
        else:
            item["provider_name"] = (
                item["payment_method_record__provider_link__provider__name"]
                or "Unknown provider"
            )
            item["provider_type"] = (
                item["payment_method_record__provider_link__provider__provider_type"]
                or "—"
            )
        item["declared_amount"] = item["declared_amount"] or Decimal("0.00")

    rows = list(qs[:REPORT_ROW_LIMIT])
    for item in rows:
        item.report_provider = _provider_for(item)

    status_bars = [
        {
            "label": "Pending verification",
            "count": pending_count,
            "percent": _percentage(pending_count, digital_count),
        },
        {
            "label": "Verified",
            "count": verified_count,
            "percent": _percentage(verified_count, digital_count),
        },
        {
            "label": "Rejected",
            "count": rejected_count,
            "percent": _percentage(rejected_count, digital_count),
        },
    ]

    return {
        "wedding": wedding,
        "rows": rows,
        "row_count": total_count,
        "row_limit": REPORT_ROW_LIMIT,
        "filters": filters,
        "providers": PaymentProvider.objects.order_by(
            "provider_type", "sort_order", "name"
        ),
        "gift_choice_choices": GuestGiftDeclaration.GiftChoice.choices,
        "status_choices": [
            choice
            for choice in GuestGiftDeclaration.PaymentStatus.choices
            if choice[0] != GuestGiftDeclaration.PaymentStatus.NOT_REQUIRED
        ],
        "provider_type_choices": PaymentProvider.ProviderType.choices,
        "provider_summary": provider_summary,
        "status_bars": status_bars,
        "stats": {
            "total": total_count,
            "digital": digital_count,
            "physical": physical_count,
            "none": no_gift_count,
            "declared_amount": _sum_amount(digital),
            "pending": pending_count,
            "pending_amount": _sum_amount(pending),
            "verified": verified_count,
            "verified_amount": _sum_amount(verified),
            "rejected": rejected_count,
            "rejected_amount": _sum_amount(rejected),
        },
    }


def _safe_csv_value(value):
    if value is None:
        return ""
    text = str(value)
    if text.startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


def payment_report_csv_response(request, wedding):
    qs, _filters = _base_queryset(request, wedding)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="{wedding.slug}-payment-report.csv"'
    )
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(
        [
            "Declared At",
            "Guest ID",
            "Guest Name",
            "Phone",
            "Gift Choice",
            "Provider Type",
            "Provider",
            "Amount",
            "Payment Status",
            "Reference",
            "Reviewed At",
            "Reviewed By",
        ]
    )

    for item in qs.iterator(chunk_size=500):
        provider = _provider_for(item)
        declared_at = timezone.localtime(item.declared_at).isoformat(
            timespec="seconds"
        )
        reviewed_at = (
            timezone.localtime(item.payment_reviewed_at).isoformat(timespec="seconds")
            if item.payment_reviewed_at
            else ""
        )
        reviewer = ""
        if item.payment_reviewed_by_id:
            reviewer = (
                item.payment_reviewed_by.get_full_name()
                or item.payment_reviewed_by.username
            )

        writer.writerow(
            [
                _safe_csv_value(declared_at),
                _safe_csv_value(item.guest.public_id),
                _safe_csv_value(item.guest.name),
                _safe_csv_value(item.guest.phone),
                _safe_csv_value(item.get_gift_choice_display()),
                _safe_csv_value(provider.get_provider_type_display() if provider else ""),
                _safe_csv_value(provider.name if provider else item.payment_method_label),
                _safe_csv_value(item.amount if item.amount is not None else ""),
                _safe_csv_value(item.get_payment_status_display()),
                _safe_csv_value(item.payment_reference),
                _safe_csv_value(reviewed_at),
                _safe_csv_value(reviewer),
            ]
        )

    return response
