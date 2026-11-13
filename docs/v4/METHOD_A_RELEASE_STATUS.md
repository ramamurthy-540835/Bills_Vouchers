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
| Full Playwright suite | Not green: interrupted after 7/102; 2 passed, 5 failed |
| Next.js production build | Prior run passed; latest rerun blocked by `EBUSY` on `.next/standalone` while a Node process was running |

The browser failures included assistant-history/request timeouts, older Add Business expectations, and an Auto Review selector mismatch. These have not been established as caused by Method A. They remain unresolved acceptance failures and must not be represented as passed.

## Deployment status

Baseline service revisions captured before changes:

- API: `gst-easy-v4-api-00002-97d`
- Web: `gst-easy-v4-web-00001-4pj`
- Existing frontend URL: `https://gst-easy-v4-web-foovqasysa-el.a.run.app`
- Existing API URL: `https://gst-easy-v4-api-foovqasysa-el.a.run.app`

No new V4 revision has been deployed in this change set. Live traffic remains on the captured baseline until the browser acceptance failures and final build gate are resolved. V2/V3 services and branches were not modified in the local changes.

## Remaining release gates

1. Complete the Playwright suite and resolve or formally classify each failure.
2. Run the Next production build after the existing Node process releases `.next`.
3. Verify the current portal schemas and obtain GST-professional review before labeling any export statutory or portal-compatible.
4. Commit and push reviewed changes to `GSTv4`, then deploy/test a V4 candidate and preserve a rollback path.
5. Promote the V4 candidate only after live smoke tests pass; never use customer-provided acknowledgement data as official filing verification.
