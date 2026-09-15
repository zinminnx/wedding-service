# EverAfter v14.1 Release QA Checklist

Use this after all milestone ZIPs are installed and before production deployment.

## 1. Development QA

```powershell
python manage.py system_qa --json deploy/last_qa_report.json
```

Warnings about production mode are normal while `EVERAFTER_PRODUCTION=False`.

## 2. Git safety

Confirm the report says `.env` and `local_print_agent/agent.env` are not tracked. Review every uncommitted path before committing.

## 3. Manual role matrix

Use separate accounts/workspaces and verify at minimum:

- Owner: full wedding/module/staff/archive access.
- Manager: daily operations but no ownership/archive/delete/package authority.
- Planner: planner/vendors/shared finance only; no private Couple finance leakage.
- Reception Staff: RSVP/check-in/return-gift operations only.
- Photo Staff: photo moderation/slideshow only.
- Print Staff: print queue only.
- Viewer: read-only areas only.

Test URL tampering between two weddings for Guests, Invitations, RSVP, Gifts, Photos, Finance, Printing, Planner and Archive.

## 4. Storage / printing

- Local photo upload, preview, download and ZIP download.
- If OneDrive is configured: upload + read-back + SHA verification before deleting any local source.
- Local Print Agent: `--once --dry-run` before real printing.
- Confirm a PRINTING job is not silently auto-requeued after an uncertain printer result.

## 5. Archive

Create a snapshot, verify SHA-256, download it, then perform a restore drill in a safe/non-production dataset. Never purge source data until archive verification and restore testing are both confirmed.

## 6. Production mode

Only on the production environment:

```powershell
python manage.py production_check
python manage.py check --deploy
python manage.py system_qa --strict --json deploy/production_qa_report.json
```

Do not enable HSTS preload until every relevant subdomain is permanently HTTPS.

## 7. Backup before release

Take a PostgreSQL backup and confirm storage/archive recovery procedures before changing live traffic.
