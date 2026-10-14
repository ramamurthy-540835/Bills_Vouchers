# Phase 05 — Canonical return preparation

Implemented: immutable period snapshots from canonical invoices and statement evidence, preparer submission, separate tax-administrator review, approval/rejection, reasoned reopen, source-version fingerprints and transaction-serialized period freezes. Synthetic workspaces and unreviewed invoices cannot prepare real snapshots. No endpoint marks a return Filed. Approved working-paper JSON remains explicitly Draft format, not government-upload-ready.

Files: `app/gst/returns.py`, `app/routers/gst_returns.py`, `app/main.py`, `app/gst/store.py`, `app/services/gst/account.py`, `frontend/app/return-workflow.tsx`, `frontend/app/returns-credit.tsx`, associated API/domain/browser tests and `scripts/check_canonical_integration.py`.

Migration: additive `013_canonical_return_workflow.sql` creates current state, immutable snapshots and audit tables in ops. Apply before deploying new bill guards. Current-state versions and financial writes share the existing transaction guard; profile edits also serialize with it. No legacy/medallion totals are merged into canonical calculations.

Evidence: 231 backend tests pass; Ruff/mypy and frontend build pass. Actual BigQuery synthetic integration passed stale-source denial, review, approval freeze and reopen in `gst_easy_bills_test_707715f7591d` on 2026-10-14 11:50 UTC. This is workflow evidence, not accountant acceptance. Financial examples remain synthetic.

Remaining: supported current official GSTR-1/GSTR-3B schemas and validators, nil returns, complete credit-ledger/reconciliation acceptance, real accountant/maker-checker UAT. Period snapshots currently cover the combined canonical evidence; portal-specific return adapters are not certified. Phase 05 is not fully accepted.

Rollback: restore prior paired preview revisions, preserve all snapshot/audit tables and recorded approvals. Older code lacks canonical freezes, so do not use it for live financial writes without review. Never delete snapshots to roll back application code.
