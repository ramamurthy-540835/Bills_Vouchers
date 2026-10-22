# Optional Auto Review candidate release — 22 October 2026

## V3 source and deployment

Branch: `GST_NEW_V3`. Runtime commit: `3a0b2270a1e1684c03da04668b3fd5cfffa556af`, pushed to GitHub.

Candidate login: https://auto-review---gst-easy-v3-web-foovqasysa-el.a.run.app/login

Cloud Build: `6b8a02bd-7158-4775-bb95-c280da9c8263`, SUCCESS.

| Component | Candidate revision | Immutable image digest |
| --- | --- | --- |
| API | gst-easy-v3-api-00008-xot | sha256:3c0a29eeb07cbe9358deda90b5b6095789d067c5e826bec826b0afccf540cddf |
| Web | gst-easy-v3-web-00007-fud | sha256:96682ba15e528d3a8dbb1a83af8d60578f5d355a0b3d75f3b5053f179b6fd5b8 |

Only the `auto-review` tags were updated, with no live traffic promotion. V3 API
`00006-g98` and web `00005-jbp` retain their existing live traffic. Candidate web
targets candidate API, using the base API service identity audience. Candidate
workers target the candidate API. No IAM or AI configuration changes were made.

## Compatibility defect and correction

The initial candidate stored a new nested policy in canonical invoice JSON.
Older live revisions reject unknown schema fields, making candidate-reviewed
invoices unreadable there. Policy is now stored separately in existing
`gst_bill_audit` entries under `auto_review_state`, atomically with invoice writes.
The canonical invoice retains its legacy shape. Changes made by an older revision
invalidate stale automatic decisions while retaining the user's opt-in.

One authorized synthetic V3 invoice was repaired by preserving policy in audit
and removing only the incompatible JSON field. Financial values, invoice version,
original evidence and previous audit records were unchanged. The repair is
restricted and idempotent. No customer financial records were used for testing.

## Executed verification

- Backend: 565 pytest tests passed. Ruff and mypy passed (89 source files).
- Frontend: TypeScript and production build passed; 84 local Playwright tests passed.
- Live candidate: login; default OFF; ON persisted through refresh; real Cloud
  Tasks processing; accurate manual exception reasons; desktop/mobile overflow
  check; authenticated original access; anonymous denial; policy reset OFF;
  unchanged invoice statuses; old live revision can still read the same invoice.
- Desktop/mobile screenshots inspected. Screenshots captured the original preview
  loading state; original file access was independently verified with HTTP 200.
- Full local tests cover positive automatic confirmation with explicit synthetic
  approved policies. Live automatic confirmation is **not accepted**: approved GST
  policies are unconfigured, so live bills safely require manual review.

Evidence is in ignored local `artifacts/auto-review-v3/`: `deployment.json`,
`preservation.json`, `candidate-live-results.json`, `compatibility-repair.json`,
`candidate-desktop.png`, `candidate-mobile.png`, and test logs. Build source is an
archive of the exact pushed commit, excluding secrets and customer documents.

## Authorized V2 follow-up

Owner separately authorized the same compatibility repair for V2. The V2 repair
is restricted to storage compatibility and its synthetic test record; V3-specific
correction workflow changes are not ported back. V2 source remains in its existing
worktree; only V3 commits were requested for GitHub push.

V2 build `69d93b69-879b-4601-bf4e-37d2f0b52f59` succeeded. API candidate is now
`gst-easy-v2-api-00016-poq`, image digest
`sha256:aab9c5160c0deab82c65dfc71f7ab8a5ad3b733ede62a4e60a02b8d669199ebd`.
The V2 web candidate is unchanged. All other services/configurations and V2 live
traffic were compared with a fresh pre-repair snapshot and preserved.

V2 verification: 456 pytest tests passed; Ruff passed; mypy passed (81 files)
after bypassing a stale incremental cache. An initial test collection failure
was resolved by using the installed shared test dependencies. No frontend source
changed for this repair, so previous frontend results were not relabeled as new runs.
Live checks passed for login, default OFF, persisted ON, real durable processing,
manual exceptions, original access, anonymous denial, responsive layout and
old-live readability. Both synthetic test invoices were returned to OFF, with
their financial status unchanged. One V2 synthetic metadata record was repaired,
preserving its version, finances, originals and prior audit history.

## Rollback and limitations

Ordinary live URLs still use their previous revisions. Stop candidate use or
remove only its `auto-review` tags to withdraw it without promoting any revision.
Do not restore the initial incompatible candidate. Retain additive rule/audit
storage and evidence; do not delete audit entries or revert repaired invoice JSON.

Candidates share their own version's existing datasets; they are not isolated
databases. No government verification, legal approval or external-provider success
is implied by synthetic tests. Batch exclusions operate per file; use individual
invoice opt-in for multiple records within one spreadsheet.
