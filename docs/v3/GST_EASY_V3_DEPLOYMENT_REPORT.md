# V3 deployment record

Target project aidirac-503309, region asia-south1, branch GST_NEW_V3.
Requested new services gst-easy-v3-api and gst-easy-v3-web did not exist during
the preservation audit.

Completed resource preparation: new V3 identities, isolated datasets with 62
copied table schemas and additive source-intake tables, private storage, queues,
artifact repository and independent session/mail secrets. No V2 customer or
financial records were copied.

Build and deployment are pending. No live V3 URL or successful build ID is
asserted at this stage. The guarded deployment script verifies the pushed source,
successful immutable image digests and preservation baseline before creation.

Rollback boundary: never route to or redeploy V2/older services. For a failed new
V3 release, stop further provisioning, preserve diagnostics and data, and use
only a separately reviewed V3 revision rollback. Do not delete datasets or
original evidence as rollback. Existing services remain outside the target set.
