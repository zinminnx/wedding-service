# EverAfter v11.4 - Financial Privacy & Documents

Prerequisites: v11.1 Budgeting, v11.2.2 Planner repair, v11.3 Vendors & Quotes.

Adds Couple Budget privacy (`Private` / `Shared with Planner`), a Planner-safe shared financial view, secure financial document uploads (PDF/images up to 10 MB), document links to Budget Items or Vendor Quotes, permission-checked downloads, and a financial audit trail for sensitive actions.

Planner-approved BudgetItems are always Shared. Owner-private Couple expenses are excluded from Planner tables, category summaries, totals, document selectors and downloads.

Install from the project root:

```powershell
.\.venv\Scripts\Activate.ps1
.\apply_patch.ps1
```

Then run:

```powershell
python manage.py runserver
```

Pages:
- `/dashboard/budget/`
- `/dashboard/finance-docs/`
- `/dashboard/vendors/`
