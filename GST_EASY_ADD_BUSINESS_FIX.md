# Add Business local correction - 17 October 2026

## Observed root cause

The local Next.js instance at localhost:3100 forwards to the synthetic browser backend at localhost:8103. POST /api/settings/customers returned HTTP 404 with {"detail":"Not Found"}, both directly and through the proxy. The synthetic backend did not register this endpoint. Production source already registers it through app.services.gst.account.router in app/main.py; no duplicate production endpoint was introduced. Earlier creation browser coverage mocked this response and therefore missed the runtime gap.

A subsequent real local onboarding request exposed another test-adapter gap: missing repository settings used by BillStore when composing the profile transaction. The SQLite adapter now supplies that configuration and executes the production profile validation path. No live Cloud Run request or exception was used to establish this diagnosis; any cloud-specific failure remains unverified.

## Changes in this task

- app/services/customer_workspace.py: retain deterministic user/request business IDs, serialized transaction, owner membership, client role, original-user identity, unverified GSTIN and private storage marker. Add typed input validation, duplicate GSTIN assertion inside the transaction, immutable creation-audit payload comparisons for changed retries, and actionable conflict messages. An optional storage callback supports isolated tests; production still uses private GCS.
- app/services/gst/account.py: preserve selected session business after creation; use existing distributed throttle (five attempts per fifteen minutes per user key); structured failure logs with status and generated request reference. Existing backend authentication, CSRF and role enforcement remain.
- frontend/app/settings/customer-form.tsx: Business Legal Name, optional GSTIN/Website and Create Business labels; busy/ref lock; user-scoped sessionStorage retry identity; useful errors without dropping inputs; success panel; explicit Switch & Complete Onboarding; refreshed account dropdown; preserved period on switching.
- frontend/app/settings/account-page.tsx: pass trusted server-derived user ID to scope the retry key.
- tests/gst/local_businesses.py: isolated SQLite test adapter for durable synthetic business/profile rows and storage markers, with owner, retry, duplicate and profile-version checks. It does not execute BigQuery SQL or write GCS.
- tests/gst/browser_backend.py: register local creation/profile-save routes, use production validation/services with the isolated adapter, reload created profiles, and clear only synthetic fixture rows during test reset.
- tests/test_customer_workspace.py: input, transaction ordering, conflict, session preservation and rate-limit regressions.
- tests/frontend/add-business.spec.ts: non-mocked create/list/dropdown/switch/onboarding/save/refresh/dashboard flow, concurrent retry, duplicate GSTIN, invalid fields, denied access and mobile cancellation.
- tests/frontend/copy.spec.ts: align the existing retry/error test with the revised labels and explicit switching.

These files also contain earlier uncommitted work. Do not revert entire files to roll back this task.

## Actual validation

- 78 backend tests passed: test_customer_workspace, test_onboarding, test_company_profile, test_platform_access, test_security, gst/test_registration_and_logos.
- 22 browser tests passed across add-business, copy and business-profile. The three Add Business tests passed again after adding duplicate-GSTIN and refreshed-dropdown assertions.
- Ruff: app and tests passed.
- mypy: all 79 source files passed.
- TypeScript --noEmit and Next.js production build passed.
- git diff --check passed (line-ending notices only).
- Desktop 1440px and mobile 390px screenshots inspected. The mobile form is scrollable above the fixed navigation and controls remain usable; no horizontal overflow.

Screenshots (relative to this repository):
- ../artifacts/gst_easy/add-business-desktop.png
- ../artifacts/gst_easy/add-business-mobile.png

Initial test failures were resolved: an unsupported async pytest marker was replaced with asyncio.run, and the local profile repository configuration was supplied. Python native dependencies required running tests outside the sandbox. Existing deprecation and pytest-cache warnings remain; they did not fail the suites. The entire repository pytest/Playwright suites were not run.

## Storage, migration and security boundaries

No new production schema or migration is required by these changes. Creation continues using existing clients, client_memberships, client_user_role, gst_client_profile, profile_audit, auth_guard and auth_attempts structures. The guarded BigQuery transaction creates the business and membership together. Repeated identical user/request IDs reuse the same client ID. Duplicate GSTIN rejection does not grant access to another tenant. A valid checksum is never treated as government verification.

Private GCS marker creation precedes the transaction. If SQL fails, a marker containing only client ID/version may remain; retries safely reuse it. This is not a partially created financial business. No automatic object purge was added.

SQLite browser tests prove local UI integration and production service validation, not BigQuery transaction execution, IAM, GCS provisioning, distributed concurrency or real authentication. The synthetic backend remains a local, single-user test harness; never deploy it. Production authorization regression tests are separate from its test cookies.

## Deployment and remaining acceptance

Local only, following the standing explicit no-push/no-deploy restriction. No commits pushed, Cloud Run changes, migrations, paid API calls or real customer writes. Current cloud revision, BACKEND_URL, BigQuery schemas and IAM were not inspected or changed in this task. Cloud end-to-end acceptance remains pending authorization and an isolated real-backend test workspace.

Local review entry: http://localhost:3100/api/local-preview then Business Profile > Add Business. This establishes a synthetic test session; it is not real customer sign-in.

## Rollback

Revert only the task-specific hunks/new test files listed above, preserving earlier uncommitted work, then rebuild/restart the local frontend and test backend. No cloud routing rollback or database down-migration is needed because none was changed. Do not delete customer records, memberships, audit history or GCS evidence as a rollback action.
