# Local navigation and access-control review

Scope: local working tree only, based on GST_EASY commit f4f6d69. No commit, Git push, Cloud Build, Cloud Run deployment, cloud configuration change or customer-data write was performed for this change. No database migration is required. No screenshot was attached to the implementation request; the current source and local synthetic UI were audited instead.

## Findings and before/after inventory

The original Next.js dropdown did not contain global user/configuration links. Its problems were unconditional Workspace access and placeholder Notifications links, mixed personal/business settings, and the absence of a shared permission-based menu definition. Existing legacy administrator endpoints already checked explicit platform access; their checks are retained and centralized with denial logging.

| Item / business purpose | Before | After and destination | Permission / API |
|---|---|---|---|
| GST dashboard | Fixed sidebar/mobile item | GST Easy Dashboard, /gst/workspace | view_workspace; canonical dashboard APIs |
| Invoice processing | Fixed Bills item | Bills & Vouchers, /bills | view_workspace; writes still require backend bill permissions |
| Returns and credit | Fixed sidebar/mobile item | Returns & Credit, /gst/filing | view_workspace; existing accountant/reviewer checks preserved |
| Reports | Functional fixed link | /reports, shared navigation configuration | view_reports; tenant-scoped report APIs; excluded for test businesses |
| Search / AI assistant | Functional fixed links | Retained /search and /assistant | view_workspace; existing scoped read-only retrieval |
| Personal profile | Mixed into account/business page | My Profile, /settings/me | manage_own_account; GET/POST /api/settings/account |
| Business profile | Client profile in dropdown | Business Profile, /settings/profile, also in sidebar/mobile | view_workspace; profile/logo writes require edit_profile |
| Account settings | Personal, password, business and access mixed | Account Settings, /settings/account, security and mobile verification | manage_own_account; existing verification APIs |
| Password change | Collapsed inside account page | Change Password, /settings/password | manage_own_account; POST /api/auth/password |
| Business onboarding | Always in dropdown | Business Profile link, /settings/onboarding | edit_profile; versioned profile API |
| Workspace access | Always in dropdown | Manage your business team link in Business Profile | manage_members, explicit active owner; members/invitations APIs |
| Customer creation | Form embedded in Business Profile | Separate /settings/customers form, linked from Business Profile | create_customer; POST /api/settings/customers; creator-owned tenant only |
| Notifications | Placeholder dashboard link | Omitted; old /settings/notifications redirects to help | No notification preferences fabricated |
| Help | No dedicated page | Help & Support, /help, usable workflow/security guidance | manage_own_account |
| Business switching | Dropdown when multiple clients | Retained authorized selector; reloads identity and permissions | Existing membership-checked /api/workspace/client |
| Logout | Existing sign-out action | Logout, closes dropdown and signs out | Existing CSRF-protected /api/auth/logout |
| Administration | Legacy backend tools; no Next.js admin workspace | Separate Administration group with /admin/workspace | platform_admin; new GET /api/admin/workspace and active tenant membership |

Client dropdown specification: My Profile, Business Profile, Account Settings, Change Password, Help & Support, then Logout. The business selector is shown only for multiple authorized memberships. No team, infrastructure, credential, global-user or placeholder-notification items appear here. My Profile and Account Settings have different responsibilities and routes.

Administrator specification: same personal account links plus a separate sidebar/mobile Workspace Administration entry. The new page lists only memberships and recent profile events for the selected authorized business. It is read-only and does not invent global infrastructure or maintenance tools. Existing backend GET /users, POST /users/{user_id}, GET /audit-logs and POST /settings/client[/create] remain protected and available at their existing backend routes; no broken Next.js links to those legacy HTML routes were added.

## Role and permission matrix

Roles remain client, tax_admin, viewer and separately provisioned platform admin; owner is the existing active membership access_role. No new persisted role system is introduced.

| Capability | Business owner | Other client member | Accountant / tax_admin | Viewer | Platform admin with membership |
|---|---|---|---|---|---|
| Read own authorized workspace | Yes | Yes | Yes | Yes | Yes |
| Edit own personal details/password | Yes | Yes | Yes | Yes | Yes |
| Edit business details/logo | Yes | Yes | Yes | No | Yes |
| Change GSTIN | Yes | No | Yes | No | Yes |
| Manage workspace invitations/members | Yes | No | No, unless owner | No | Only if also owner |
| Create a separate caller-owned customer | Yes | Yes | Yes | No | Yes |
| Read platform-admin workspace page/API | No | No | No | No | Yes |
| Access unrelated tenant data | No | No | No | No | No |

Existing invoice, reconciliation and return approval permissions remain authoritative; menu visibility is not a write grant. Separate administrator login still requires a configured allowlist, verified identity and active platform grant. A legacy role named admin never by itself grants platform access.

## Implementation and security boundaries

Backend navigation_permissions in app/services/access.py derives presentation capabilities from server-resolved identity and active ownership. /api/settings/account supplies these capabilities and email-verification status. Frontend lib/navigation.ts defines stable item IDs, labels, icons, routes, sections and required capabilities, with canAccessMenuItem, getVisibleNavigation and getVisibleAccountMenu. Both desktop and mobile use that definition; roles are not accepted from localStorage or URL parameters.

AccountPage guards owner/customer/onboarding/administrator routes before rendering their contents. The new administrative API independently checks platform access, then resolves an authorized active client and binds both queries to that client. Existing legacy administrator guards now use require_platform_admin and emit structured platform_access_denied security logs without passwords or tokens. Existing CSRF/session protections are unchanged.

Effective request and queued-worker roles now come from current active client_memberships instead of preferring a potentially stale client_user_role record. Membership removal and downgrade therefore cannot be bypassed by the old mirror role or global user role in the canonical workspace. The worker rechecks this before processing. No historical role rows were migrated or deleted. Before any later deployment, audit active membership/mirror-role differences; this change intentionally denies privileges supported only by a stale mirror.

Permissions refresh after hydration, on window focus and every 30 seconds while the page remains open. A changed role/selected membership reloads server-derived content; authentication/authorization failure clears the workspace. Backend checks remain effective on every request even before the UI refresh. Background refresh requests are marked only to avoid extending last_seen; idle expiry and all authentication checks still run. Permission identity uses the authorized navigation client, independently of synthetic demo record identifiers. Successful business switching uses the existing session endpoint and reloads the page.

Dropdown uses native details/summary and keyboard-operable links. Escape closes it and restores focus to the summary; outside pointer interaction, link selection and pathname changes close it. Viewer edit controls are omitted, not hidden with CSS. Missing-logo errors that occurred before hydration are also detected after hydration, avoiding a broken image and misleading Remove action.

My Profile shows name, immutable login email, mobile, verification states, current business, account role and password link. Personal saves do not include role fields. Existing mobile changes clear verification; the existing provider/OTP policy remains in force. Business Profile retains versioned storage, logo management, protected GSTIN editing, business type/state/preferences, and owner-only team access. The forced-password page also uses the existing accessible password-eye component.

## Changed files

Backend: app/services/access.py; app/services/gst/account.py; app/routes.py; app/routers/gst_bills.py.

Frontend: frontend/lib/navigation.ts; frontend/app/account-menu.tsx; frontend/app/workspace.tsx; frontend/app/workspace-server.tsx; frontend/app/login-form.tsx; frontend/proxy.ts; frontend/app/settings/{account-form,account-page,logo-upload}.tsx; frontend/app/settings/page.tsx; new frontend/app/settings/{me,password,customers}/page.tsx; new frontend/app/help/page.tsx; new frontend/app/admin/workspace/page.tsx.

Tests: tests/test_navigation_permissions.py; tests/test_platform_access.py; tests/gst/browser_backend.py; tests/frontend/navigation.spec.ts; tests/frontend/copy.spec.ts. The synthetic role-changing endpoints exist only in the local browser fixture and are not imported into production.

## Validation and artifacts

Backend: 354 tests passed; Ruff passed; mypy passed across 75 source files. Existing dependency deprecation warnings remain. An existing unwritable pytest cache produced warnings, so the final full run used -p no:cacheprovider. Initial new-test failures were corrected: the tenant-query naming now follows the repository's binding convention, and the test constructs fresh Request objects instead of mutating a cached URL.

Frontend: production build and its TypeScript checks passed with 29 routes. All 25 browser scenarios passed in the final local run (50.1 seconds). Browser tests use local synthetic identities and mocked cloud responses, not real users. Tests cover all four roles, owner-only navigation, direct page/API denial, password visibility, Escape/outside/link dismissal, refresh, business switching, role revocation, mobile overflow and existing invoice/reconciliation/return journeys. A revocation timing test exposed the pre-hydration event gap; the implementation now refreshes immediately on hydration. The onboarding mock was updated to return the complete account contract, including permissions, so background refresh sees the same identity as the server-rendered page.

Sanitized screenshots: artifacts/gst_easy/local-rbac-client-desktop.png and local-rbac-client-mobile.png; corresponding viewer, tax_admin and admin pairs use the same naming pattern. Browser result JSON: artifacts/v3/frontend-tests.json. No genuine customer evidence or passwords appear in these screenshots.

## Limitations and rollback

No cloud routing was inspected or altered, no cloud test records were created, and no live-user UAT was run under the user's local-only restriction. No production-readiness claim is made. The new admin page provides the implemented scoped read-only overview; it does not replace existing legacy administrative editors. Help is an implemented guide, not a fabricated ticket-submission service. Email change, actual provider delivery, SMS acceptance and broader GST release gates remain as previously documented.

Changes remain uncommitted in the working tree for review. To withdraw them, review the diff against f4f6d69 and reverse only this task's changes, preserving any subsequent work; do not reset the repository or purge evidence. There is no schema or cloud rollback to perform. Cloud Run continues serving the previously deployed customer-setup release until a separate deployment is authorized.
