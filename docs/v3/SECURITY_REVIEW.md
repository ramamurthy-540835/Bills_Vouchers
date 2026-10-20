# V3 security review

The branch preserves current session/CSRF, membership, canonical invoice
authorization, original evidence and filing locks. Correction routes reuse
object-level scope and require optimistic versions. Intake ignores no tenant
fields: unmapped fields are rejected, and SQL binds selected client.

V3 resources use new service identities, datasets, private buckets, queues and
secrets. Only schemas and serialization guards were provisioned; no V2 rows.
The API remains Cloud Run IAM protected. The web login can be public while all
application data remains authenticated. Worker OIDC is retained.

Connector adapters have no public configuration endpoint or default unrestricted
network transport. Production OAuth/egress is not claimed complete. Provider
content is untrusted input; no LLM may execute database writes or approvals.

Release gates: check source for secrets/customer evidence, compare all 31
existing service configurations and IAM hashes, inspect new runtime isolation,
verify private API denial, test CSRF/tenant/version/lock boundaries.
Formal penetration testing, credential-broker review and statutory acceptance
are still outstanding.
