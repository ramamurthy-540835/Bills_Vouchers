# GST Easy preview deployment — 14 October 2026

Frontend: https://gst-easy---bills-voucher-web-foovqasysa-el.a.run.app

API: https://gst-easy---bills-voucher-foovqasysa-el.a.run.app

Current deployed application source: `3e261f05f4bc7461cb589c038df8819e6b710d5d` on `GST_EASY`. Canonical reporting is live alongside audited upload recovery, reconciliation review and client/platform administrator separation. Earlier details below remain historical evidence.

## Reporting release - 15 October, 13:29 UTC

- API build `3d02c10c-7fe6-4c0a-9d21-2611e28f153b`, revision `bills-voucher-00121-xef`, image SHA256 `46db9114006c639c36be790fb0de083186ed2ad8517b0be2ee16ccfdc16db766`.
- Web build `68e6acb0-0992-4c27-af93-ec9e39c76418`, revision `bills-voucher-web-00058-qar`, image SHA256 `6896c6d1622dd2b709c7c2a261757095e97c0e206df58bc0dcb6bb047d54ec9a`.
- Both immutable builds succeeded. Only the two `gst-easy` tags moved. Production percentages and every other tag were verified unchanged. SMTP/signing secrets retained; Twilio remains unconfigured. No schema migration or financial write is required.
- Seven report types, period filters and private CSV/Excel downloads are implemented; tax summaries also support PDF. See GST_EASY_PHASE_06_REPORT.md for scope and limitations.
- Full backend run: 295 passed; subsequent final report-focused run: 11 passed, including an additional independent-scenario case. Ruff, mypy (73 files), frontend production build and all 15 local browser journeys passed. Actual BigQuery reporting integration passed; synthetic PDF visually checked.
- Live health/readiness, public account pages, invalid-admin denial, unauthenticated reports/financial routes and worker denial passed. Desktop and 390px public browser checks passed. These checks did not create an account or prove authenticated customer UAT.
- Existing monitoring dashboard updated to these revisions; notification channels unchanged.
- Rollback: inspect current routing, then move only API `gst-easy` to `bills-voucher-00120-fun` and web `gst-easy` to `bills-voucher-web-00057-jud`. Preserve every other tag/percentage, secrets and evidence. No database rollback.

## Durable upload recovery release - 15 October, 12:48 UTC

- API build `51abab8c-8d29-4f26-befe-19c2207664eb`, revision `bills-voucher-00120-fun`, image SHA256 `4d3c349675d7533b5fb91e40c82832cab7daf851bca045a124c5d407191d6a2a`.
- Web build `9b3b5d66-bc99-4391-b3c9-c2b75319377f`, revision `bills-voucher-web-00057-jud`, image SHA256 `94abc4c47130983979b3029320e64bf49ea9b9038745af1921992ef837dbbe2f`.
- Successful immutable builds deployed only to `gst-easy`, with no production traffic. Before/after routing assertions confirm production percentages and every other tag are unchanged. Existing SMTP/signing-secret and administrator settings retained. No schema migration, historical job backfill, queue-policy change or IAM change.
- Worker claims, retry events and terminal progress are audited. Recovery after 35 minutes of inactivity applies to protocol-1 jobs; older unfenced in-flight jobs require review. Progress and invoice writes from superseded workers are rejected. Retried extraction preserves saved evidence, and filing locks are no longer mislabeled as duplicate invoices.
- 284 backend tests, Ruff, mypy (72 files), Next production build and 14 local browser journeys passed. Actual BigQuery integration passed in `gst_easy_bills_test_eb306dfe1e6b` at 12:33 UTC, including concurrent claims 200/409, stale retry, superseded progress/invoice write denial, completed no-op, retry-actor audit and tenant denial. Existing lifecycle/reconciliation/return checks also passed. The first integration run exposed an incomplete synthetic invoice fixture; after correction, the complete run passed. Tables expire after 24 hours.
- Live smoke passed at 12:48 UTC: healthy/ready API, public auth pages, invalid-admin denial, unauthorized financial endpoint/worker denial and expected registration validation. Desktop/mobile public browser checks passed. No account or email was created. Authenticated customer recovery and actual queue/GCS/Vertex failure injection remain pending.
- Existing monitoring dashboard updated in place to API `00120-fun` and web `00057-jud`; notification channels unchanged. Operator instructions and detailed rollback constraints: `GST_EASY_JOB_RECOVERY.md`.
- Previous paired preview revisions: API `bills-voucher-00119-dex`, web `bills-voucher-web-00056-zag`. Prefer a forward fix. Before rolling back to their unfenced worker code, stop new recovery requests and verify active deliveries have ended; review queue routing. Move only the `gst-easy` tags after that review, preserving all job/audit/object evidence and secret/admin configuration. Never reset historical jobs, drop evidence or promote production traffic as part of rollback.

## Reconciliation review release - 14 October, 14:00 UTC

- API build `9bcb45a1-f07b-4e5d-84e7-f6ed1d1340f0`, revision `bills-voucher-00119-dex`, image SHA256 `f04f4b6666a799c76bb4cc9ae216ad40500c0f747b79b77c4c63d632ea01fa94`.
- Web build `fee46a85-a31c-4535-b6f3-fcaa36773a48`, revision `bills-voucher-web-00056-zag`, image SHA256 `3d07552d5cc43e9508f5e97bbc04ec1fdf7d7450b2ecd96eafbf3ef24c5c61c3`.
- Both immutable builds succeeded. Only the `gst-easy` tags moved, with zero production traffic. Production percentages and all other preview tags were asserted unchanged. SMTP/signing-secret bindings and the separate administrator allowlist were retained.
- Additive migration 015 applied before deployment: job `5a8715f7-db4b-4106-9b91-d870a125ff90`. No financial backfill, evidence purge or historical seed scripts ran. New review history is retained in `ops.gst_reconciliation_review`.
- Validation: 272 backend tests; Ruff/mypy (71 files); production frontend build; 13 local browser journeys. Actual synthetic BigQuery integration passed concurrent review 200/409, tenant history isolation, stale evidence denial, immutable history, period locks, return invalidation and unchanged fingerprints for periods without reviews. Phase 04 report records the dataset and detailed scope.
- Live public/access smoke passed at 13:59 UTC: healthy/ready API, 401 for unauthenticated reconciliation/history/returns, 403 for unauthorized workers, and rejected invalid admin credentials. Registration returned expected mobile validation (422), proving the configuration gate is passed without creating an account or sending mail. Live desktop/mobile registration/password visibility and separate admin page checks passed at 14:00 UTC.
- Monitoring dashboard updated in place to the new revisions; notification channels unchanged. Actual authenticated customer review acceptance, mailbox delivery and accountant acceptance remain pending. Local browser evidence mocks comparison/history; its synthetic backend lacks the source-statement download fixture and logged prefetch errors. The passing browser suite is not proof of an original-GCS-download round trip.
- Rollback: verify current routing, then move only API `gst-easy` to `bills-voucher-00118-tad` and web `gst-easy` to `bills-voucher-web-00055-ceh`. Retain migration 015 and all review history. Earlier return code ignores review versions; prevent approval of affected snapshots until a reviewed mitigation or forward fix is in place. Preserve separate admin grants, client restrictions, SMTP and signing configuration. Never change production routing as part of this rollback.

## Access separation update — 14 October, 13:25 UTC

- API build `f2fc368a-a212-40c1-a71e-654ef806ccec`, revision `bills-voucher-00118-tad`, image SHA256 `99a6fa083544fbdcff99ede5632774f85869a1950171741596f8b51f3ce96a06`.
- Web build `9120bc71-d0f5-4a92-b193-e10d590ba8ca`, revision `bills-voucher-web-00055-ceh`, image SHA256 `3f1201ca1a4036997f73e638c6956739c7cbff719999a2841b78587d337a6fa6`.
- Successful immutable builds deployed only to `gst-easy`; production percentages and every other tag remained unchanged. SMTP/signing secrets retained. `PLATFORM_ADMIN_EMAILS=ai@aidirac.com` is configured.
- Migration 014 and audited account assignment completed: migration job `8b69cf10-1d74-4303-b7a3-89b8882df35b`, assignment job `f8677d9f-45d9-4989-9870-d2b96da7163e`. The client identity role was verified as `client` afterward. The administrator grant is separate from legacy identity roles. Both accounts' previous sessions were revoked. Identity-table changes apply across deployments sharing that database, although production traffic was not moved. Passwords, verification, memberships and business records were preserved.
- 254 backend tests passed, followed by 25 focused final checks and 10 access tests (including three additional missing-workspace-role cases). Ruff/mypy and the Next build passed. Twelve local browser journeys passed. Live desktop/mobile public browser checks passed; admin login rejected synthetic invalid credentials with 401, and normal registration reached validation rather than a configuration error. No real login credential was used or account/email created by these smoke checks.
- Existing monitoring dashboard refreshed to the new revisions. `GST_EASY_ACCESS_SEPARATION.md` records implementation, changed files and policy. Actual administrator mailbox verification is still pending; no verified state was fabricated.
- Prior revisions are API `bills-voucher-00117-ner` and web `bills-voucher-web-00054-mel`. Rolling application code back reintroduces legacy role inheritance; prefer disabling the admin allowlist/grant while preserving the client restriction. Never restore the client's global admin role, erase audit history or reinstate revoked sessions automatically.

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
