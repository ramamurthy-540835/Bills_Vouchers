# Measured baseline
Read-only synthetic login/navigation against the previous V3 auto-review candidate, 23 October 2026, three fresh browser contexts:

| Metric | Samples, seconds | Median |
|---|---|---|
| Sign-in to workspace | 12.148, 10.681, 7.274 | 10.681 |
| Bills navigation | 21.152, 9.627, 9.922 | 9.922 |

Evidence: artifacts/auto-review-v3/intelligence-live-baseline.json. Three samples cannot establish p95/p99 or load SLOs. No login improvement is claimed from these measurements. Infrastructure concurrency/minimum instances have not been changed.

Status: implementation candidate; not a complete Auto Review 2.0 release. Local tests are not legal acceptance or live provider acceptance. V2 is excluded.
