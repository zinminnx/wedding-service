from django.core.management.base import BaseCommand, CommandError

from printing.models import PrintAgentDevice
from weddings.models import Wedding


class Command(BaseCommand):
    help = "Create a wedding-scoped Local Print Agent token. The secret is printed once."

    def add_arguments(self, parser):
        parser.add_argument("wedding", help="Wedding public ID or slug")
        parser.add_argument("--name", default="Venue Print PC")
        parser.add_argument("--printer", default="")

    def handle(self, *args, **options):
        wedding = Wedding.objects.filter(public_id=options["wedding"]).first()
        if not wedding:
            wedding = Wedding.objects.filter(slug=options["wedding"]).first()
        if not wedding:
            raise CommandError("Wedding not found.")
        device, token = PrintAgentDevice.issue_token(
            wedding=wedding,
            name=options["name"][:120],
            printer_name=options["printer"][:200],
        )
        self.stdout.write(self.style.SUCCESS(f"Created print agent: {device.name}"))
        self.stdout.write("Copy this token now. It is not stored in plaintext:")
        self.stdout.write(token)
