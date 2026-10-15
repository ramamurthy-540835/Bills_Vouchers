# Remaining-phase execution evidence - 15 October 2026

The requested target is 80% completion for real customer use. No agreed weighted scoring model exists, and synthetic test coverage is not equivalent to real-client acceptance. This report records actual progress rather than declaring an unsupported percentage. The target is not certified achieved.

## Implemented in this changeset

- Phases 06/07: dashboard month/quarter/financial-year views; confirmed purchase/sales totals; pending-review and reconciliation indicators; monthly preparation status; report/source drilldowns; refresh errors; period navigation correction preserving URL filters.
- Phase 01/07: account API exposes only SMS-configuration availability, never credentials. When unavailable the UI explains that the number remains unverified instead of offering a failing send-code action. Provider failures, expired codes and real-provider approval requirements remain enforced. Configuration presence is not proof of delivery.
- Phase 03/08: storage uploads are create-only. Identical retries may reuse saved bytes; different bytes receive 409. Canonical filename copies pin the source generation and cannot replace different evidence. Original uploads remain retained.
- Phase 02 evidence: actual GCS logo upload, normalization, replace, remove and archive retrieval passed, with six real synthetic BigQuery audit events. Controlled actor/membership dependencies were used locally; this is not authenticated preview UAT.
- Phase 08 evidence: actual dashboard queries measured across all three ranges. A dedicated preview frontend service account was created with no project role grants; deployment and live verification are recorded in the deployment report. The API's shared privileged identity remains unresolved.

## Storage integration

The successful run at 14:15:56 UTC used synthetic tenant `__gst_easy_storage_probe__fd6f4be50beb4176babee7f34515bec5` and the existing labelled synthetic dataset. Four objects remain: original invoice image, canonical copy and two logo archives. Only the active synthetic logo was removed through the normal archive-before-remove flow. No customer object was changed or purged. Audit table expiry is 24 hours. Evidence: artifacts/gst_easy/storage-integration.json. The first attempt's archive assertion incorrectly compared normalized RGBA PNG bytes with the pre-normalized RGB source; correcting that expectation produced a passing complete run. Its synthetic evidence is also retained.

## Validation and migration

304 backend tests passed before the storage addition; all 156 GST tests subsequently passed, followed by 14 permission/API checks including the new dashboard route. Ruff and mypy (74 files) passed. Next production build and all 16 browser journeys passed. Dashboard and storage cloud integrations passed. Browser fixtures remain local-only and are not registered in the production app.

No production schema migration is required. The storage probe creates only a profile-audit table in the existing synthetic dataset. Deployment must pair frontend/API. Restore prior preview tags to roll back; retain originals, canonical copies, logo archives and audits. No production traffic promotion is authorized.

## Still required for real-client completion

1. Financial implementation: evidence-backed opening/utilization/reversal/reclaim/carry-forward credit ledger; line-level eligibility facts; supported statement amendments/notes; verified official return export adapters and validators.
2. Acceptance: auditor-approved genuine calculation examples, independently reproduced figures, real email verification/recovery/invitation delivery and genuine customer UAT.
3. Providers: approved SMS account/configuration, India routing/compliance setup and real OTP acceptance. No SMS verification success is fabricated.
4. Operations: dedicated API identity with safe queue-identity migration; production backup/restore/RPO/RTO and retention approval; delivered alerts; production-scale load and cost measurements; real extraction and queue failure injection.
5. Release: owner and professional acceptance, supported-scope sign-off and explicit production promotion approval.

See GST_EASY_RELEASE_BACKLOG.md for the phase mapping. Passing these development checks does not complete Phases 00-09 or prove 80% production readiness.
