# Phase 08 — Operations and security progress

Deployment tooling now builds on the existing services with new `gst-easy` tags, immutable successful image digests, no-traffic routing, preserved existing tags and routing assertions. Separate preview bill/identity queues prevent dispatch to old preview workers. Additive migrations are recorded with SHA-256 and BigQuery job IDs. Secrets are not included in reports; only configuration-presence checks are recorded.

Security evidence includes the automated permission, tenant, token, duplicate/concurrency and workflow checks described in GST_EASY_SECURITY_REPORT.md. BigQuery synthetic integrations exercise failure/conflict boundaries and retain 24-hour expiring test tables. This is not a complete disaster-recovery test.

Deployment follow-up: both immutable images are live on new zero-traffic tags; original traffic and tags were preserved. A revision-scoped request/latency monitoring dashboard was created. Public endpoint/access smoke and desktop/mobile registration browser checks passed; see GST_EASY_DEPLOYMENT_REPORT.md.

Outstanding: replace the overprivileged shared compute runtime identity with reviewed least-privilege identities; measured load/latency/cost budgets; legacy unfenced-job/uncertain-dispatch repair; production backups and recovery acceptance; retention acceptance; delivered alerts; independent security review. These remain open despite the successful preview deployment.

## Synthetic restore evidence - 15 October, 13:27 UTC

`scripts/check_restore_drill.py --run` passed against the existing labelled synthetic integration dataset. It restored 12 tables from a common BigQuery snapshot timestamp into `gst_easy_restore_test_c8be83b6f05b`, comparing row counts, content SHA-256 and schemas. Snapshot/restored tables expire after 24 hours. It also created, copied and restored a tiny synthetic object under `__gst_easy_restore_probe__/c8be83b6f05b/` in the existing private application bucket, verifying original/restored bytes and recording generations. Three objects are retained; no source deletion or overwrite occurred. Evidence: `artifacts/gst_easy/restore-drill.json`. Total drill runtime was 62.78 seconds, not a production RTO measurement.

Two initial drill attempts failed on script SQL escaping and an overly restrictive table-name validator; both were corrected and the complete run passed. Their isolated tables also expire after 24 hours. No customer data was used. This tests restoration mechanics, not complete production disaster recovery: scheduled backups, independent failure domains, identity/configuration restoration, retention approval, production-scale RPO/RTO and operational recovery remain unaccepted.

Read-only IAM audit confirmed the shared runtime identity still has broad project roles including Run admin, Artifact Registry writer, Cloud Build builder, Storage object admin, BigQuery data editor and Secret Manager accessor. No IAM role was removed or added. A dedicated identity rollout must account for queued OIDC worker identities and readiness bucket-metadata access; granting a new identity permission to impersonate the old privileged identity is not an acceptable shortcut. Production identity changes require a separately reviewed migration.

Reconciliation release follow-up: monitoring now updates the recorded dashboard in place with an etag and verifies its project/display name before replacement. The actual update succeeded for API `00117-ner` and web `00054-mel`; no duplicate dashboard or notification changes. Live smoke includes the new reconciliation authorization boundary. SMTP/signing-secret configuration remains active after deployment.

Rollback uses saved traffic-before evidence and prior immutable image digests. Do not drop additive tables, audit history or retained evidence during application rollback. Production promotion requires separate explicit authorization.


## Worker recovery - 15 October 2026

Latest preview hardening: frontend revision `bills-voucher-web-00059-cij` now uses dedicated `gst-easy-web-preview@aidirac-503309.iam.gserviceaccount.com`, with no direct project role grants. Its public page/proxy/browser checks passed. The API remains on the shared privileged identity, so least-privilege hardening is only partial. No service-account key, token-creator or impersonation grant was added. This follows the [Cloud Run service identity guidance](https://docs.cloud.google.com/run/docs/configuring/services/service-identity): a service not directly calling Google Cloud APIs needs no roles for those APIs. Existing production revision identities and routing were preserved.

The dashboard now loads and verifies all selected months in two bounded queries. Synthetic measurements were 3.993s/month, 3.583s/quarter and 5.532s/year, with 52,428,800 billed bytes per query. This establishes a small-fixture baseline, not an SLO or production load test. Original evidence writes now use generation preconditions and reject different-byte collisions; actual synthetic GCS retries, naming and logo archive/audit round trips passed. See the progress and deployment reports for retained test objects and rollback effects.

Added audited worker claims with 35-minute inactivity expiry and claim checks inside canonical invoice/progress transactions. Eligible failed/stale uploads can be recovered through authorized history controls. The actual BigQuery integration passed concurrency, superseded-worker denial, tenant isolation and audit checks; see GST_EASY_JOB_RECOVERY.md. No new schema, queue configuration, IAM grant or production traffic change is required. Real Cloud Tasks/GCS/Vertex failure injection and load/cost measurements remain necessary. Older in-flight jobs are excluded from automatic recovery until their unfenced workers are reviewed.
