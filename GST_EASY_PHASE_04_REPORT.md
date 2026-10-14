# Phase 04 — Reconciliation safeguards (in progress)

This is a partial implementation report, not financial acceptance.

## Implemented

`app/gst/matching.py` retains invoice dates, statement GSTIN/period, source SHA-256, parser version and B2B section provenance. It validates nested object shapes, rejects unsupported populated document sections and treats missing ITC-availability evidence as unavailable.

`app/gst/report.py` requires the supplier GSTIN, invoice number and invoice date to match before comparing tax amounts. Punctuation is preserved rather than silently merging distinct invoice numbers. Duplicate statement candidates cannot overwrite one another in an index or grant matched credit. The four independent cash scenarios remain separate.

`tests/gst/test_report_and_files.py` covers wrong/missing dates, punctuation differences, duplicate candidates, missing availability and unsupported sections. Full backend regression: 215 passed. Ruff and mypy passed (65 source files).

## Official-source review

Reviewed on 14 October 2026: [GST portal GSTR-2B FAQ](https://tutorial.gst.gov.in/userguide/returns/FAQ_gstr2b.htm). The portal describes additional eligibility restrictions beyond the availability shown on the statement. Its coverage includes more than B2B invoices, so the current B2B adapter must not imply complete statement coverage.

[CBIC Circular 98/17/2019](https://cbic-gst.gov.in/pdf/Circular-98-17-2019-GST.pdf) was located for tax-head utilization review, but direct retrieval failed in this session. This is not sufficient verification of current utilization rules. No utilization-rule update was made.

## Compatibility, migration and rollback

No schema migration or deployment was performed. Existing statement rows without invoice dates/availability evidence now remain unmatched or unavailable; re-import supported source statements after accountant review. Do not backfill invented dates or eligibility. Raw original statement retention and complete import version history still need implementation.

Rollback by reverting this isolated code changeset and deploying an approved prior preview. That reintroduces the previous match weaknesses, so it requires review before real financial use. Customer data, production traffic and previous preview tags remain unchanged.

## Remaining work

Accountant-approved examples and current official schema/validator verification; supported amendments and credit/debit-note imports; complete source preservation/version history; duplicate import handling; manual exception decisions; line-level eligibility evidence; opening/utilization/reversal/reclaim/carry-forward credit ledger; date/rate/RCM and tax-head rule acceptance; actual UI/API and genuine-data verification. Phase 04 is not complete.
