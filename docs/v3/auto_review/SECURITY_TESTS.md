# Security evidence
Local tests exercise default OFF, malformed policy input, required If-Match, viewer denial, version conflicts, individual exclusion, period locks, cancellation, duplicate checks, original evidence and atomic membership/policy fences. Existing tenant, original-file, CSRF, worker and correction regressions remain in the backend/browser suites.

Business policy resides outside canonical invoice JSON so older revisions can still read shared records. Workers retain OIDC validation and membership rechecks. No public GCS URL, new global permission, real-customer global AI allowance or disabled filing lock is introduced.

BigQuery SQL unit tests inspect transaction guards; only a live candidate test can verify actual database execution. Live cross-tenant and concurrent load verification for this release remains pending.

Status: implementation candidate; not a complete Auto Review 2.0 release. Local tests are not legal acceptance or live provider acceptance. V2 is excluded.

Live candidate evidence: business policy transactions and durable batch execution succeeded against V3 BigQuery/Cloud Tasks. V2/older Bills & Vouchers configurations and existing V3 traffic passed the final comparison. The all-project comparison retains an unrelated prism-frontend drift failure; see V3_DEPLOYMENT_REPORT.md.
