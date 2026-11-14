# GST Easy V4 Method A release status

Date: 14 November 2026
Branch: `GSTv4`
Baseline source: `925a753807083ec550c8f7feec2b7584f1ee9860`

## Implementation

- Added read-only return validation, maker-checker-approved guided preparation packages, private evidence upload, and customer-reported filing history.
- The packages are worksheets and internal evidence, **not GST Portal upload files**. GSTR-1 current portal schema compatibility and GSTR-3B import compatibility have not been established.
- Customer-reported acknowledgement references and uploaded proof remain unverified. No automated portal submission or payment is performed.
- Legacy internal draft generation is explicitly labeled as not a GSTN schema; its state machine cannot mark a return filed or locked from a manually entered ARN.
- Automatic GSTIN lookup routes are not exposed in the customer API. Future provider gates fail closed and have no mounted customer-facing routes.

## Verification evidence

| Check | Result |
|---|---|
| Full backend pytest suite | 1,023 passed, 27 skipped, 12 warnings |
| Focused Method A/API/authorization tests | 59 passed |
| Ruff (`app tests`) | Passed |
| mypy (`app`) | Passed, 100 source files |
| TypeScript (`tsc --noEmit`) | Passed |
| Focused GSTIN frontend test | 1 passed |
| Full production-mode Playwright suite | 102 passed, 0 failed, 0 skipped, 0 flaky (local synthetic backend) |
| Next.js production build | Passed on 14 November 2026 |
| Live V4 demo sign-in/workspace | Passed with latest V4 Secret Manager version; authenticated session and private bill context verified |
| Live Method A read-only checks | Passed: return status and validation both HTTP 200; portal export remains explicitly unsupported |
| Filing workflow UI and download navigation | 5 focused Playwright checks passed on a rebuilt local standalone web app; live Cloud Run logs exposed a Next.js prefetch defect subsequently fixed in source |

The initial browser run used an incorrect local setup and stale filing UI assertions. The synthetic test backend now enforces the same write-permission check, and the assertions match the Method A filing UI and safeguards. The final full run completed with 102/102 passing. Live sign-in used Secret Manager version `latest` (version 2); an earlier smoke harness reading version 1 returned an invalid-credential response. The V4 synthetic workspace was read-only for live acceptance; no financial records were changed.

During follow-up, a signed-in live page check initially sampled the Filing Centre before its own state request had completed. After waiting for the component to settle, live `GET /api/gst/returns?period=2026-11` rendered the draft status and synthetic-workspace guard correctly. Cloud Run logs also showed `GET /api/gst/bills/working-papers?...&_rsc=...` returning 422 because downloadable API endpoints were rendered as Next.js `Link` elements and prefetched as page routes. The GSTR-2B evidence download used the same pattern. Both were changed to native download links, with regression coverage ensuring no `_rsc` prefetch is issued. Five focused Playwright tests pass against a rebuilt standalone V4 frontend and local synthetic API. Deployment of this follow-up source change is recorded below once complete.

## Deployment status

Baseline service revisions captured before changes:

- API: `gst-easy-v4-api-00002-97d`
- Web: `gst-easy-v4-web-00001-4pj`
- Existing frontend URL: `https://gst-easy-v4-web-foovqasysa-el.a.run.app`
- Existing API URL: `https://gst-easy-v4-api-foovqasysa-el.a.run.app`

Cloud Build `89c1cbef-44e3-4190-adc6-c52c85d34891` succeeded from exact pushed `GSTv4` commit `e8dc70d069f66838729d0639f85ced7488084d00` using the isolated V4 source staging bucket.

- API image: `asia-south1-docker.pkg.dev/aidirac-503309/gst-easy-v4/api@sha256:8d95613f692777c67cc207714f27a5a354ad5ec3d5c873d2bdfc8812030697c0`.
- Web image: `asia-south1-docker.pkg.dev/aidirac-503309/gst-easy-v4/web@sha256:48cf6643e07b1f8d46732eca261d72e6303f4485fb4add1c8cc384cf7f5c327c`.
- Deployed API revision: `gst-easy-v4-api-00006-hin`, Ready, 100% traffic; web revision: `gst-easy-v4-web-00007-bim`, Ready, 100% traffic.
- Existing URLs remain `https://gst-easy-v4-api-foovqasysa-el.a.run.app` and `https://gst-easy-v4-web-foovqasysa-el.a.run.app`.
- Live smoke: `/login` and `/bills?period=2026-11` returned HTTP 200. The unauthenticated `/api/health` proxy returned expected JSON `401 Please log in`. Authenticated demo checks reached `/gst/workspace`, passed navigation/session/private bill context, and had no horizontal overflow at 1440px. Return status and read-only validation returned HTTP 200; validation correctly flagged unresolved pending/rejected invoices and the portal-schema warning.
- The Nature Labs 1 demo account and business are synthetic (`is_test=true`). Its package/evidence actions remain blocked by design; no financial data was changed. Secret Manager version 2 matches the stored password hash (checked in memory; neither value was printed or persisted).
- The read-only preservation audit passed after promotion for all six protected older/V2/V3 services, their traffic/configuration/IAM, remote V2/V3 branch refs, and existing project IAM grants.

The exact-head V4 revisions are live at 100% traffic. Signed-in workspace and read-only Method A acceptance passed. Full filing-package/evidence acceptance remains pending because synthetic tenants are prohibited from statutory filing actions; V2/V3 services and branches were not modified.

## Remaining release gates

1. A signed-in package/evidence test requires an authorized non-synthetic V4 test tenant. Do not disable the synthetic-workspace filing guard or relabel demo data.
2. Obtain the current GST Portal Returns Offline Tool/schema from an authorized source and professional GST review before implementing or labeling any export as portal-compatible. Current outputs remain guided worksheets; GSTR-3B remains online-entry guidance.
3. Keep the previous V4 revisions available for rollback; rollback targets are API `gst-easy-v4-api-00002-97d` and web `gst-easy-v4-web-00001-4pj`.
4. Never use customer-provided acknowledgement data as official filing verification.
