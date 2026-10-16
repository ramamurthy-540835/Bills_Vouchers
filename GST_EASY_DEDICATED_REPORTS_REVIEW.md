# Dedicated GST Easy reports - local delivery, 17 October 2026

## Status and audit

Local changes only on GST_EASY. No commit, push, Cloud Run deployment, production traffic change, GCP write or migration. Existing uncommitted work was preserved.

Before implementation, all nine Open report controls changed a selector on the same page instead of navigating to a dedicated destination. The nine local API calls returned their correct kind/title and selected client, but the empty fixture returned zero invoice rows (cash returned tax-head rows). This was not evidence of populated, persisted report functionality. Missing capabilities included dedicated URLs, richer source fields, row filters, and distinguishing an absent statement import from unmatched invoices.

## Final category order and route mapping

Semantic source order, keyboard order and visual order are identical: GST & ITC; Invoice & Reconciliation; Sales & Purchase. Desktop uses three equal columns, tablet two, mobile one. The dashboard KPI grid is unchanged in this task.

All routes use GET /api/gst/bills/reports with the indicated kind and authenticated session-selected business:

| Report | Stable route | API kind |
|---|---|---|
| Usable Input Tax Credit | /reports/usable-itc | credit |
| GST Liability on Sales | /reports/gst-liability | liability |
| Estimated GST Cash Requirement | /reports/cash-requirement | cash |
| Purchases Without ITC | /reports/purchases-without-itc | without_itc |
| Pending Bill Reviews | /reports/pending-reviews | pending |
| Reconciliation Mismatches | /reports/reconciliation-mismatches | mismatches |
| Unmatched Invoices | /reports/unmatched-invoices | unmatched |
| Sales Register | /reports/sales-register | sales |
| Purchase Register | /reports/purchase-register | purchases |

Existing /reports?kind= bookmarks and legacy report choices remain supported. Invalid dedicated slugs return 404. Dedicated routes retain report permission checks and active membership, period selection, refresh and business-switch context. Filters belonging to the previous business are discarded on a business switch.

## Functionality and architecture

Canonical gold.gst_invoice is the invoice source; silver.gst_bills_gstr2b and its import history provide matching evidence. Legacy accounting and medallion filing records are not added to report totals. BillStore continues binding client_id and period parameters to its queries. Report generation retains source fingerprints and bounded report size checks. No schema or parallel reporting database was added to the production application.

report_details.py projects canonical invoices and existing calculate()/compare() results into the nine report tables. report.py exposes its already computed credit pools and scenario details without changing set-off rules or dashboard amounts. Reports include signed notes, eligibility reasons, matching status, source invoice links, original evidence where recorded, book/statement comparisons, and tax-head utilization for all four scenarios.

Filters (search, party, invoice type, eligibility, matching direction/status, invoice dates, sorting) apply to authorized rows before pagination and CSV/Excel rendering. Monthly financial context is clearly labeled as the full period; it is not recalculated from a searched subset. Filtered row totals and exports use the same rows and Decimal arithmetic. Formula-like spreadsheet values continue through the existing safe-cell writer. The existing tax-summary PDF remains available; unsupported PDF exports are not offered.

Pending reports open the existing Bills review drawer. Corrections use the existing authorized save API. Reconciliation reports pass the selected case to the existing Returns & Credit comparison and review UI. No second invoice editor, confirmation engine or reconciliation resolution service was created.

## Changed source files for this task

Frontend:
- frontend/lib/report-catalog.ts: ordered catalog, stable slugs and typed shared response.
- frontend/app/reports/[report]/page.tsx: one shared dynamic page resolving nine allowed routes.
- frontend/app/reports-panel.tsx: real links, dedicated report details, filters, summaries, source actions, exports, timeouts and errors.
- frontend/app/workspace-server.tsx and workspace.tsx: selected report context and period navigation preservation.
- frontend/lib/navigation.ts and frontend/proxy.ts: dedicated-route membership navigation and authentication coverage.
- frontend/app/reconciliation-panel.tsx: select the report-linked exception in the existing review interface.
- frontend/app/gst-easy.css: catalog responsive order and filter wrapping; dashboard 3x3 styles preserved.

Backend:
- app/gst/report_details.py: report-specific evidence projections.
- app/gst/reports.py: shared row filters, metadata, summaries and consistent exports.
- app/gst/report.py: expose existing calculated pools/scenario details.
- app/routers/gst_bills.py: pass allowlisted filter arguments into report generation.

Tests:
- tests/gst/persisted_reports.py and browser_backend.py: explicit local SQLite synthetic fixture with two businesses and original PDFs; never included in the production app routes.
- tests/gst/test_detailed_reports.py: all nine persisted projections, exact financial examples, filters, exports, missing statements and separate tenants.
- tests/gst/test_reports.py: maintain classification checks including newly requested unestablished credit.
- tests/gst/test_bills_permissions.py: add statement-history method to the existing storage test double.
- tests/frontend/reports.spec.ts: nine route tests plus filters, originals, switching, responsive order, saved corrections and selected reconciliation case.
- tests/frontend/navigation.spec.ts: report catalog actions are now links rather than selector buttons.

## Recorded validation

- Full pytest: 386 passed, six existing dependency/lifespan deprecation warnings.
- Ruff: passed.
- Clean mypy: passed, 76 source files.
- Standalone TypeScript check: passed; production build's TypeScript check also passed.
- Next production build: passed, includes /reports/[report].
- Final full Playwright suite: 43 passed in 1.2 minutes.
- git diff --check: passed; existing LF/CRLF notices only.

An intermediate full pytest run exposed a test double missing statement_history; it was updated to match the actual BillStore interface. An intermediate browser run exposed an exact-label lookup issue for dynamic filters; explicit accessible labels were added and the filter journey passed. No outstanding test failure is known from the final runs.

All nine reports were individually opened and downloaded in the browser. Persisted test data was written to artifacts/gst_easy/report-fixtures.sqlite and read through separate SQLite connections. Assertions include net sales INR 5310.00 in business A, INR 10620.00 in business B, usable ITC INR 180.00, and independent cash estimates 0.00 / 270.00 / 630.00 / 810.00. These are synthetic test expectations, not customer figures or accountant acceptance.

## Screenshots and review

- artifacts/gst_easy/report-catalog-desktop.png
- artifacts/gst_easy/report-catalog-tablet.png
- artifacts/gst_easy/report-catalog-mobile.png
- artifacts/gst_easy/report-sales-mobile.png
- artifacts/gst_easy/report-usable-itc.png
- artifacts/gst_easy/report-gst-liability.png
- artifacts/gst_easy/report-cash-requirement.png
- artifacts/gst_easy/report-purchases-without-itc.png
- artifacts/gst_easy/report-pending-reviews.png
- artifacts/gst_easy/report-reconciliation-mismatches.png
- artifacts/gst_easy/report-unmatched-invoices.png
- artifacts/gst_easy/report-sales-register.png
- artifacts/gst_easy/report-purchase-register.png

Browser results: artifacts/v3/frontend-tests.json. Screenshots use designated synthetic local data. Local session bootstrap: http://localhost:3100/api/local-preview. Then open http://localhost:3100/reports?period=2026-09 to review populated test reports.

## Explicit limitations and dependencies

- Live BigQuery/GCS records and Cloud Run were not queried or validated in this local-only task. Production code uses the existing tenant-scoped canonical store; browser evidence used persisted local SQLite fixtures. This does not establish real-client or accountant acceptance.
- Canonical invoices do not store upload timestamps or assigned reviewers. Those fields are shown as unavailable rather than inferred or fabricated. Extraction confidence and stored review reasons are shown where present.
- Existing zero-rate classification reports NON-GST; it does not independently establish whether an invoice is exempt, zero-rated or non-GST. The report explains that limitation without changing tax rules.
- Purchases Without ITC now also shows eligible-classified lines whose credit is not established. Its broader scope is stated explicitly; the existing dashboard KPI retains its narrower non-eligible classification calculation.
- No imported statement means a dependency warning, not an assertion that every purchase is unmatched. An explicitly imported empty statement remains distinct and may produce missing-statement records.
- Reconciliation review status may be stale; the existing resolution workflow revalidates source fingerprints. Original statement downloads appear only where a source digest is recorded.
- Cash amounts are existing monthly estimates, not verified government electronic ledgers or a carry-forward ledger.
- The local fixture server is a test harness, not multi-user production authentication. It must never be deployed.

## Rollback

No cloud or data migration rollback is required. Review and reverse only this task's report-route/service/test hunks, retaining earlier uncommitted navigation, registration and dashboard work. Rebuild/restart the local frontend and fixture backend. Do not reset the working tree wholesale.
