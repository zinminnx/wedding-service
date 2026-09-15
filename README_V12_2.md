# EverAfter v12.2 - Printing System

Requires v12.0 Storage Foundation and v12.1 Photo Storage Upgrade.

This milestone adds the server-side wedding print queue. It intentionally does **not** perform silent browser printing. The trusted Windows Local Print Agent is the next milestone (v12.3).

## Adds

- `printing` Django app and Module Registry activation.
- Wedding-scoped print settings.
- Photo print jobs with Queue / Claimed / Printing / Printed / Failed / Cancelled states.
- Copies, paper size, fit mode, notes and audit-friendly timestamps.
- Approved-photo-only queueing.
- Local/OneDrive-neutral source downloads through the v12.1 photo storage bridge.
- Owner / Wedding Manager / Print Staff server-side access using `PERM_PRINT`.
- Owner/Manager queue enable/pause/default settings.
- Requeue, cancel, manual printed/failed controls for operations and testing.
- Sidebar navigation and Django admin screens.
- Printing depends on Photos in Module Registry.

## Important rule

v12.2 is a **cloud/server queue**, not the physical printer integration. Do not use browser auto-print or kiosk JavaScript as a substitute. v12.3 will add the local Python agent that claims queue jobs and sends them to the configured printer.

## Install

Extract into the project root and run:

```powershell
.\.venv\Scripts\Activate.ps1
.\apply_patch.ps1
```

Then:

```powershell
python manage.py runserver
```

Open:

`http://127.0.0.1:8000/dashboard/printing/`
