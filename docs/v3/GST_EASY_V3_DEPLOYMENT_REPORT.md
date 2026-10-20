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
Authenticated live workflow acceptance remains blocked by email delivery.
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
