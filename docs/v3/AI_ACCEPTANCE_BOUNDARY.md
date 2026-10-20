# V3 synthetic AI acceptance boundary

The owner authorized global inference for synthetic V3 tests only on
20 October 2026. Application services, BigQuery, GCS and queues stay in
asia-south1. Global inference does not carry an India-only residency guarantee.

The initial V3 runtime used Gemini 2.5 Flash. Google's model lifecycle page lists
20 October 2026 as its retirement date. Gemini 3.8 Flash is the selected follow-up
model, subject to actual project access and live execution.

Sources checked:
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/model-versions
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-8-flash

`GEMINI_LOCATION` is separate from the storage/application region.
`GEMINI_ALLOWED_CLIENT_IDS` must contain the single synthetic acceptance business
for this deployment. Global inference fails closed if the allowlist is absent.
Extraction and assistant calls check server-derived client identity before a
model client is created. Other businesses cannot invoke this model path.

The release script verifies the allowed business exists in the isolated V3
dataset, has is_test=true and SYNTHETIC_TEST_ONLY provenance. It does not grant
new memberships or accept a browser-supplied business override.

Extraction strips correction state, actor, reason and timestamp from model
output. Those are server-owned workflow fields, not document facts.

Passing adapter tests is not evidence of live extraction. Record actual model
availability, extraction and assistant results separately. Real customer
processing requires a separate residency/provider decision. Initial deployments
now default AI to disabled until this explicit configuration is applied.
