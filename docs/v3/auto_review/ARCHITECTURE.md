# Invoice Intelligence architecture
Business policy lives in the existing tenant-bound audit table, separate from canonical financial payloads. This retains compatibility with older V3 revisions. A policy change requires bill-write permission and an expected version. The default is disabled, scope both.

Existing-invoice selection creates a durable intelligence_batch job with at most 100 unique invoice IDs and captured versions. Existing Cloud Tasks OIDC dispatch and job leases execute it. Each invoice is separately opted in and validated through the existing canonical confirmation service. The save transaction checks membership, version, locks and business-policy version before any financial replacement.

Future uploads inherit the selected business policy only when no explicit file/batch choice is supplied. The browser binds dispatch to expected_client. OFF never disables extraction or deterministic validation. Original GCS evidence remains private.

No new financial table or destructive migration is introduced. Policy audit, batch jobs and canonical invoices remain distinct sources with distinct purposes.

Status: implementation candidate; not a complete Auto Review 2.0 release. Local tests are not legal acceptance or live provider acceptance. V2 is excluded.
