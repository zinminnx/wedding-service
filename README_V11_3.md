# EverAfter v11.3 - Vendors & Planner Quotes

Requires:
- v10.4 Module Registry
- v11.1 Budgeting Foundation
- v11.2.2 Planner Installation Repair

## What this patch adds

- Dedicated `vendors` Django app.
- Wedding-scoped vendor directory.
- Vendor quotation / planner-estimate workflow.
- Draft -> Proposed -> Owner Approved / Rejected / Withdrawn states.
- Alternative comparison groups (e.g. three Photographer quotes).
- Wedding Owner-only approval/rejection.
- Approved quote creates a `BudgetItem(source=PLANNER)`.
- Draft/proposed/rejected quotes never affect financial totals.
- Wedding Financial Summary consolidates Couple costs + Owner-approved Planner costs.
- Planner costs remain read-only on the Budget page and are managed from Vendors & Quotes.
- Module Registry key `vendors`, depending on `planner` and `budgeting`.
- Server-side module gate and sidebar navigation.

## Important financial rule

A Planner quote is not a committed wedding cost merely because it exists or is proposed. It enters the Planner Budget only when the Wedding Owner approves it.

For quotes sharing the same non-empty Decision Group, approving one automatically rejects other currently proposed alternatives in that group.

`deposit_amount` in v11.3 is a vendor quotation term only. It is not automatically recorded as a paid amount. Payment/receipt document workflows continue in the next financial milestone.

## Install

Extract the ZIP into the project root (same folder as `manage.py`), then run:

```powershell
.\.venv\Scripts\Activate.ps1
.\apply_patch.ps1
```

Then:

```powershell
python manage.py runserver
```

Open:
- `http://127.0.0.1:8000/dashboard/vendors/`
- `http://127.0.0.1:8000/dashboard/budget/`

## Suggested verification

1. Add three vendors/quotes with Decision Group `Photographer`.
2. Propose all three.
3. As Wedding Owner, approve one.
4. Confirm the approved quote appears under Planner Budget on the Budget page.
5. Confirm the other proposed quotes in the same Decision Group become Rejected.
6. Confirm Draft/Rejected quote amounts do not affect the Financial Summary.
