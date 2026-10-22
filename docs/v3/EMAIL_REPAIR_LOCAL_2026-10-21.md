# Bounded email repair — local implementation

Status: implemented and unit/regression tested locally; NOT deployed. No cloud
resources, queues, accounts or inboxes were accessed. No message was sent.

## Defect and correction

The previous repair path created an unnamed task on every invocation. Repeated
repair calls could restart queue retry cycles without a durable repair budget.

`app/services/auth_mail_repair.py` now reserves work in an additive
`auth_mail_repairs` table using the existing identity transaction guard. It:

- Permits at most three durable repair reservations per outbox ID.
- Waits ten minutes before initial repair and between accepted repair waves.
- Excludes accepted/sent, ignored, expired, actively leased and over-one-day-old
  requests. Unknown recipients remain handled by the existing worker.
- Reuses pending reservations after interruption instead of consuming a new one.
- Uses a stable hashed task name for each mail ID/attempt pair.
- Treats AlreadyExists as reconciliation of that same queue reservation.
- Leaves enqueue failures/unknown outcomes pending and continues other rows.
- Records queued status only after queue acceptance or AlreadyExists, without
  marking the message provider-accepted, delivered or the user verified.
- Limits reservation selection and processing to 50 rows per invocation.
- Keeps the existing authenticated/OIDC worker route and token lifecycle.

Queue execution retries remain governed separately by queue configuration. Three
repair reservations are not a promise of three SMTP calls. SMTP itself does not
provide exactly-once delivery: a lost response after acceptance can still leave an
ambiguous outcome. No claim of exactly-once mail delivery is made.

Google's task-name deduplication is temporary; the durable reservation table is
therefore retained rather than relying solely on queue tombstones:
[Cloud Tasks documentation](https://docs.cloud.google.com/tasks/docs/dual-overview).

## Migration and later release prerequisites

Prepared file: `migrations/v3_auth_mail_repairs.sql`.

1. Obtain owner authorization before any push, deployment or database operation.
2. Review and substitute PROJECT and V3_FINANCE placeholders with the isolated
   V3 configuration. Do not run the template unchanged or target older datasets.
3. Apply the additive table before releasing the updated repair endpoint.
4. Validate the transaction SQL and concurrent reservations against an authorized
   isolated database. Local tests inspect the SQL contract but do not execute BQ.
5. Verify queue attempt/backoff limits and perform an authorized test of enqueue
   failure, repair replay, delivery acceptance and actual inbox outcome.

No changes to positional auth_outbox inserts or historical migrations are needed.
Existing request IDs start with no repair reservations. Missing repair storage
fails closed with 503. Normal registration and original task scheduling do not
depend on the new table.

Rollback: suspend repair invocations while reverting the repair code if needed;
retain the additive table and budget history. Do not delete reservations to force
resends, mark users verified, or revert to unbounded repeated repair dispatch.
Explicit user-requested resend creates a new request under existing throttling.

## Local evidence

- Full backend suite: **537 passed**, six existing deprecation warnings.
- Ruff: passed.
- mypy: passed, 88 source files.
- New tests cover reservation SQL guards and bounds, stable task identities,
  AlreadyExists, unknown enqueue results, failure isolation, missing migration,
  concurrent-reservation failure and interrupted acceptance recording.
- Initial test setup required an explicit synthetic Cloud Tasks module because
  that SDK is unavailable in this local Python environment. Tests never loaded
  cloud credentials. This is not an SDK integration or live queue test.
- No frontend changes; no new frontend build/browser run was required for this
  backend-only increment.

Logs are in `artifacts/local-followup-2026-10-21/*-mail.log`.
Provider webhooks, bounce/complaint events, delivery tracing, actual recovery
inbox acceptance and the broader V3 phases remain pending.
