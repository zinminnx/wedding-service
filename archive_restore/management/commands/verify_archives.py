from django.core.management.base import BaseCommand, CommandError

from archive_restore.models import ArchiveSnapshot
from archive_restore.services import verify_snapshot


class Command(BaseCommand):
    help = "Verify EverAfter archive ZIP checksums."

    def add_arguments(self, parser):
        parser.add_argument("--archive", dest="archive_id", default="")
        parser.add_argument("--wedding", dest="wedding_public_id", default="")

    def handle(self, *args, **options):
        queryset = ArchiveSnapshot.objects.select_related("stored_object", "wedding").exclude(stored_object=None)
        if options["archive_id"]:
            queryset = queryset.filter(public_id=options["archive_id"])
        if options["wedding_public_id"]:
            queryset = queryset.filter(wedding_public_id=options["wedding_public_id"])
        if not queryset.exists():
            raise CommandError("No matching archive snapshots found.")
        failed = 0
        for snapshot in queryset:
            try:
                verify_snapshot(snapshot)
                self.stdout.write(self.style.SUCCESS(f"OK {snapshot.public_id} {snapshot.wedding_public_id}"))
            except Exception as exc:
                failed += 1
                self.stderr.write(self.style.ERROR(f"FAIL {snapshot.public_id}: {exc}"))
        if failed:
            raise CommandError(f"{failed} archive(s) failed verification.")
