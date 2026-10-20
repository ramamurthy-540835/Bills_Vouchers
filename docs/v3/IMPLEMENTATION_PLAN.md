# V3 implementation plan

## Baseline and gates

- Source `14df23a305826df0f5024ebd10705555045a9185`; work only on GST_NEW_V3.
- Preserve local PDF guide. Preserve original/V2 services, data, queues and IAM.
- Capture sanitized configuration and full-configuration fingerprints before cloud
  creation. Refuse existing V3 names; prohibit old service targets in release scripts.
- Every implementation slice needs tests, actual outcome and a logical commit.

## Ordered work

1. **P0-A:** test email adapter/outbox edge cases, separate accepted/expired/ignored
   outcomes, add bounded safe diagnostics; verify real delivery only with approved inbox.
2. **P0-B:** add independent Decimal comparison contracts with explicit declared-rate
   provenance. Govern corrections with reason, version, evidence and approval; fail
   closed for unknown legal classification.
3. **P0-C:** tenant-scoped event staging, schema/identity policies, deduplication and
   quarantine; connect approved invoice records to the existing upload/review store.
4. **P0-D:** baseline arithmetic/API/queue metrics; optimize demonstrated bottlenecks.
   No fixed microsecond claim or costly large-load run without a budget.
5. **P0-E:** rejection codes, correction requests, resubmission and history using
   existing canonical statuses/audit/locks. Preserve financial exclusion until confirm.
6. **P0-F:** proposals and reviewer decisions for supported adjustments; official
   export/submission gated by legal/provider/schema verification.
7. **Connectors:** read-only REST and MCP adapters with approved destination/tool
   allowlists, audience/issuer validation and revocation; no arbitrary SQL.
8. **Compliance:** versioned registry and 50-scenario matrix. Each status distinguishes
   implemented arithmetic, legal review, official-schema tests and live acceptance.
9. **Release:** new `cloudbuild-gst-easy-v3.yaml`, isolated V3 resources, immutable
   images from pushed branch, private API/worker, deliberately public login frontend.
10. **Acceptance:** local full gates; authorized staging flows; provider results;
    preservation comparison; publish actual URL only after reachability checks.

External blockers are tracked separately so they do not prevent safe local work.
Unsupported capabilities stay hidden/disabled with an accurate explanation.
