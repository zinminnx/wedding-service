# EverAfter v14.1 - Full System QA & Release Readiness

Prerequisite: v14.0 Security & Production Hardening.

This is a non-destructive QA/release checkpoint after the original major roadmap. It does not create a Django test database and does not change wedding business data.

## Adds

- `python manage.py system_qa`
- Machine-readable JSON QA report
- Django/database/migration checks
- Roadmap app registration checks
- Critical URL reverse checks
- Multi-wedding relation integrity checks
- Invitation/QR token presence checks
- Check-in override integrity
- Photo/storage wedding-scope integrity
- Printing approval/wedding-scope integrity
- Planner financial visibility integrity
- Financial document wedding-scope integrity
- OneDrive StoredObject metadata checks without making Graph network requests
- Archive verification metadata checks
- Production security-mode summary
- Git checks for accidentally tracked `.env` / print-agent runtime secrets
- Dirty working-tree warning
- Manual role / tenant isolation / storage / printing / archive release checklist

## Install

Extract into the project root and run:

```powershell
Ctrl + C
.\.venv\Scripts\Activate.ps1
.\apply_patch.ps1
```

Then run the full QA:

```powershell
python manage.py system_qa --json deploy/last_qa_report.json
```

or:

```powershell
.\deploy\run_release_qa.ps1
```

While local development mode is active, a warning that `EVERAFTER_PRODUCTION=False` is expected. Before a real production release, run the strict QA only after production environment variables and HTTPS/proxy settings are configured:

```powershell
python manage.py production_check
python manage.py check --deploy
python manage.py system_qa --strict --json deploy/production_qa_report.json
```

## Important

A PASS from automated QA does not replace the manual two-wedding URL-tampering test or the role matrix test. Those are listed in `deploy/QA_RELEASE_CHECKLIST.md`.
