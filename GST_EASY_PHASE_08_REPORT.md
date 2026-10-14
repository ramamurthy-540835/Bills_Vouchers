# Phase 08 — Operations and security progress

Deployment tooling now builds on the existing services with new `gst-easy` tags, immutable successful image digests, no-traffic routing, preserved existing tags and routing assertions. Separate preview bill/identity queues prevent dispatch to old preview workers. Additive migrations are recorded with SHA-256 and BigQuery job IDs. Secrets are not included in reports; only configuration-presence checks are recorded.

Security evidence includes the automated permission, tenant, token, duplicate/concurrency and workflow checks described in GST_EASY_SECURITY_REPORT.md. BigQuery synthetic integrations exercise failure/conflict boundaries and retain 24-hour expiring test tables. This is not a complete disaster-recovery test.

Outstanding: replace the overprivileged shared compute runtime identity with reviewed least-privilege identities; measured load/latency/cost budgets; stale-job/uncertain-dispatch repair; full backups and restoration; retention acceptance; monitoring dashboards and delivered alerts; independent security review. These remain open even after a successful preview deployment.

Rollback uses saved traffic-before evidence and prior immutable image digests. Do not drop additive tables, audit history or retained evidence during application rollback. Production promotion requires separate explicit authorization.
