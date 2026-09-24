# GST Workspace

The authenticated `/gst/workspace` page defaults to actual records for the selected client. The sidebar replaces Demo workspace with GST Workspace. Synthetic examples remain behind a secondary, labelled link and never become customer financial entries.

Choose a month and a reporting view: monthly preparation, calendar-quarter review, or Indian financial year (April to March). Each section is scoped by the selected client's authorised session and bound period parameters. Overview financial figures still come exclusively from Gold.

## Using actual records

1. Select the authorised client in the account menu and choose the return period.
2. Check Client profile. A tax administrator must complete the GSTIN and confirm filing frequency and applicable rules. This view displays the profile; editing remains through the administrator API.
3. Upload bills in Documents. Purchases shows extracted amounts and explains corrections; follow Review original to inspect and correct the bill. Unreviewed bills are excluded from financial calculations.
4. Open the relevant month in GST Filing & ITC, import the actual sales register and GSTR-2B in the supported normalised JSON format, and run ITC computation.
5. Review line decisions and rule references, tax-head totals, reconciliation differences, blocked/deferred/reversed credit and all readiness checks.
6. Download working papers for the selected reporting view. The ZIP contains CSV registers, ITC decisions, reconciliation, review issues, a JSON snapshot, README and a SHA-256 manifest.
7. Verify final figures in the GST portal, submit there, and have a tax administrator record the acknowledgement and lock the period.

## Boundaries that remain explicit

- The app prepares working papers and draft JSON. Current GST portal-upload schemas are not verified; it does not submit returns or make payments.
- Quarter totals consolidate monthly records; they are not a completed QRMP return. Cash totals add monthly estimates without modelling inter-period credit carry-forward, opening balances, payments, interest or late fees.
- Annual view is a financial-year review, not a completed GSTR-9/GSTR-9C. Composition returns and reverse-charge workflows need separate verification. Nil sales/credit require preparer confirmation; absence of records is never treated as a declaration.
- Reports are capped at 20,001 rows per source table and explicitly blocked as incomplete above 20,000. Export smaller periods if needed.
- A previously validated invoice that fails subsequent review triggers recomputation so stale ITC is removed. Invoice header totals are checked against taxable value and tax, allowing a one-rupee rounding tolerance; differences require review.
- Source evidence is retained. The workspace and downloads do not change customer financial records.

## Validation

`pytest -q`, `ruff check app tests`, `mypy app`, frontend `npm run build`, `scripts/gst_workspace_smoke.py`, and read-only `scripts/gst_workspace_live_smoke.py` (credentials from environment).

Unit tests cover period boundaries, current Gold runs, exclusion of unreviewed amounts, absence of retrospective cross-month netting, tenant/period query binding, spreadsheet formula escaping and ZIP integrity. Browser checks exercise every report section, searches, downloads, reporting selectors and mobile layout.
