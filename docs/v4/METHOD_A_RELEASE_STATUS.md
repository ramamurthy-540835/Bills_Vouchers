# GST Easy V4 Method A release status

Date: 13 November 2026
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

The initial browser run used an incorrect local setup and stale filing UI assertions. The synthetic test backend now enforces the same write-permission check, and the assertions match the Method A filing UI and safeguards. The final full run completed with 102/102 passing. This is local UI coverage, not live customer account/API acceptance.

## Deployment status

Baseline service revisions captured before changes:

- API: `gst-easy-v4-api-00002-97d`
- Web: `gst-easy-v4-web-00001-4pj`
- Existing frontend URL: `https://gst-easy-v4-web-foovqasysa-el.a.run.app`
- Existing API URL: `https://gst-easy-v4-api-foovqasysa-el.a.run.app`

Cloud Build `cd9f814a-3221-4557-83c3-61087cf2c64c` succeeded from commit `c95b8d4d1b699d8efaf5349bd08cbecf39bd2a8f` using the isolated V4 source staging bucket.

- API candidate: `gst-easy-v4-api-00003-wiw`, digest `sha256:4cfb056c3929bd318e23014f3e1dfdf41a2fbe5d2045e98e7a946f1e00da8f6b`, Ready.
- Web candidate: `gst-easy-v4-web-00002-wam`, digest `sha256:75995d5ce495d069fc1ca949c948aa32fe48fbdd18cd4b0913388d637c4de2f6`, Ready.
- Candidate URLs: `https://method-a-candidate---gst-easy-v4-api-foovqasysa-el.a.run.app` and `https://method-a-candidate---gst-easy-v4-web-foovqasysa-el.a.run.app`.
- Candidate smoke: web `/login` returned HTTP 200. The protected API `/healthz` remains unverified: the current operator cannot impersonate the V4 web service account to mint the required audience-bound token, and no IAM grant was changed. Cloud Run reports the API container healthy and Ready.
- Traffic remains 100% on API `gst-easy-v4-api-00002-97d` and web `gst-easy-v4-web-00001-4pj`. The existing V4 URL is unchanged and still serves the pre-change revision.
- The read-only preservation audit passed for all six V2/V3/older services, branch refs, and existing project IAM grants.

The candidates have not been promoted to live traffic. The authenticated API smoke remains incomplete. V2/V3 services and branches were not modified.

## Remaining release gates

1. Push the updated browser harness and UI expectations to `GSTv4`, then rebuild from that exact pushed commit.
2. Complete a protected API smoke test through an authorized V4 service identity, without expanding IAM unnecessarily.
3. Verify the current portal schemas and obtain GST-professional review before labeling any export statutory or portal-compatible.
4. Promote V4 traffic only after the candidate API smoke and V4 functional smoke pass; keep the captured revisions available for rollback.
5. Never use customer-provided acknowledgement data as official filing verification.
