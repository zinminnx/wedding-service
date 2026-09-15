# EverAfter v13.2 - Audit & Analytics

Prerequisites: EverAfter through v13.1 Dashboard Theme Platform.

## Adds

- Wedding-scoped central `AuditEvent` ledger.
- Successful authenticated mutation logging through middleware.
- No POST body, password, invitation token, print-agent token, source token, or IP address is stored by the central request audit.
- Historical backfill from existing Financial Audit, Archive Events, Check-in Events and Return Gift movements.
- Owner-only full Audit Trail with category / actor / date / search filters and UTF-8 CSV export.
- Owner + Wedding Manager operational Analytics dashboard.
- Live KPIs for guests, invitation opens, RSVP, expected attendance, check-in, gifts, photos, printing and planner tasks.
- Up to 30 days of daily activity visualization for RSVP, check-ins, photos and audited mutations.
- Analytics CSV export.
- Module Registry activation for `analytics`.
- Existing feature data is never deleted when Analytics is disabled.

## Permission rule

Wedding Managers can view operational Analytics. The detailed Audit Trail and audit CSV are Wedding Owner / Super Admin only.

The analytics page intentionally reports operational counts rather than private financial amounts.

## Install

Extract this ZIP into the project root (same folder as `manage.py`) and run:

```powershell
Ctrl + C
.\.venv\Scripts\Activate.ps1
.\apply_patch.ps1
```

Then:

```powershell
python manage.py runserver
```

Open:

- Analytics: `http://127.0.0.1:8000/dashboard/analytics/`
- Owner Audit Trail: `http://127.0.0.1:8000/dashboard/audit/`

The installer runs `migrate`, `seed_modules`, historical audit backfill, `manage.py check`, a standalone smoke check, and `makemigrations --check --dry-run`. It does not create a Django test database.
