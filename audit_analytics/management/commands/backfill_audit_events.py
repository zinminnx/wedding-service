import hashlib

from django.apps import apps
from django.core.management.base import BaseCommand

from audit_analytics.models import AuditEvent
from audit_analytics.services import record_event
from weddings.models import Wedding


def fingerprint(label, pk):
    return hashlib.sha256(f"{label}:{pk}".encode("utf-8")).hexdigest()


class Command(BaseCommand):
    help = "Backfill central audit records from existing EverVow event ledgers without duplicating rows."

    def handle(self, *args, **options):
        created_before = AuditEvent.objects.count()
        self._financial()
        self._archive()
        self._checkins()
        self._return_gifts()
        created = AuditEvent.objects.count() - created_before
        self.stdout.write(self.style.SUCCESS(f"Audit backfill complete: {created} new central event(s)."))

    def _financial(self):
        if not apps.is_installed("financial_docs"):
            return
        try:
            Model = apps.get_model("financial_docs", "FinancialAuditEvent")
        except LookupError:
            return
        for item in Model.objects.select_related("wedding", "actor").iterator():
            record_event(
                wedding=item.wedding,
                actor=item.actor,
                category=AuditEvent.Category.FINANCE,
                action=item.action,
                entity_type=item.entity_type,
                entity_id=item.entity_id,
                message=item.message,
                source=AuditEvent.Source.BACKFILL,
                source_fingerprint=fingerprint("financial_docs.FinancialAuditEvent", item.pk),
                created_at=item.created_at,
            )

    def _archive(self):
        if not apps.is_installed("archive_restore"):
            return
        try:
            Model = apps.get_model("archive_restore", "ArchiveEvent")
        except LookupError:
            return
        wedding_cache = {item.public_id: item for item in Wedding.objects.all()}
        for item in Model.objects.select_related("actor", "snapshot").iterator():
            wedding = wedding_cache.get(item.wedding_public_id)
            if not wedding:
                continue
            record_event(
                wedding=wedding,
                actor=item.actor,
                category=AuditEvent.Category.ARCHIVE,
                action=f"archive.{item.action.lower()}",
                entity_type="archive_snapshot",
                entity_id=getattr(item.snapshot, "public_id", ""),
                message=item.message,
                source=AuditEvent.Source.BACKFILL,
                source_fingerprint=fingerprint("archive_restore.ArchiveEvent", item.pk),
                created_at=item.created_at,
            )

    def _checkins(self):
        if not apps.is_installed("checkins"):
            return
        try:
            Model = apps.get_model("checkins", "CheckInEvent")
        except LookupError:
            return
        for item in Model.objects.select_related("wedding", "created_by", "guest").iterator():
            guest_id = getattr(item.guest, "public_id", "") if item.guest_id else ""
            record_event(
                wedding=item.wedding,
                actor=item.created_by,
                category=AuditEvent.Category.CHECKIN,
                action=f"checkin.{item.action.lower()}",
                entity_type="guest",
                entity_id=guest_id,
                message=f"Check-in {item.action.lower()} {item.quantity_delta:+d}; resulting count {item.resulting_count}.",
                source=AuditEvent.Source.BACKFILL,
                source_fingerprint=fingerprint("checkins.CheckInEvent", item.pk),
                created_at=item.created_at,
            )

    def _return_gifts(self):
        if not apps.is_installed("gifts"):
            return
        try:
            Model = apps.get_model("gifts", "ReturnGiftMovement")
        except LookupError:
            return
        for item in Model.objects.select_related("wedding", "created_by", "guest").iterator():
            guest_id = getattr(item.guest, "public_id", "") if item.guest_id else ""
            record_event(
                wedding=item.wedding,
                actor=item.created_by,
                category=AuditEvent.Category.GIFTS,
                action=f"return_gift.{item.movement_type.lower()}",
                entity_type="guest" if guest_id else "return_gift_inventory",
                entity_id=guest_id,
                message=f"Return-gift inventory {item.quantity_delta:+d}; quantity after {item.quantity_after}.",
                source=AuditEvent.Source.BACKFILL,
                source_fingerprint=fingerprint("gifts.ReturnGiftMovement", item.pk),
                created_at=item.created_at,
            )
