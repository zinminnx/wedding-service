# EverAfter v13.1 - Dashboard Theme Platform

This milestone adds a dashboard-only theme platform. It is separate from Invitation Themes.

## Included

- Per-user visual theme preference.
- Independent layout density preference: Comfortable / Compact / Spacious.
- Five built-in visual themes:
  - EverAfter Classic
  - Ivory & Gold
  - Midnight Gold
  - Emerald Royal
  - Rose Champagne
- Main Admin theme management UI.
- Create/edit theme metadata, colors, fonts, radius and ordering.
- Activate/retire themes and choose the system default.
- Existing users keep a retired theme until they switch; retired themes cannot be newly selected.
- Dashboard roles, module permissions and wedding access are never changed by a theme.
- Dynamic CSS variables preserve the existing dashboard structure rather than replacing shared CSS.
- Module Registry activates `dashboard_themes` as a system-level, non-wedding-toggle feature.

## Install

Extract this ZIP into the project root (same folder as `manage.py`), merge/replace, then run:

```powershell
Ctrl + C
.\.venv\Scripts\Activate.ps1
.\apply_patch.ps1
```

Restart:

```powershell
python manage.py runserver
```

Open:

- `http://127.0.0.1:8000/dashboard/themes/`
- `http://127.0.0.1:8000/dashboard/themes/manage/` (Main Admin only)

The installer runs `migrate`, `seed_modules`, `check`, a standalone smoke check, and `makemigrations --check --dry-run`. It does not create a Django test database.
