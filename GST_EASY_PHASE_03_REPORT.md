# Phase 03 — Canonical bill lifecycle

Status: implementation in progress. These changes do not complete every Phase 03 acceptance requirement.

## Implemented changes

- Required, bounded rejection reasons stored in canonical invoice payloads and audit history.
- An explicit Decimal-only line-total summation API and review button. This sums entered amounts; it does not infer tax eligibility or replace invoice evidence.
- Tenant-scoped durable upload history and saved-upload retry after a definite dispatch failure. A transaction allows only one retry claim. An ambiguous Cloud Tasks timeout leaves the job queued rather than overwriting a potentially running worker.
- Deleted-bill listing and explicit restore to `needs_review`. Deleted source documents cannot silently reappear through re-upload. Version checks and the existing duplicate transaction protect concurrent restores.
- Existing filing status freezes now protect canonical edits, confirmation/rejection, delete/restore, import and upload. Date changes check both old and new periods. The existing filing transition uses the same canonical transaction guard when canonical bills are enabled. This does not combine medallion and canonical financial totals.
- Original evidence and deletion audit remain retained. No evidence purge or historical duplicate cleanup was performed.

## Changed files and APIs

Backend: `app/gst/schemas/invoice.py`, `app/gst/store.py`, `app/gst/jobs.py`, `app/routers/gst_bills.py`, `app/services/gst/workbench.py`.

Frontend: `frontend/app/bills/bills-panel.tsx`. Regression fixtures/tests: `tests/gst/browser_backend.py`, `tests/gst/test_bills_permissions.py`, `tests/frontend/copy.spec.ts`. Actual database checks: `scripts/check_canonical_integration.py`.

New endpoints: GET `/api/gst/bills/history`, GET `/api/gst/bills/deleted`, POST `/api/gst/bills/{id}/restore`, POST `/api/gst/bills/sum-lines`, POST `/api/gst/bills/upload/{id}/retry`. Reject now requires JSON `reason`.

## Migration and deployment

No new schema is required for this changeset. It uses existing canonical payload/audit/job tables and `finance_analytics.gst_filing_status`. Canonical guard provisioning from `infra/bq/migrations/007_gst_invoice.sql` must exist; missing guards fail closed. API and frontend must deploy together because reject now requires a reason. No Cloud Run revision, traffic or customer dataset was changed.

## Validation evidence

- Full backend suite: 210 passed. Ruff and mypy passed; frontend production build passed.
- Eight browser journeys passed after adding rejection, Decimal summation and delete/restore. Live Cloud Tasks retry delivery remains untested.
- Real BigQuery integration passed tenant isolation, canonical save/delete, prevention of deleted re-upload, concurrent restore (one 200 and one 409), restore-to-review, durable history, single retry claim, and frozen-period delete/import/date-move denial. Latest synthetic dataset `aidirac-503309.gst_easy_bills_test_202c8a2d8abc`; tables expire in 24 hours. Evidence: `artifacts/gst_easy/canonical-integration.json`, 2026-10-14 11:15 UTC.

## Remaining acceptance work

Queue-timeout repair and stale-running-job recovery need an operations workflow and failure injection. Full upload progress/refresh recovery, cross-period locking under simultaneous filing transitions, live extraction, retention approval, preview UI/backend validation and traceable dashboard impact still need evidence. Full canonical approval/snapshot/reopen workflow belongs to Phase 05 and is not implemented by these guards. Restore currently uses the existing bill-write permission; customer retention policy must approve that scope before release.

## Rollback

Roll back the paired frontend/API preview revisions. Keep retained original files, deleted audit payloads and job history. Never purge restored/deleted evidence to roll back code. Older code lacks the new deleted-evidence and freeze protections, so do not promote an older build for real financial writes without reviewing those limitations. Production traffic remains unchanged.


## Durable recovery follow-up - 15 October 2026

Added transactionally claimed workers, claim-checked progress and invoice writes, audited retry, preserved extraction checkpoints and recovery controls for failed/stale protocol-1 jobs. Inactivity threshold is 35 minutes. Legacy in-flight jobs without the new protocol require operator review. Filing locks now propagate instead of being mislabeled as duplicate invoices. No schema migration or historical job backfill. See GST_EASY_JOB_RECOVERY.md for implementation, tests, operator procedure and rollback constraints. 284 backend tests, 14 browser tests, Ruff/mypy and frontend production build passed. Actual Cloud Tasks/GCS/Vertex failure injection, retention acceptance and authenticated customer UAT remain open; Phase 03 is not fully accepted.
