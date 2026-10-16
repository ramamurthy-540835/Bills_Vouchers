# GST Easy dashboard and reports redesign

Local implementation on GST_EASY; no commit, push or Cloud Run deployment. Earlier uncommitted changes remain preserved. No schema, migration, IAM, production traffic or storage changes.

## Source changes

- frontend/app/gst-easy-dashboard.tsx: one ordered nine-card grid; remove all card-level report links; preserve values and tooltips; move the invoice upload entry point after all informational sections. Authorized users see either Upload your first bills or Upload Bills, both linking to the existing Bills interface with the selected period.
- frontend/app/gst-easy.css: scoped grid/card, compact upload and report-category styles. Desktop has three columns, widths at or below 1100px have two, and at or below 700px have one. Fixed sidebar space is accounted for. Existing unrelated card selectors remain unchanged.
- frontend/app/reports-panel.tsx: three report groups and nine focused entries; retain original report choices, period/range selector, provenance, evidence links, pagination and exports; add refresh, monthly financial context and cash scenarios.
- frontend/app/workspace.tsx: pass the existing exact INR formatter to Reports.
- app/gst/reports.py: add focused report kinds using the existing canonical evidence, calculate(), reconciliation compare(), classification rules, fingerprints and export writer. No new financial engine or invoice writes.
- tests/gst/test_reports.py: focused kinds, exports, missing-data semantics, classification parity and cross-client rejection.
- tests/frontend/copy.spec.ts: replace obsolete card-link assertions with summary-only assertions while retaining range/refresh checks.
- tests/frontend/navigation.spec.ts: responsive grid dimensions, ordered layout, no card links, stable KPI values, upload placement and all nine report choices.

## Report mapping

| Entry | Existing service and focused view |
|---|---|
| Usable Input Tax Credit | Eligible line decisions, matching status, monthly calculated credit and tax heads |
| GST Liability on Sales | Confirmed sales register with monthly liability and tax-head context |
| Estimated GST Cash Requirement | Existing tax-head calculation and four independent monthly scenarios |
| Purchases Without ITC | Non-eligible purchase line decisions with reasons, signed GST and signed purchase value |
| Sales Register | Existing confirmed sales register |
| Purchases Register | Existing confirmed purchase register |
| Pending Bill Reviews | Canonical needs_review and extracted invoices |
| Reconciliation Mismatches | Existing comparison statuses excluding exact and missing records |
| Unmatched Invoices | Existing missing_book and missing_statement cases |

CSV and Excel remain available through the authorized report endpoint. The existing Tax-head summary retains PDF export; no unsupported PDF buttons were added. Export context retains missing-calculation indicators. Eligible line classification alone is explicitly distinguished from usable credit after matching, availability and credit-note rules.

## Validation and visual evidence

202 backend tests passed, covering tests/gst, navigation permissions and platform access. Ruff passed. Clean mypy passed across 75 files. Next production build and TypeScript checks passed (29 routes). The initial browser redesign test incorrectly counted Next.js route announcements as report errors; it now scopes assertions to the report region.

Screenshots, captured with synthetic local data:
- artifacts/gst_easy/dashboard-redesign-desktop.png
- artifacts/gst_easy/dashboard-redesign-tablet.png
- artifacts/gst_easy/dashboard-redesign-mobile.png
- artifacts/gst_easy/reports-redesign-mobile.png

Final Playwright run: 30 tests passed in 47.3 seconds. Browser results: artifacts/v3/frontend-tests.json.

## Scope and limits

The local preview uses synthetic in-memory fixtures, not real customer accounts. Live cloud verification and accountant acceptance were not performed. Existing calculations remain unchanged: range totals sum independent monthly estimates, not a carry-forward ledger. Reports continue to reject synthetic invoices and unauthorized tenant evidence. Existing report limits and classification coverage remain in effect; no missing evidence is fabricated. Returns & Credit still has no upload action; it reuses the summary component with uploads disabled. Bills upload, extraction, review and duplicate handling remain on the existing pipeline.

## Review and rollback

Open http://localhost:3100/api/local-preview then choose GST Easy or Reports. No cloud rollback is needed. To reverse this task, review and reverse only the redesign hunks listed above, preserving earlier local role/navigation changes, then rebuild/restart the local preview. Do not reset the working tree wholesale.
