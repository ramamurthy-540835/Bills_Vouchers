# V3 deployment record

Target project aidirac-503309, region asia-south1, branch GST_NEW_V3.
Requested new services gst-easy-v3-api and gst-easy-v3-web did not exist during
the preservation audit.

Completed resource preparation: new V3 identities, isolated datasets with 62
copied table schemas and additive source-intake tables, private storage, queues,
artifact repository and independent session/mail secrets. No V2 customer or
financial records were copied.

Initial deployment succeeded from b069a3e16e5f54ff163fe5d9e27afa8cade9f186.
Cloud Build c575e048-0feb-4ff6-83a5-bd6886b10913 succeeded.

- Frontend: https://gst-easy-v3-web-foovqasysa-el.a.run.app
- Private backend: https://gst-easy-v3-api-foovqasysa-el.a.run.app
- API revision: gst-easy-v3-api-00002-t5p
- Web revision: gst-easy-v3-web-00001-x27
- API digest: sha256:f3dfb37ab4037d88adbad37a0aefc22d497174cb71f122319e80538e0dbbe075
- Web digest: sha256:cfc9dc03687deb2d299e9285939ec72cfe39dbe18b6b04de2cf8ff5606cbcd86

Desktop/mobile login and registration pages returned 200 without page overflow.
Anonymous application identity access returned 401; direct private API access
returned 403. Runtime frontend/backend pairing and V3 dataset/storage prefixes
were checked. All 31 pre-existing service configuration and IAM hashes matched
the preservation baseline after deployment.

Actual registration of the authorized synthetic acceptance identity succeeded.
Email was provider-accepted but the user confirmed nonreceipt, including spam.
At that initial stage, authenticated live workflow acceptance was blocked by
email nonreceipt; see the later recipient acceptance below.
No bypass or manual email verification was performed.

Follow-up model isolation and mail trace changes require a separate reviewed
release; the initial deployment above does not prove those changes are live.
The guarded update script checks expected V3 revisions, pushed commit, successful
image digests, synthetic tenant provenance and the older-service baseline.

## Verified follow-up release

The follow-up was deployed from ed8a2c095b4116b02ab5a39f425d5320c62c71aa.
Cloud Build 917517d9-c284-484a-997b-96a31b24d881 succeeded.

- API revision: gst-easy-v3-api-00003-rdp
- Web revision: gst-easy-v3-web-00002-wqs
- API digest: sha256:7070b469a0c912debd4982df0d3e6923c1ef41cce86f0ff859837e03ba7ed065
- Web digest: sha256:eda26f5730353887670864aa95f54a24c2d791447b286aec1df39f316d4da510

The URLs above are unchanged. The global model is enabled only for the approved
synthetic acceptance client. Existing service/IAM preservation passed again at
10:56:25 UTC. The six live authentication-boundary checks passed after rollout.
The fresh email was still not received; this is not a completed onboarding release.

The first follow-up build submission was rejected because gcloud selected the
default staging bucket, which the V3 build identity cannot read. No IAM was
broadened. Retrying with the explicit V3 staging bucket succeeded. The exact
new temporary archive in the default bucket was checksum-verified and removed
by its generation; no pre-existing object was removed or overwritten. Future
builds must specify `--gcs-source-staging-dir=gs://aidirac-503309-gst-easy-v3-builds/source`.

Later documentation/test-only commits are not implied to be the deployed image.

Rollback boundary: never route to or redeploy V2/older services. For a failed new
V3 release, stop further provisioning, preserve diagnostics and data, and use
only a separately reviewed V3 revision rollback. Do not delete datasets or
original evidence as rollback. Existing services remain outside the target set.

## Source reconciliation release — 20 October 2026

- Pushed/deployed commit: `6f7c45f75934eeea43a80059372ab2e9c2301683`.
- Successful Cloud Build: `ee8bab5f-060e-408c-a5be-7591af01809d`.
- API revision: `gst-easy-v3-api-00004-9gv`.
- Web revision: `gst-easy-v3-web-00003-tx5`.
- API digest: `sha256:4ee7403baedab1dff687fed7cc65dc6a1ec652abac4c3e1484f33750f40987a8`.
- Web digest: `sha256:871074570307d8dca13908a1f8f04d11b9b80cc2d1624a1dbc4936214fec0da1`.
- Frontend remains https://gst-easy-v3-web-foovqasysa-el.a.run.app.
- Frontend/backend pairing and isolated V3 dataset/bucket identity were verified.
- All 31 pre-existing service configuration/IAM fingerprints matched after rollout.
- V2 branch remains `14df23a305826df0f5024ebd10705555045a9185`;
  existing/V2 build files are unchanged.

The V3-only source reconciliation audit table was created by job
`ff62c898-0020-43ef-a23c-739531aef9c5`. No existing financial tables were altered.
Real synthetic service tests retained original source bytes, rejected foreign
paths and left canonical invoice counts unchanged.

Eight live checks passed at 11:57:14 UTC: login/registration reached, anonymous
identity/source history/original access denied, CSRF-less writes denied and direct
API access without IAM denied. The first smoke expectation incorrectly required
401 for a write rejected earlier by CSRF middleware with 403; the test was
corrected to require the exact csrf_token error. No security logic was relaxed.
These are boundary checks, not full authenticated financial acceptance.

The owner separately confirmed delivery to their authorized Gmail recipient,
verified sign-in and dashboard access. Same-address mail nonreceipt remains
unexplained; password recovery and bounce/complaint acceptance remain pending.

The previous V3 revisions are API `gst-easy-v3-api-00003-rdp` and web
`gst-easy-v3-web-00002-wqs`. A reviewed rollback may target only those V3 revisions;
retain the additive audit table and all original evidence.
