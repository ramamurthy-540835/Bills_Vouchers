# Local V3 follow-up — 21 October 2026

All changes remain local and uncommitted on GST_NEW_V3. No push, deployment,
Cloud Run operation, cloud-resource mutation or live-email test was performed.
Owner confirmation is required before a future push or release.

## Implemented and locally tested

### Bounded recovery after transaction contention

BillStore retries an explicitly aborted concurrent-update transaction at most
three times, with jittered backoff (total sleep at most 600ms). The complete SQL
transaction is replayed with identical tenant parameters, preserving optimistic
versions, worker fences, duplicate checks and filing locks. A lost worker or
newly frozen filing period still stops processing. Unknown commit outcomes,
timeouts, generic conflicts, business assertions and nontransaction writes are
never automatically replayed.

This addresses a recoverable contention path in job progress and financial
transactions. It does not eliminate global-guard contention, guarantee recovery
after process termination, or establish cloud throughput. Existing stale-worker
recovery remains necessary. No schema or global-lock changes were made.

### Month-specific dashboard profiles

Quarter/year calculations now load the applicable profile for each constituent
month instead of using the selected month's profile throughout. Independent
monthly calculations and the source-change check remain intact. The selected
profile remains the top-level display context. This correctness fix may add
profile lookups for ranges; it is not a claim of improved dashboard latency.

### Connector failure handling

Malformed non-object MCP SSE events return a safe ConnectorError instead of
an unhandled attribute error. Empty or unchanged continuation cursors are rejected
to prevent a non-advancing sync loop. Response chunks are checked against the
size budget before being appended to the accumulated buffer.

The adapter remains restricted to injected approved transports and synthetic
local tests. These fixes do not supply production OAuth, customer consent,
persistent sync jobs or live MCP interoperability certification.

## Executed verification

- Targeted transaction/dashboard/job recovery tests: 32 passed.
- Full backend suite after changes: **529 passed**, six existing deprecation warnings.
- Ruff app/tests: passed.
- mypy app: passed, 87 files.
- Git diff whitespace check: passed (Windows line-ending notices only).
- An initial new-test syntax error and subsequent response-type inference issue
  were corrected before the final passing checks.
- No frontend files changed. The preceding diagnostic pass's 79 browser tests,
  TypeScript and build results are historical baseline evidence, not rerun results
  for this follow-up. New behavior was tested locally with repository fakes and
  synthetic HTTP transport; no real BigQuery contention or cloud latency claim.

Logs: `artifacts/local-followup-2026-10-21/`.

## Remaining phases

1. Email: bounded operational repair now implemented locally; see
   `EMAIL_REPAIR_LOCAL_2026-10-21.md`. Its additive migration is unapplied.
   Provider event integration and inbox/recovery acceptance remain pending.
2. Performance: profile dashboard query costs and warm latency; do not add a
   tenant cache that can serve stale financial values without a consistency design.
3. Bulk intake: durable asynchronous large batches, safe canonical promotion,
   partial-failure recovery and compensation.
4. Corrections: replacement-evidence versioning, notifications and governed
   material-difference maker/checker policy.
5. Adjustments: persisted proposals, independent approval and immutable financial
   snapshots; legal treatment remains subject to professional review.
6. Connectors: connection management, credential broker, consent/revocation,
   persisted cursors and scheduled sync.
7. Compliance: effective-date legal rules, official schema validation and all
   50 professionally reviewed scenarios. Government submission remains disabled.
8. Release: review local diff, owner confirmation, then separately authorized
   push/deployment and live acceptance. No release step was executed here.
