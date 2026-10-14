# Phase 04 — Reconciliation safeguards (in progress)

This is a partial implementation report, not financial acceptance.

## Implemented

`app/gst/matching.py` retains invoice dates, statement GSTIN/period, source SHA-256, parser version and B2B section provenance. It validates nested object shapes, rejects unsupported populated document sections and treats missing ITC-availability evidence as unavailable.

`app/gst/report.py` requires the supplier GSTIN, invoice number and invoice date to match before comparing tax amounts. Punctuation is preserved rather than silently merging distinct invoice numbers. Duplicate statement candidates cannot overwrite one another in an index or grant matched credit. The four independent cash scenarios remain separate.

`tests/gst/test_report_and_files.py` covers wrong/missing dates, punctuation differences, duplicate candidates, missing availability and unsupported sections. Full backend regression: 215 passed. Ruff and mypy passed (65 source files).

Follow-up: `app/gst/store.py` and `app/routers/gst_bills.py` now retain original statement JSON in private storage, record source metadata, preserve previous imported rows in the transactional audit and reject previously imported source hashes. GET `/api/gst/bills/gstr2b/history` and `/api/gst/bills/gstr2b/{hash}/original?period=...` expose scoped history and evidence. `frontend/app/returns-credit.tsx` provides history/download controls and explains the B2B-only scope.

Nine browser journeys passed, including statement history and import error feedback. The expanded actual BigQuery check passed statement provenance, repeated-source rejection and cross-tenant history isolation as well as prior lifecycle checks. Evidence: `artifacts/gst_easy/canonical-integration.json`, dataset `aidirac-503309.gst_easy_bills_test_ea937d9feae9`, 2026-10-14 11:29 UTC. Only synthetic rows were used; tables expire in 24 hours. Browser history was mocked and the integration uses a synthetic object reference, so actual GCS statement round-trip still needs preview evidence.

## Official-source review

Reviewed on 14 October 2026: [GST portal GSTR-2B FAQ](https://tutorial.gst.gov.in/userguide/returns/FAQ_gstr2b.htm). The portal describes additional eligibility restrictions beyond the availability shown on the statement. Its coverage includes more than B2B invoices, so the current B2B adapter must not imply complete statement coverage.

[CBIC Circular 98/17/2019](https://cbic-gst.gov.in/pdf/Circular-98-17-2019-GST.pdf) was located for tax-head utilization review, but direct retrieval failed in this session. This is not sufficient verification of current utilization rules. No utilization-rule update was made.

## Compatibility, migration and rollback

No schema migration or deployment was performed. Existing statement rows without invoice dates/availability evidence now remain unmatched or unavailable; re-import supported source statements after accountant review. Do not backfill invented dates or eligibility. Earlier source files cannot be reconstructed from missing historical evidence; the new version history applies prospectively.

Rollback by reverting this isolated code changeset and deploying an approved prior preview. That reintroduces the previous match weaknesses, so it requires review before real financial use. Customer data, production traffic and previous preview tags remain unchanged.

## Remaining work

### Two-sided reconciliation follow-up

Implemented `app/gst/reconciliation.py`, the scoped GET `/api/gst/bills/reconciliation?period=YYYY-MM`, and `frontend/app/reconciliation-panel.tsx`. The Returns & Credit screen now filters exact matches, per-head rounding differences, date mismatches, amount mismatches, ambiguous candidates, missing statement/book records, incomplete evidence and unsupported document types. Every candidate remains visible; date-only/duplicate candidates are never automatically approved. Bill links open the individual review drawer; statement links use the existing authorized original-download endpoint. Private object references are excluded.

Working-paper XLSX exports include reconciliation cases and statement candidates with per-head Decimal differences, source hashes and invoice identifiers. No calculation rule, tax credit, financial record or database schema changes. Comparison is read-only; authorized manual exception decisions and credit-ledger work remain outstanding. Existing four cash scenarios are unchanged.

Validation: 247 backend tests passed, Ruff and mypy (69 files) passed, production frontend build passed, and 11 browser tests passed. Browser coverage includes filter/retry/evidence links and 390px layout; reconciliation browser responses are synthetic. A mobile select overflow discovered by the test was corrected. The initial sandbox test run could not load cryptography DLLs; the permitted full run passed. No genuine financial acceptance is implied.

Deployment: pending isolated preview build at the time of this changeset; final revision/build evidence will be recorded in `GST_EASY_DEPLOYMENT_REPORT.md`. Rollback uses the previous API/frontend immutable images and only the `gst-easy` tags. No data migration or destructive rollback is required; retain SMTP and signing-secret bindings.

Accountant-approved examples and current official schema/validator verification; supported amendments and credit/debit-note imports; live source-storage validation and semantic duplicate policy; manual exception decisions; line-level eligibility evidence; opening/utilization/reversal/reclaim/carry-forward credit ledger; date/rate/RCM and tax-head rule acceptance; actual preview UI/API and genuine-data verification. Phase 04 is not complete.
