# Phase 02 — Business onboarding and workspace access

Status: implemented and locally tested; preview and real email delivery acceptance remain pending. This report does not certify customer readiness.

## Changes

- Draft onboarding, completion validation, GSTIN/PAN/state consistency, versioned profiles and audit records in `app/services/gst/account.py` and `frontend/app/settings/onboarding-form.tsx`.
- Explicit owner memberships for self-registration. Owners invite accountants, tax administrators and viewers; acceptance requires the invited verified email, a valid single-use token and an active invitation. Revocation disables membership and current client roles. No ownership is inferred from GSTIN or email domain.
- Invitation mail uses the durable identity outbox. Missing provider configuration fails explicitly.
- Private logo replacement/removal archives prior objects, checks storage generation and records intent/completion audit events.
- New onboarding, workspace access and invitation acceptance pages; header logo refresh after changes.

## Migration and API

`migrations/012_workspace_onboarding.sql` adds onboarding completion, invitations and profile audit. Its owner backfill is restricted to self-registration profiles whose creator matches the existing active membership. Review before applying to customer datasets. It was applied only to an isolated synthetic BigQuery dataset.

New APIs: `/api/settings/members`, `/api/settings/members/{id}`, `/api/settings/invitations`, `/api/settings/invitations/{id}`, `/api/settings/invitations/accept`, and DELETE `/api/settings/profile/logo`. Existing profile and account APIs provide version/completion and owner information.

## Evidence

- Backend regression run: 204 passed before three additional invitation-revocation conflict cases.
- Ruff and mypy passed (65 source files); Next production build passed.
- Eight local Chromium journeys passed, including draft onboarding, error feedback, invitations/revocation, password controls and mobile layout.
- Actual BigQuery integration passed registration isolation, concurrent duplicate rejection, email token replay/expiry, reset session revocation, distributed throttling, onboarding versioning, email-bound invitation acceptance, invitation replay rejection, non-owner denial and membership revocation. Dataset: `aidirac-503309.gst_easy_identity_test_271ff1f1be04`, synthetic data only, 24-hour table expiration. Evidence: `artifacts/gst_easy/identity-integration.json` (2026-10-14 10:50 UTC).
- Browser invitation delivery was mocked; BigQuery integration replaced mail scheduling. These checks do not prove email delivery.

## Deployment, dependencies and rollback

No customer schema changes, Cloud Run revisions or traffic changes were performed. SMTP sender approval/configuration and real invitation delivery remain open. The new transactional invitation revocation guard has unit coverage; its SQL still needs a live integration run. Preview acceptance remains pending.

Deploy with migrations 010–012 and configured identity outbox worker. Roll back application revisions without deleting additive tables, profile history, membership audit or archived logos. Review any pending invitations and outbox records before disabling a deployed worker. Do not undo owner grants or financial records through an automatic destructive rollback.
