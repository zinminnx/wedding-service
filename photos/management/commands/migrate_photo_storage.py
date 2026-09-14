from django.core.management.base import BaseCommand, CommandError

from integrations.models import WeddingStorageSettings
from photos.models import WeddingPhoto
from photos.storage_backend import migrate_photo_to_selected_backend


class Command(BaseCommand):
    help = "Safely migrate wedding photos to each wedding's selected storage backend. Dry-run by default."

    def add_arguments(self, parser):
        parser.add_argument("--wedding", help="Wedding public ID, e.g. WED-ABC123. Optional.")
        parser.add_argument("--execute", action="store_true", help="Actually migrate files.")
        parser.add_argument(
            "--delete-local-after-verify",
            action="store_true",
            help="Delete old local file only after OneDrive read-back SHA-256 verification.",
        )

    def handle(self, *args, **options):
        qs = WeddingPhoto.objects.select_related("wedding", "storage_object", "uploaded_by").order_by("id")
        if options.get("wedding"):
            qs = qs.filter(wedding__public_id=options["wedding"])
            if not qs.exists():
                raise CommandError("No photos found for that wedding public ID.")

        candidates = []
        for photo in qs.iterator():
            settings_obj, _ = WeddingStorageSettings.objects.get_or_create(wedding=photo.wedding)
            current = photo.storage_object.backend if photo.storage_object_id else "LOCAL"
            if current != settings_obj.provider or not photo.storage_object_id:
                candidates.append((photo.public_id, photo.wedding.public_id, current, settings_obj.provider))

        if not options["execute"]:
            self.stdout.write(f"Photo storage migration dry-run: {len(candidates)} candidate(s).")
            for public_id, wedding_id, current, target in candidates[:50]:
                self.stdout.write(f"  {wedding_id} / {public_id}: {current} -> {target}")
            if len(candidates) > 50:
                self.stdout.write(f"  ... and {len(candidates) - 50} more")
            self.stdout.write("Run again with --execute to migrate. Existing local files are kept by default.")
            return

        migrated = 0
        skipped = 0
        failed = 0
        for photo in qs.iterator():
            try:
                _record, changed = migrate_photo_to_selected_backend(
                    photo,
                    delete_local_after_verify=options["delete_local_after_verify"],
                )
                if changed:
                    migrated += 1
                    self.stdout.write(self.style.SUCCESS(f"Migrated {photo.public_id}"))
                else:
                    skipped += 1
            except Exception as exc:
                failed += 1
                self.stderr.write(self.style.ERROR(f"Failed {photo.public_id}: {exc}"))

        self.stdout.write(
            f"Photo storage migration complete: migrated={migrated}, skipped={skipped}, failed={failed}."
        )
        if failed:
            raise CommandError("One or more photos failed to migrate; source files were preserved.")
