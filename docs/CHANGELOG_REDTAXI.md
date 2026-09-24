# RedTaxi change log

## Phase 1 — Homepage control-plane rework

- Replaced the time-of-day greeting with the `Overview` title and active-client/GSTIN subtitle, with the unresolved-client fallback.
- Removed the overview marketing hero while preserving the existing sidebar document-queue control.
- Added the empty `exec-dashboard` section for the Phase 3 dashboard.
- Kept the existing upload, search, KPI, and latest-document controls unchanged.

## Phase 2 — Client account control (in progress)

- Added the additive SCD-2 `client_user_role` migration; existing memberships seed only as `client`.
- Added the Red Taxi account-logo asset. No user credential is stored in the repository.
- Added a Secret Manager environment-backed bootstrap path that creates the Red Taxi client, client membership, and client role without storing credentials in source.
