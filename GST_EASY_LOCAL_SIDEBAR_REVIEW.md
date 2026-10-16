# Selected-business sidebar review ? 16 October 2026

Local changes only on GST_EASY. No commit, push, Cloud Run deployment, database migration or customer-data change.

## Changes

The existing dropdown business selector remains the switch control. After the membership-checked switch succeeds, it fetches the destination business account and effective permissions, verifies the returned client ID, and navigates to the current authorized module or GST dashboard. It preserves the period/range and removes stale invoice and module-specific query parameters. The full navigation remount reloads module data, profile and logo.

The dark-green sidebar now names the selected business. Desktop and mobile share the existing centralized permission configuration. Ordinary viewers retain read modules and lose editing controls. Reports uses server-derived view_reports, omitted for test businesses to mirror the existing backend export/report restriction. No per-business licensing database or arbitrary module entitlements were invented; businesses with equal permissions retain the same menu.

The switch endpoint now checks the active business list joined to active memberships, rejecting inactive as well as unrelated businesses. Server rendering refuses to merge module data with a different account client ID, and redirects unavailable module routes to the dashboard. Existing focus/30-second permission revalidation and backend authorization remain in force.

## Files changed for this task

- app/services/access.py ? selected-business report permission.
- app/services/gst/account.py ? pass selected client to permissions.
- app/services/gst/workbench.py ? active-business switch authorization.
- frontend/lib/navigation.ts ? report permission and authorized switch destination.
- frontend/app/account-menu.tsx ? preserve selector; resolve fresh context before navigating.
- frontend/app/workspace-server.tsx ? module guard and account/data context consistency.
- frontend/app/workspace.tsx ? selected-business sidebar label.
- tests/gst/browser_backend.py ? distinct synthetic profiles and correctly scoped bill stores.
- tests/test_navigation_permissions.py ? sample restriction and inactive/foreign switch rejection.
- tests/frontend/navigation.spec.ts ? profile/dashboard switching, same-permission menus, restricted reports, refresh, mobile and invoice isolation.

## Validation

186 backend tests passed (navigation permissions, platform access and tests/gst). Ruff passed. Clean mypy check passed for 75 source files. Next production build and its TypeScript checks passed with 29 routes. Initial sandbox Python imports were blocked; tests passed with approved access to installed native packages. A stale mypy cache was resolved with --no-incremental. Two new browser test issues were corrected: preserved date-range URL expectation and waiting for initial bill loading before upload.

Final full Playwright run: 28 tests passed in 41.2 seconds. Browser results are recorded in artifacts/v3/frontend-tests.json. Sanitized desktop/mobile role screenshots are in artifacts/gst_easy/local-rbac-*-desktop.png and local-rbac-*-mobile.png.

## Local review and limits

Open http://localhost:3100/api/local-preview on this computer. Use Account menu > Switch business to select Red Taxi, Synthetic Read Only or Synthetic Restricted Sample. All records are synthetic and in memory. This single-user fixture backend is not production authentication and must never be deployed. Real membership behavior is separately covered by backend tests. Live GCP, real-client acceptance and cloud AI delivery were not tested or changed.

Search and assistant retain their existing backend selected-client scoping; this task does not change retrieval or introduce new access grants. No schema changes are required.

## Rollback

Review and reverse only this task's hunks in the files listed above, preserving the earlier uncommitted RBAC work. Rebuild/restart the local frontend and fixture backend. Do not reset the working tree wholesale. No cloud rollback is needed because nothing was deployed.
