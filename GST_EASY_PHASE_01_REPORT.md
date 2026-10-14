# Phase 01 implementation report — in progress

## Continued implementation and new evidence

The sections below describe the initial changeset; this section supersedes its older implementation gaps where noted. Acceptance remains open for live delivery and deployment.

- Email requests now enter auth_outbox. Registration creates its verification request in the same transaction as the isolated identity. Public recovery requests no longer look up account existence or call SMTP. OIDC-authenticated Cloud Tasks workers send messages; an authenticated repair endpoint can reschedule pending deliveries. Failed delivery retains the request for retry. Token values are derived with a domain-separated HMAC and are never stored in plaintext. Repeated worker deliveries use the same single-use link.
- Registration, email verification, password reset and mobile verification audit events are persisted transactionally. Password reset also queues a security notification atomically.
- Identity transactions now use their own auth_guard in the configured account dataset, removing their dependency on the canonical invoice guard.
- Mobile verification has a Twilio Verify adapter, account UI, local ten-minute expiry, per-user/number request limits, replay rejection and user/phone binding. Only an approved provider response can set mobile_verified. REQUIRE_OTP restricts unverified users to account/security actions. Credentials are absent; real SMS acceptance is pending. Provider behavior is based on https://www.twilio.com/docs/verify/api/verification-check and https://www.twilio.com/docs/verify/api/rate-limits-and-timeouts.
- Migration 010 now includes auth_guard, auth_events and auth_outbox; migration 011 adds mobile_challenges. Neither is applied to customer datasets. Queue and OIDC worker configuration are required before deploying the new account flow. Schedule /internal/auth/mail/repair with an authorized service identity for enqueue-failure recovery.
- Retained server-rendered password fields also receive an accessible eye control from app/static/password-input.js.
- Backend: 185 tests pass. Six browser scenarios pass, including provider-error/expired-code UI behavior. Production build passes. Gemini requests now use explicit SDK Content objects to avoid inconsistent mixed-list inference; fresh mypy passes for 63 source files.
- Real BigQuery integration tests passed in isolated dataset aidirac-503309.gst_easy_identity_test_271ff1f1be04 at 2026-10-14T10:34:30Z. Coverage: registration, isolated membership, concurrent duplicate insertion (one 201, one 409), verification, replay/expiry rejection, session revocation and distributed throttling. Tables expire after 24 hours. Source schemas were copied without source rows. Audit/reset transactions were optimized after real tests exposed the configured query-cost ceiling; the ceiling was not raised.
- Remaining delivery acceptance: approved sender mailbox, SMTP/queue/OIDC configuration, live email delivery, Twilio credentials/service and live SMS verification. Outbox worker database integration and mobile database/provider integration need additional evidence beyond mocked unit/browser tests. No provider account was purchased, real SMS sent, or unrelated project's secret payload read.

Date: 14 October 2026. Branch: GST_EASY. This changeset is not production-ready and does not satisfy all Phase 01 acceptance criteria.

## Implemented locally

- Required full name, email, mobile, country code (default +91), business name, password and confirmation. GSTIN is optional at registration; supplied values still undergo existing validation.
- E.164-shaped mobile storage with Indian mobile validation and mobile_verified=FALSE. Phone numbers are contact information, not an authorization or login key. Shared contact numbers are currently allowed; this duplicate-mobile policy needs product review before acceptance.
- Accessible shared password eye button for current Next.js login, registration, confirmation, change-password and reset-password fields. Keyboard toggling preserves the value, masking is default and autocomplete remains available.
- Password requirement feedback, server-side registration confirmation and explicit bcrypt UTF-8 byte/null validation. Passwords over 72 bytes no longer silently truncate; historical accounts using such passwords will need recovery.
- New registrants have email_verified=FALSE and receive no authenticated session. Login and current-user authorization reject explicitly unverified users. Historical NULL verification flags retain legacy behavior pending a reviewed legacy ownership migration policy.
- Configurable SMTP over verified STARTTLS for single-use email verification and password recovery links. No provider credentials or secret values are stored in source. Missing email configuration blocks registration before an account is created.
- Tokens use cryptographic randomness, persist only SHA-256 hashes, expire after 30 minutes and are consumed using the existing BigQuery transaction guard. Links carry tokens in the URL fragment; the browser removes the fragment and submits the token in a POST body.
- Password resets increment session_version and consume outstanding tokens of the same purpose. Requests for links return a common message for unknown and known accounts, including delivery errors.
- Distributed account/token rate counters use BigQuery transactions. Keys are hashed; counters include successful attempts. Avoid treating Next.js proxy peer addresses as distinct customer IPs.
- Legacy /signup POST returns 410; GET redirects to the isolated registration UI. Global-admin automatic signup has been removed.

## Changed files

Backend: app/config.py, app/main.py, app/routes.py, app/security.py, app/services/registration.py, app/services/auth_identity.py, app/services/identity_validation.py. Explicit Google Cloud imports in app/services/documents.py and app/services/tasks.py remove stale type ignores.

Frontend: frontend/app/password-input.tsx, identity-form.tsx, login/page.tsx, register/page.tsx, settings/account-form.tsx, forgot-password/page.tsx, reset-password/page.tsx, verify-email/page.tsx, gst-easy.css.

Tests: tests/test_auth_identity.py, tests/test_identity_validation.py, tests/test_security.py, tests/gst/test_registration_and_logos.py, tests/frontend/copy.spec.ts. Existing registration smoke scripts now include mobile and confirmation fields.

## API and migration requirements

POST /api/auth/register now requires mobile_number, country_code and confirm and returns verification_required rather than an authenticated workspace. POST /api/auth/request-link accepts email and purpose (verify/reset). POST /api/auth/verify-email accepts token. POST /api/auth/reset-password accepts token, password and confirm.

migrations/010_identity_verification.sql adds nullable users.email_verified and creates auth_tokens/auth_attempts. It has NOT been applied. Existing mobile columns from migration 009 and the canonical guard row must already exist. No new seed script was run.

Deployment must be coordinated: the new login rate limiter requires auth_attempts. Deploying code before the migration will break login. Review migration in an isolated dataset first, validate real transaction/replay/concurrency behavior, then configure AUTH_PUBLIC_URL, SMTP_HOST, SMTP_PORT, SMTP_SENDER and credentials through Secret Manager. Registration with unavailable mail after account creation can recover through resend; durable delivery outbox remains needed.

## Verification evidence

- Backend: 171 tests passed, including malformed Unicode/bcrypt bounds, mobile validation, unverified login rejection, disabled legacy signup, token hashing, reset-session SQL contract, token error handling and shared-rate-limit errors.
- Ruff passed. Fresh mypy --no-incremental passed for 61 source files.
- Next.js production build and TypeScript passed with the three new public auth pages.
- Four existing browser journeys passed. The new eye/recovery test initially matched Next.js's route announcer as a second alert; the assertion was scoped to the form, and the targeted rerun passed. Five scenarios passed across these runs.
- Token database tests currently inspect SQL contracts and mock database error outcomes. They are NOT proof of actual BigQuery replay/expiry/concurrency correctness. SMTP delivery has NOT been tested against a real provider. Browser recovery tests exercise input behavior, not real delivery.

## Remaining acceptance blockers

1. Real email sender configuration, delivery evidence and a durable asynchronous outbox; synchronous delivery timing currently differs between known and unknown account requests, despite identical public response text.
2. Approved provider-backed mobile OTP, expiry/retry/replay behavior, and real ownership confirmation. No code marks mobile_verified true.
3. Transactional authentication audit completeness and verified reset/security notification delivery.
4. Distributed throttling load/latency/cost measurements and trusted edge abuse controls; the current global transaction guard is a scalability bottleneck.
5. Review and test the duplicate-mobile and legacy-email ownership policies.
6. Actual migration execution in an isolated environment and concurrent registration/token-consumption integration tests.
7. Complete all customer/UI/backend acceptance journeys, including recovery email delivery through the deployed proxy.

## Preview impact and rollback

No new image was deployed, no cloud schema was changed and no preview or production traffic was moved. The currently deployed preview retains its previous behavior.

For a future preview: apply reviewed additive schema before compatible code, use isolated no-traffic revisions and run real delivery/tenant tests. Do not roll back to the old immediate-login registration implementation after accepting unverified identities: that older code does not enforce their verification flag. A safe rollback must preserve the new login/current-user verification boundary or disable login and registration temporarily while fixing the revision. Keep token/audit evidence under the reviewed retention policy; do not drop tables as an automatic rollback step.

Phases 02–09 remain pending; no accountant, genuine-client or production acceptance is claimed.
