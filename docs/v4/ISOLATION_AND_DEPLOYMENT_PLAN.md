# V4 resource and permission plan

Discovered project: `aidirac-503309`. Existing GST services are in `asia-south1`. Neither proposed V4 service existed at the initial inventory. The original six V2/V3/older services, service IAM, revisions, traffic and protected Git branch SHAs were captured read-only before changes.

Source: `GST_NEW_V3`, commit `5656ed8caaf76abc1b859effe5368893ee4fb637`. This exact commit was verified on GitHub before creating the separate `GSTv4` worktree. Untracked V3 user-guide/test files remain untouched in their original worktree.

## New V4 resources only

- Cloud Run: `gst-easy-v4-api` and `gst-easy-v4-web`.
- Service accounts: `gst-easy-v4-api`, `gst-easy-v4-web`, `gst-easy-v4-build`.
- BigQuery: `gst_easy_v4_finance_analytics`, `gst_easy_v4_gold`, `gst_easy_v4_silver`, `gst_easy_v4_ops`. Copy current V3 table schemas only, never customer/account/financial rows. Initialize only required serialization guard rows. Any views must be reviewed and rewritten to V4 references or remain blocked.
- Private, uniform-access, public-access-prevention buckets: `aidirac-503309-gst-easy-v4-documents`, `aidirac-503309-gst-easy-v4-builds`.
- Artifact Registry: `gst-easy-v4`; immutable commit-specific API/frontend images.
- Cloud Tasks: `gst-easy-v4-bills` and `gst-easy-v4-auth`; no V3 consumers or schedules. Start with bounded dispatch and retries.
- Secrets: a new random V4 session key, a V4 SMTP credential secret, and V4-only test account credentials. No plaintext credentials enter Git, documentation or logs. Reusing the existing approved SMTP sender requires copying its credential into a new secret without modifying the original provider/account configuration.

## Approval boundary: shared project IAM

The master prompt explicitly requires approval before shared IAM changes. The following additive permissions are proposed **only for new V4 identities**; no existing principal's permissions are to be changed:

| New principal | Scope | Permission/role | Purpose |
|---|---|---|---|
| V4 API | Project | `roles/bigquery.jobUser` | Execute jobs; dataset access is separately restricted to new V4 datasets |
| V4 API | New project custom role `gstEasyV4Predictor` | `aiplatform.endpoints.predict` | Invoke the configured document model without broad Vertex administration |
| V4 build | Project | `roles/logging.logWriter` | Cloud Build logs |

All other grants are confined to newly created V4 resources: dataset writer, V4 document-bucket object access, V4 build-bucket read, V4 registry writer, V4 queue enqueuer, API self `serviceAccountUser` for task OIDC, V4 secret access, and V4 API invoker for V4 web/task identities. Existing project policy bindings must be captured first and preserved when these additions are made.

Google documents [generative-model access permissions](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/access-control) and the separation of [BigQuery job and dataset permissions](https://docs.cloud.google.com/bigquery/docs/access-control).

## Access and release

Initially deploy private V4 services. Test authenticated routing and worker OIDC. A public V4 **frontend login** is appropriate only after reviewing application authentication, CSRF and route authorization; the API remains IAM-protected, with application membership checks behind the frontend proxy. Only the new frontend's invoker policy may be made public. No URL redirects, custom domains, V2/V3 traffic changes or V2/V3 IAM changes are allowed.

Retrieve actual URLs after deployment. Configure the frontend, CORS, worker targets and email callbacks using those returned URLs. Do not invent hostnames. Build from a pushed, reviewed `GSTv4` commit and record exact source, build and image digests.

## Testing and acceptance

Trace all four workbook rows and four screenshots. Separate inherited V3 repairs from new V4 fixes. Establish a baseline before runtime tuning and compare the same isolated V4 workload before/after. Report sample count and avoid unsupported P95 claims. Keep local mocks, real storage/database tests, real model extraction and owner-confirmed inbox delivery separate.

Provision fresh synthetic V4 demo identities/businesses through existing application services. Existing V3 demo/customer records and credentials are not copied or modified. Financial fixtures use Decimal calculations and retained original evidence, normal validation, audited review and test-client filing restrictions.

Release remains BLOCKED wherever an approval, inbox confirmation, real-sample authorization or integration prerequisite is outstanding. No live filing is enabled.
