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
YAML files are unchanged. Post-deployment comparison passed after initial
deployment and again after the V3 follow-up release at 10:56:25 UTC on
20 October 2026: all 31 pre-existing service configuration and IAM fingerprints
matched. The V2 remote branch remains
14df23a305826df0f5024ebd10705555045a9185.

A failed build attempt created a new temporary source archive in the default
Cloud Build staging bucket. That exact new object was checksum-verified and
removed by generation. No existing application object or bucket IAM changed.
The successful build uses only the new V3 staging bucket. Preservation evidence
does not claim that no temporary build object was ever created outside it.
