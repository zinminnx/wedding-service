# EverAfter v13.0 - Archive & Restore

Prerequisites:
- v10.4+ Module Registry
- v12.0 Storage Foundation
- Current wedding lifecycle statuses in `weddings.Wedding`

## What this patch adds

- Dedicated `archive_restore` Django app.
- Owner-only Archive & Restore dashboard at `/dashboard/archive/`.
- Wedding-scoped archive snapshots with audit events.
- Self-contained ZIP export containing:
  - `data.json` for wedding-scoped database records,
  - managed `StoredObject` file bytes,
  - legacy Django `FileField` uploads not yet registered in Storage,
  - `manifest.json` with per-file SHA-256 hashes.
- Archive verification checks:
  - outer ZIP SHA-256,
  - `data.json` checksum,
  - every archived file size and SHA-256.
- Archive packages are stored through the v12 Storage abstraction, so the selected wedding backend may be Local or OneDrive.
- Wedding can be marked `ARCHIVED` only after a verified snapshot exists.
- Restore reopens retained archived data as `DRAFT`, preventing invitations from being silently republished.
- `DELETE_PENDING` requires a verified snapshot and typed wedding ID confirmation.
- **No automatic database purge or storage deletion in v13.0.**
- Management command: `python manage.py verify_archives`.
- Module Registry activation with dependency `archive_restore -> onedrive`.

## Safety model

EverAfter follows: **Export -> Verify -> Archive -> Delete Pending**.

v13.0 deliberately stops before destructive purge. This means a failed archive, failed checksum, lost OneDrive object, or operator mistake cannot cause the patch itself to delete wedding data.

The v13.0 restore action is a non-destructive workspace restore. It verifies the snapshot, keeps the archive, keeps all retained records, and changes the wedding back to `DRAFT` for Owner review.

## Archive size ceiling

Synchronous archive builds default to 512 MB of source data to avoid unexpected memory pressure. Override in `.env` only after confirming server capacity:

```text
EVERAFTER_ARCHIVE_MAX_BYTES=1073741824
```

Use `0` to disable the ceiling.

## Install

Extract this ZIP into the wedding-service project root, then:

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

```text
http://127.0.0.1:8000/dashboard/archive/
```

## Verify archives from CLI

All snapshots:

```powershell
python manage.py verify_archives
```

One archive:

```powershell
python manage.py verify_archives --archive ARC-XXXXXXXXXXXX
```

One wedding:

```powershell
python manage.py verify_archives --wedding WED-XXXXXXXXXX
```
