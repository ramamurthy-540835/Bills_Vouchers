# GST Easy preview deployment — 14 October 2026

Frontend: https://gst-easy---bills-voucher-web-foovqasysa-el.a.run.app

API: https://gst-easy---bills-voucher-foovqasysa-el.a.run.app

Deployed application source: `d7fc2cbe1a27b322cb490b82da28a9bf4c99ed12` on `GST_EASY`. Later commits add release evidence and operational scripts, not different deployed application code.

## Immutable builds and revisions

| Component | Cloud Build | Cloud Run revision | Image SHA-256 |
|---|---|---|---|
| API | f95320c2-add4-4191-90fe-94de7fb99886 | bills-voucher-00114-bel | 2a553b8246b910c747f0504b735e37cdac26f209ef62a6bcebef49aaa1ad3d98 |
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

SMTP host/user/password/sender and Twilio Verify service/API credentials are absent from runtime configuration. Thus registration verification, recovery delivery, invitations and mobile verification are not end-to-end operational. No delivery success was fabricated. Existing authorized accounts can use sign-in; authenticated live customer UAT has not been performed in this deployment check.

The shared compute runtime identity remains a least-privilege concern. Full credit-ledger functionality, accountant financial acceptance, verified official exports, full recovery/load/security evidence and genuine-client UAT remain open. This deployment is a review preview, not completion of all Phases 00–09.

## Rollback

Retain `artifacts/gst_easy/traffic-before.json` and `deployment.json`. Since production/previous previews were unchanged, they remain available. To withdraw this preview, remove only the two `gst-easy` tags; inspect current routing first and preserve every other tag/percentage. If replacing the preview, deploy approved immutable images with `--no-traffic` and recheck routing. Do not drop additive identity, audit, snapshot or financial tables, undo approvals, or purge GCS evidence during application rollback. Production promotion needs explicit authorization and acceptance evidence.
