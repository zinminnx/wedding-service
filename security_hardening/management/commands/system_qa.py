from django.core.management.base import BaseCommand, CommandError

from security_hardening.qa import run_full_qa


class Command(BaseCommand):
    help = "Run non-destructive EverAfter release QA without creating a Django test database."

    def add_arguments(self, parser):
        parser.add_argument("--quick", action="store_true", help="Skip deeper wedding-data/storage integrity scans.")
        parser.add_argument("--skip-git", action="store_true", help="Skip Git tracked-secret and dirty-worktree checks.")
        parser.add_argument("--strict", action="store_true", help="Treat WARN results as command failure.")
        parser.add_argument("--json", dest="json_path", help="Write a machine-readable QA report to this path.")

    def handle(self, *args, **options):
        report = run_full_qa(quick=options["quick"], skip_git=options["skip_git"])

        for item in report.items:
            line = f"[{item.level}] {item.code}: {item.message}"
            if item.detail:
                line += f" | {item.detail}"
            if item.level == "FAIL":
                self.stderr.write(self.style.ERROR(line))
            elif item.level == "WARN":
                self.stdout.write(self.style.WARNING(line))
            else:
                self.stdout.write(self.style.SUCCESS(line))

        if options.get("json_path"):
            path = report.write_json(options["json_path"])
            self.stdout.write(f"JSON report: {path}")

        counts = report.counts
        self.stdout.write("")
        self.stdout.write(
            f"EverAfter QA summary: {counts['PASS']} PASS / {counts['WARN']} WARN / {counts['FAIL']} FAIL"
        )

        if counts["FAIL"]:
            raise CommandError("EverAfter system QA found blocking failures.")
        if options["strict"] and counts["WARN"]:
            raise CommandError("EverAfter system QA strict mode found warnings.")
        self.stdout.write(self.style.SUCCESS("EverAfter system QA: PASS"))
