from django.core.management.base import BaseCommand

from integrations.graph import get_graph_config
from integrations.models import StoredObject, WeddingStorageSettings


class Command(BaseCommand):
    help = "Show EverVow storage foundation status without making network calls."

    def handle(self, *args, **options):
        config = get_graph_config()
        self.stdout.write(f"Graph configured: {'yes' if config.complete else 'no'}")
        if not config.complete:
            self.stdout.write("Missing: " + ", ".join(config.missing))
        self.stdout.write(f"Wedding storage settings: {WeddingStorageSettings.objects.count()}")
        self.stdout.write(f"Registered storage objects: {StoredObject.objects.count()}")
        self.stdout.write(self.style.SUCCESS("Storage foundation status: OK"))
