# GST Easy preview deployment — 14 October 2026

Frontend: https://gst-easy---bills-voucher-web-foovqasysa-el.a.run.app

API: https://gst-easy---bills-voucher-foovqasysa-el.a.run.app

Current deployed application source: `13565e6996da5b3d243cc11085fff2f43f0360e0` on `GST_EASY`. The reconciliation update is live. Earlier deployment details below remain historical evidence.

## Reconciliation preview update — 14 October, 12:59 UTC

- API build `0aafbbd8-edd1-45a2-ace4-b2cb650d15d3`, revision `bills-voucher-00117-ner`, image SHA256 `02cc6305a0a3b0f70ddaab8ac115adebbbb306c5977df6dab73a71c9f840fe3b`.
- Web build `0832cb93-9acf-4ebe-bd3b-6bd331e3b764`, revision `bills-voucher-web-00054-mel`, image SHA256 `adfac3a60bc21e88273d39b66a94e00904eab58b69833d0a7214b2a23a254f20`.
- Both builds succeeded. Only the existing `gst-easy` tags moved; production and every other tag remained identical. SMTP and signing-secret bindings were retained.
- Added read-only two-sided reconciliation, source drilldowns, mobile filters/retry and XLSX evidence sheets. No database migrations or financial writes.
- 247 backend tests, Ruff, mypy (69 files), Next build and 11 local browser tests passed. The final blank-value export adjustment also passed all 12 permission/export tests. Live smoke passed, including 401 on unauthenticated reconciliation. Registration still passes mail readiness and rejects an empty form with normal 422 validation. No account or email was created by these probes; authenticated customer acceptance remains pending.
- Existing monitoring dashboard updated in place to these revisions using its current etag, following the [dashboard update API](https://docs.cloud.google.com/monitoring/api/ref_v3/rest/v1/projects.dashboards/patch). No notification channels changed.
- Rollback: after checking current routing, move only the API `gst-easy` tag to `bills-voucher-00116-poj` and web `gst-easy` to `bills-voucher-web-00053-kat`. Those are the pre-update revisions with working mail configuration. Do not change production routing, shared secrets or retained data.

## Previous immutable builds and revisions

| Component | Cloud Build | Cloud Run revision | Image SHA-256 |
|---|---|---|---|
| API | f95320c2-add4-4191-90fe-94de7fb99886 | bills-voucher-00116-poj | 2a553b8246b910c747f0504b735e37cdac26f209ef62a6bcebef49aaa1ad3d98 |
| Frontend | d666a574-b914-4a92-b44a-84a1cf59ce69 | bills-voucher-web-00053-kat | a7712c7f7d7152eadfa730cb2ef84a9051d095f9ddd08bb13fc5dc17ad3a5769 |

Both builds succeeded. Deployment used new `gst-easy` tags and zero production traffic. Existing tags and production routing were compared before/after and remained identical. Production remains 100% on `bills-voucher-redtaxi-account` and `bills-voucher-web-public-redtaxi-api`; preview-v3 still points to its previous revisions.

## Database and queues

Reviewed additive migrations 010–013 applied. The narrowly scoped owner-backfill candidate count was zero. Job IDs and migration hashes are in `artifacts/gst_easy/migrations.json`. No historical seed, invoice purge, payment or GST submission ran.

New queues: `gst-easy-bills` and `gst-easy-auth`, asia-south1, max two concurrent dispatches/two dispatches per second, ten attempts. Both target the new API preview. Existing queues were not altered.

## Verification

- 231 backend tests, Ruff and mypy passed; frontend production build passed.
- Ten local browser journeys passed. Selected delivery/workflow browser responses are mocked.
- Actual isolated BigQuery tests passed canonical save/delete/restore, concurrent restore, statement version/duplicate isolation, retry claim, stale return snapshots, approval freeze and reopen.
- Live public login, registration and password-recovery pages returned 200.
- Live `/health` and `/readyz` returned 200; readiness verified BigQuery and GCS connectivity.
- Unauthenticated bills/returns/membership access returned 401; unauthenticated internal worker access returned 403.
- Live desktop/390px registration fields and password show/hide passed; screenshots and JSON evidence are under `artifacts/gst_easy`.
- `/api/health` correctly requires authentication. `/healthz` returned an edge HTML 404; public smoke uses the working application `/health` plus `/readyz`. Do not configure a new probe against `/healthz` without investigating that edge behavior.

## Monitoring and open gates

[Preview monitoring dashboard](https://console.cloud.google.com/monitoring/dashboards/builder/156a57ed-0435-4575-8ff9-253faae16f1f?project=aidirac-503309) shows request rate and per-series p95 latency for the two new revisions. No alert recipients were changed. Dashboard implementation follows the [Cloud Monitoring dashboard API](https://docs.cloud.google.com/monitoring/dashboards/api-dashboard).

After the user selected `ai@aidirac.com`, SMTP was configured with `smtppro.zoho.in:587` and STARTTLS. Authentication succeeded against the existing `ZOHO_SMTP_PASSWORD:1` secret. Server settings follow [Zoho SMTP documentation](https://www.zoho.com/mail/help/imap-access.html); the domain MX records identify Zoho's India region. Secret values were never printed or committed. The first follow-up probe exposed a missing application signing-secret binding. Revision `00116-poj` also binds the existing `bills-voucher-app-secret:1`, validated to meet the worker's length requirement. Existing preview sessions may need a fresh sign-in.

At 12:24:19 UTC the registration request through the frontend passed mail/worker readiness and reached normal mobile-field validation (422 for an intentionally empty form). No test account was created and no message was sent; actual inbox arrival, verification, recovery and invitation delivery still require end-to-end acceptance. Twilio credentials remain absent. Operational evidence is in `artifacts/gst_easy/mail-configuration.json` and `registration-readiness.json`. Production and all other preview routes remain unchanged. The monitoring dashboard currently filters the original API revision `00114-bel`; its filter needs updating to track this configuration-only revision.

To roll back this configuration change, inspect current routing and move only the API `gst-easy` tag to `bills-voucher-00114-bel`. That restores the original missing-mail configuration and blocks registration again. Do not rotate/delete the shared secrets or change production routing as part of this rollback.

The shared compute runtime identity remains a least-privilege concern. Full credit-ledger functionality, accountant financial acceptance, verified official exports, full recovery/load/security evidence and genuine-client UAT remain open. This deployment is a review preview, not completion of all Phases 00–09.

## Rollback

Retain `artifacts/gst_easy/traffic-before.json` and `deployment.json`. Since production/previous previews were unchanged, they remain available. To withdraw this preview, remove only the two `gst-easy` tags; inspect current routing first and preserve every other tag/percentage. If replacing the preview, deploy approved immutable images with `--no-traffic` and recheck routing. Do not drop additive identity, audit, snapshot or financial tables, undo approvals, or purge GCS evidence during application rollback. Production promotion needs explicit authorization and acceptance evidence.
