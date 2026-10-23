# Existing-bill processing
Select the business and period, enable existing or both scope, then Run Auto Review. The server deduplicates eligible pending IDs and captures versions in a durable batch. Confirmed, rejected, sample, running and individually excluded invoices are skipped. Filing locks are checked before enqueue and at mutation.

The batch is bounded to 100 invoices. Repeat for remaining eligible bills. A conflicting active batch is rejected. Policy OFF/version changes cancel remaining work, and an atomic save fence handles cancellation racing with validation. Human edits and confirmation win stale-version conflicts. Completed entry retries do not repeat writes.

A worker crash after saving the opt-in but before persisting the entry outcome may cancel that entry on retry because its captured version is stale. This preserves financial safety but requires manual retry; exactly-once completion across that gap is not claimed.

Status: implementation candidate; not a complete Auto Review 2.0 release. Local tests are not legal acceptance or live provider acceptance. V2 is excluded.
