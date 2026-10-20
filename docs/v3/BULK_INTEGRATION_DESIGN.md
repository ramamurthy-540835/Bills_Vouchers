# Multi-source intake

The new `/api/gst/bills/intake` routes reuse selected-business membership and
bill-write permission. CSV, XLSX and JSON are bounded to 10 MB and 10,000 rows;
expanded XLSX is capped at 50 MB. Explicit column mapping is available in the API.
The UI currently expects canonical column names.

Rows carry source identity/version, event type, references and Decimal text
amounts. Unknown fields are rejected rather than silently accepting tenant IDs.
Trip, payment and settlement events never implicitly create taxable invoices.
Preview quarantines malformed rows and identifies duplicate/conflicting source
identities. The original file is retained privately. Parameterized staging writes
are tenant-bound and serialized using the existing guard. Repeating the same
file/source/mapping returns the existing deterministic batch ID.

The batch and source-record tables are additive V3-only tables. History reads are
tenant-bound. Files retained before a failed transaction may be orphaned evidence;
no customer evidence is deleted to compensate.

Implemented: normalization, mapping API, preview, staging, history, source
provenance, within-batch duplicate/conflict detection and bounded inputs.
Cross-batch same/older versions are conservatively flagged duplicate_or_conflict.

Remaining: asynchronous large-job execution, detailed cross-source invoice
identity resolution, explicit canonical promotion/review, failed-row retries,
approved compensation and 100,000-row acceptance. Staging is not completion of
the requested financial consolidation workflow. No canonical financial totals
are changed by this intake.
