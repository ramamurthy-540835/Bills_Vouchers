# Preservation baseline

Read-only inspection captured 31 existing Cloud Run services before provisioning.
The sanitized baseline is `artifacts/gst_new_v3/preservation-before.json`.
It contains URLs, revision/image references, traffic, service identities,
nonsecret configuration and complete configuration/IAM SHA256 fingerprints.
Raw secret values were never included.

`scripts/audit_gst_new_v3.py` verifies every baseline service and IAM policy.
Provisioning ran this guard before adding V3 resources. New table schemas were
read from V2, but no records were copied. Existing SMTP credentials were read
into a new V3 secret without altering the original or its IAM.

New resources use gst-easy-v3 / gst_easy_v3 names. Existing V2 and older build
YAML files are unchanged. Final post-deployment comparison is still required;
the baseline alone is not proof of post-deployment preservation.
