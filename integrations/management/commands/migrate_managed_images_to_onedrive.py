from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from integrations.image_media import migrate_local_image_record_to_onedrive
from integrations.models import StoredObject


class Command(BaseCommand):
    help = (
        "Move managed image originals (guest photos + invitation covers) from Local Media "
        "to OneDrive with read-back SHA-256 verification. Dry-run by default."
    )

    def add_arguments(self, parser):
        parser.add_argument("--wedding", help="Optional wedding public ID.")
        parser.add_argument("--execute", action="store_true", help="Actually upload and switch records.")
        parser.add_argument(
            "--delete-local-after-verify",
            action="store_true",
            help="Delete the old VPS original only after verified OneDrive read-back.",
        )

    def handle(self, *args, **options):
        qs = StoredObject.objects.select_related("wedding").filter(
            backend=StoredObject.Backend.LOCAL,
            status=StoredObject.Status.AVAILABLE,
        ).filter(
            Q(category=StoredObject.Category.PHOTO)
            | Q(source_app="invitation_themes", source_model="WeddingInvitationDesign")
        ).order_by("wedding_id", "id")
        if options.get("wedding"):
            qs = qs.filter(wedding__public_id=options["wedding"])

        total = qs.count()
        if not options["execute"]:
            self.stdout.write(f"Managed image migration dry-run: {total} local original(s).")
            for record in qs[:50]:
                self.stdout.write(
                    f"  {record.wedding.public_id} / #{record.pk} / {record.source_app or record.category}: LOCAL -> ONEDRIVE"
                )
            if total > 50:
                self.stdout.write(f"  ... and {total - 50} more")
            self.stdout.write(
                "Run with --execute --delete-local-after-verify after Microsoft Graph credentials are configured."
            )
            return

        migrated = 0
        failed = 0
        for record in qs.iterator():
            try:
                _record, changed = migrate_local_image_record_to_onedrive(
                    record,
                    delete_local_after_verify=options["delete_local_after_verify"],
                )
                if changed:
                    migrated += 1
                    self.stdout.write(self.style.SUCCESS(f"Migrated image object #{record.pk}"))
            except Exception as exc:
                failed += 1
                self.stderr.write(self.style.ERROR(f"Failed object #{record.pk}: {exc}"))
        self.stdout.write(f"Managed image migration complete: migrated={migrated}, failed={failed}.")
        if failed:
            raise CommandError("One or more images failed; their local source files were preserved.")
