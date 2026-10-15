# Module status - 15 October 2026

This current summary supersedes the initial Phase 00 inventory. Implementation and automated evidence are distinct from real-customer acceptance; historical phase reports retain their original checkpoints.

| Module | Implemented and tested scope | Outstanding acceptance |
|---|---|---|
| Registration/login | Required mobile, password eyes, verification/recovery tokens, isolated registration, distributed throttling, durable email outbox, separate administrator sign-in | Actual mailbox/recovery delivery, SMS configuration and provider verification, load measurements |
| Business profile/logo | Saved onboarding, versioning, private logo management, invitations and revocation | Real invitation delivery, live storage evidence, customer role acceptance |
| Bills upload/review | Review/reject/delete/restore, durable history, audited worker claims/stale recovery, duplicates, Decimal summation and period locks | Live queue failure injection and recovery acceptance, live extraction and refresh evidence, retention approval |
| GST Easy dashboard | Canonical calculations and four independent cash scenarios | Accountant acceptance, full drilldowns/filter coverage |
| GSTR-2B reconciliation | B2B provenance/history, two-sided comparison, authorized append-only review decisions and stale evidence detection | Amendments/notes, broader sections, genuine evidence, financial exception policy |
| ITC ledger | Existing deterministic report calculations | Opening/utilization/reversal/reclaim/carry-forward ledger, line-level evidence and reviewed rules |
| Return workflow | Canonical immutable snapshots, maker-checker approvals, stale-source protection including review versions, period locks/reopen | Official schemas/validators and supported exports, accountant UAT |
| Search/assistant | Scoped canonical retrieval and read-only summaries with source references | Live Gemini/injection evidence, complete retrieval/report coverage |
| Notifications | Durable transactional outbox and configured SMTP | Actual recipient delivery and remaining workflow notification coverage |
| Desktop/mobile UI | 14 local browser journeys, 390px layout, failed-edit recovery and review/return refresh | Complete action inventory and genuine customer journeys |
| Tenant security | Automated access/concurrency tests and actual isolated BigQuery checks; explicit platform grants | Independent security review and full deployed authenticated UAT |
| Cloud operations | Immutable preview releases, isolated queues, routing preservation and monitoring dashboard | Least-privilege runtime identity, backups/restore, measured SLOs, delivered alerts |
| Real-client UAT | Public preview smoke checks only | Authorized genuine evidence, accountant and owner acceptance |

Latest automated checkpoint: 284 backend tests, Ruff, mypy (72 files), production frontend build and 14 browser tests pass. Actual BigQuery review and worker-recovery integration passed with synthetic expiring tables. See Phase 04 and deployment reports for exact scope and evidence. No phase is certified complete solely from source presence or passing tests.
