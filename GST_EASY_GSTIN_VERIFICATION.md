# GSTIN verification implementation and release gates

Local implementation only. No cloud resource, migration, production traffic, secret, or paid lookup was changed.

## Design and current capability
- Existing `profiles.validate_gstin` format/checksum logic is unchanged.
- Manual mode is the default. The official portal link is navigation only; it never writes verification evidence.
- `taxpayer_provider.py` defines a strict normalized provider contract and a code-reviewed adapter registry. **The registry is intentionally empty: no approved provider/account/API contract has been supplied. Live verification is not operational yet.** Do not configure a generic URL or assume vendors share an API schema.
- Future reviewed adapters receive credentials from Secret Manager, enforce a 10-second network timeout, bound response size, disable redirects and automatic paid retries, validate provider GSTIN identity, and translate provider errors to safe codes. No scraping, CAPTCHA bypass, or browser-supplied endpoints.
- Append-only verification evidence records pending/terminal states, actor, selected client, provider, profile fingerprint, time and normalized outcome. No raw payload or credentials are retained.
- Evidence freshness is 24 hours, an application review policy rather than a statutory validity claim. GSTIN, legal/trade name, address, registration type or state changes make evidence stale. Comparisons are conservative case/whitespace-normalized exact comparisons; unknown fields are not inferred.
- Fresh terminal evidence is reused. A guarded BigQuery transaction enforces a 60-second cooldown and five attempts per client/hour. Interrupted pending attempts become failed in presentation after two minutes. No automatic retries. The guard serializes first writes across instances; measure contention before release.
- Legacy `gstin_verified` is never set by this feature. Provider evidence does not establish ownership/KYC or loosen existing financial gates. Supplier lookup is not exposed and cannot modify client evidence.

## Routes and permissions
GET `/api/businesses/current/gstin-verification` loads evidence for the active authorized membership. POST `/api/businesses/current/verify-gstin` requires existing edit-profile permission and uses only the saved GSTIN. POST rejects request bodies/query parameters, including alternate client IDs or supplier GSTINs. Existing application authentication, session, same-origin and CSRF middleware remain in force. Synthetic clients cannot invoke live lookup.

## Configuration and Secret Manager
Defaults: `GST_VERIFICATION_MODE=manual`, `GST_VERIFICATION_LIVE_ENABLED=false`, `GST_VERIFICATION_STORAGE_ENABLED=false`. Other modes: `gsp` or unavailable. GSP availability requires all gates, a registered approved adapter, and accessible credentials.
After provider approval, install optional dependency `.[gst-verification]`. Set `GST_VERIFICATION_PROVIDER` to the reviewed adapter identifier and `GST_VERIFICATION_SECRET_VERSION` to `projects/PROJECT/secrets/NAME/versions/NUMBER`. Use a pinned numeric version, never secret material in source, logs, browser settings or API responses. Grant the Cloud Run service identity Secret Manager Secret Accessor only on that secret. Secret read timeout is five seconds; failures disable availability. Do not enable live calls until owner approval covers provider terms, consent and costs.

## Database migration plan
Review `migrations/017_gst_taxpayer_verification.sql` against the actual project/dataset before execution. It creates the partitioned, client-clustered evidence table and a single transaction-guard row; it does not alter customer records. Run this migration separately after review; do not run historical seed/migration scripts. Then verify table location, partition filters, guard cardinality and service IAM with an isolated test tenant before setting storage enabled. Do not set automatic table expiry without approved retention policy. The UI reads the latest attempt within 366 days; older evidence is retained but not presented as a recent check.

## Files
Backend: `app/config.py`, `app/services/gst/account.py`, `taxpayer_provider.py`, `taxpayer_verification.py`, `taxpayer_routes.py`, and optional dependency in `pyproject.toml`.
Frontend: `settings/gstin-verification.tsx`, `company-checks.tsx`, `account-form.tsx`, `onboarding-form.tsx`.
Tests: `tests/gst/test_taxpayer_verification.py`, `tests/frontend/gstin-verification.spec.ts`, manual-only route in the local browser harness.

## Acceptance and operational limits
Automated tests use fake providers, mocked Secret Manager where applicable, and isolated synthetic browser fixtures. They do not prove a vendor's production contract, BigQuery migration execution, real credentials or paid end-to-end verification. Required before live acceptance: choose approved provider; implement/review its documented adapter; sandbox contract tests; apply reviewed migration; test distributed concurrency against actual BigQuery; verify credentials, costs and timeout behavior; record owner/accountant acceptance. Monitor safe state/error-code counts, pending age, lookup latency, storage errors, rate limits and provider spend; do not log raw provider responses.

## Rollback
Disable `GST_VERIFICATION_LIVE_ENABLED` first and set mode to manual. Disable storage reads only if history queries fail. Preserve append-only evidence and guard tables; do not drop or purge them. Revert only this feature's changeset if necessary, preserving other local work. Registration/profile editing/checksum validation continue without the integration. No customer financial records or verified flags require rollback.

## References
GSTN GSP ecosystem: https://www.gstn.org.in/gsp-ecosystem
Google Secret Manager access: https://docs.cloud.google.com/secret-manager/docs/access-secret-version

## Local test evidence (17 October 2026)
- 67 backend tests passed: provider outcomes, checksum rejection, timeouts/rate limits, stale and in-flight profile changes, cached repeated lookup, Secret Manager failure, denied membership, wrong-client/supplier input, audited parameterized store queries, profile validation and existing navigation permissions.
- 33 Playwright tests passed: manual status, simulated provider states, rate-limit error, business switch/viewer restrictions, existing profile/onboarding/recovery/navigation flows.
- Ruff passed across app/tests. Focused mypy passed for all three new backend modules. Next production build (including TypeScript) passed.
- Native Python tests required execution outside the sandbox because of blocked native libraries; warnings were existing dependency deprecations and pytest cache permissions.
- All provider/Secret Manager tests are simulated. Database transaction SQL is inspected by tests, not executed against cloud BigQuery. Migration, live provider contract, credentials, IAM and concurrent cloud writes remain unverified release gates.
- Screenshots: `../artifacts/gst_easy/gstin-manual-desktop.png`, `gstin-manual-mobile.png`, `gstin-mismatch.png` (synthetic provider only).
