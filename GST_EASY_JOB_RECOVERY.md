# Durable upload recovery - 15 October 2026

## Behavior and boundaries

New uploads and newly claimed workers use recovery protocol version 1. The existing job JSON stores a random worker claim; no schema migration is needed. A transaction records each claim/retry with actor and before/after evidence in the existing bill audit. Claim conflicts return 409. Database checks bind every worker progress update and invoice insertion to the current unexpired claim. A superseded worker cannot update progress or insert invoices.

An upload that failed can be retried from Bills > Upload history and deleted bills. A protocol-1 queued/reading upload becomes retryable after 35 minutes without a persisted checkpoint. Active uploads remain unavailable for manual retry. Retry preserves original objects, extracted evidence and saved invoice IDs; stable invoice IDs and existing duplicate guards prevent reinsertion. Completed deliveries do nothing. Extracted objects use a claim-specific filename, preventing a superseded extractor from replacing the new worker's saved extraction.

Failed storage/database operations retain the latest saved checkpoint and expose a recovery message. Filing locks propagate as locked-period errors rather than misleading duplicate messages. Worker authorization is rechecked using the original uploader; recovery never transfers the original uploader's permissions to another user. Clients still need backend bill-write permission to retry, and all queries are tenant scoped.

Browser polling stops when an upload needs recovery so controls become available. History explains the inactivity threshold and exposes Retry saved upload only when appropriate. Original documents are retained.

## Operator procedure

1. Identify the authorized business, period and upload in history. Do not re-upload merely because dispatch timed out.
2. Check worker/queue logs and the last checkpoint. Never display raw object references or worker tokens in customer messages.
3. Retry failed or eligible stale jobs through the application. An uncertain retry response means dispatch may have succeeded; refresh history before another attempt.
4. Investigate repeated failures, revoked uploader access and locked periods. Do not bypass authorization or unlock a financial period merely to force processing.
5. Older queued/reading jobs without protocol 1 are not automatically recovered. Establish that old workers have stopped and review an explicit recovery procedure first; this release does not mutate historical jobs in bulk.
6. Preserve all original objects, audit records and deleted evidence. No physical cleanup or historical seed execution is part of recovery.

## Source and tests

Implementation: app/gst/job_state.py, app/gst/store.py, app/gst/jobs.py, app/routers/gst_bills.py and frontend/app/bills/bills-panel.tsx. Existing retry/progress/history endpoints expose retryability and a safe explanation. No new permission or external API integration.

Regression evidence: 284 backend tests, Ruff, mypy (72 source files), Next production build and 14 local browser journeys passed. New tests cover active-claim denial, completed no-op, failure preservation, reuse of extraction after an invoice-write failure, locked-period errors, legacy exclusion and history recovery controls. Local browser backend now supplies an empty statement history for source-link prefetch rather than raising an AttributeError. Actual BigQuery integration passed on 15 October at 12:33 UTC in `aidirac-503309.gst_easy_bills_test_eb306dfe1e6b`: concurrent worker claims returned 200/409; stale retry succeeded; superseded progress and invoice writes were denied; completed deliveries were no-ops; retry actor audit and tenant isolation passed. Existing restore/reconciliation/return-lock checks also passed. Tables expire after 24 hours. The first run stopped on a missing required field in the synthetic test invoice; the corrected fixture passed. Preview deployment evidence is recorded separately.

## Release and rollback

Deploy a paired API/frontend only to the GST Easy preview. New claims/checkpoints add BigQuery transactions and audit rows; throughput/cost still needs measurement. This feature does not prove end-to-end real Cloud Tasks delivery, Gemini extraction or disaster recovery.

Prefer a forward fix for recovery defects. Rolling back to an unfenced worker while recovery workers remain active removes the safety boundary: first stop new recovery requests, verify active deliveries have ended, and review queue routing. Preserve job/audit/object evidence. Do not reset job statuses or worker tokens in bulk. Production promotion remains a separate approval gate.
