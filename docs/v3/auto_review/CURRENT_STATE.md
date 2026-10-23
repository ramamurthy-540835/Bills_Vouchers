# Audit — 23 October 2026

Baseline GST_NEW_V3: 82f7035. Remote fetched; no tracked modifications. Two
untracked user-guide files are preserved and excluded. V2 is out of scope.

Existing invoice opt-in, exact-cent tax checks, versioned audit policy, original
retention, durable Cloud Tasks jobs, duplicate/period guards and correction queues
exist. Business-level future/existing scope and aggregate exception UI do not.
Frontend uploads wait for extraction before submitting the next file. Assistant
history is already bounded to eight turns, but rate limiting rejects the ninth
request within a minute; provider errors are collapsed to a generic 503. This is
a reproducible failure path, not proof of the cause of every reported live error.
Extraction substitutes embedded PDF text for visual pages, losing conflict evidence.

Canonical line schema has no unit-price/discount/charge basis. Advanced valuation
cannot honestly be declared verified from existing taxable amounts alone. Approved
GST rules are not configured in the candidate; automatic confirmation remains
fail-closed. No model/rate/legal approval is inferred from historical handoffs.

Cloud baseline saved privately under artifacts/auto-review-v3/intelligence-services-before.json.
