# GST Easy V3 assistant release and diagnostics

Release date: 29 October 2026. Status: live, verified on the main V3 URL.

Application: https://gst-easy-v3-web-foovqasysa-el.a.run.app/assistant?period=2026-10

## Deployed source and resources

- Branch: GST_NEW_V3.
- Application commit: `02383640a28b21609cea76beb335da21cbd99ed1`.
- Successful release build: `9680e5bd-93e1-43fb-857d-a3cee6ed8108`.
- API: `gst-easy-v3-api-00019-tid`, 100% main traffic.
- Web: `gst-easy-v3-web-00019-bay`, 100% main traffic.
- Web BACKEND_URL points to the canonical V3 API, with its matching OIDC audience.
- API image digest: `sha256:a95e22eea08ee7c81ce879806c62a7a5c85ef594173016eec7b6b3bac4e4e2a0`.
- Web image digest: `sha256:efb41e05171ba9c432276748bc4ec72921c966515ca3d02f890a5d1453678e61`.
- Additive table: `aidirac-503309.gst_easy_v3_finance_analytics.assistant_history`.
- Migration job: `7cd8dac7-e7bf-4257-95ad-002d89a2d7a9`; asia-south1; 90-day retention.

The application commit was pushed before building its exact Git archive. Later
diagnostic/report changes do not change app/frontend runtime source. Existing
untracked user-guide files were preserved and excluded from the release archive.

## Delivered behavior

120 public scenario templates, 29 wording aliases and 31 progressive portal topics
cover common GST/application questions. Financial amounts come from the scoped
backend summary. Ambiguous questions request clarification. Unusual supported
financial questions retain the bounded Gemini path.

Recently asked is scoped by authenticated user, selected business and period.
Saved answers survive sign-in and are explicitly historical. Pagination, new
conversations and own-history clearing are implemented. Browser-supplied history
cannot override another user's context. No shared personal-answer cache exists.

The existing assistant layout remains, with a collapsible history section. A live
candidate test found mobile overflow for long saved questions. The release adds
scoped wrapping rules. Local regressions also found a hydration effect that could
clear the first typed question; scope remounting now initializes state without that
reset. Both fixes are included in the deployed application commit.

## Actual test results

| Validation | Result |
|---|---|
| Broad backend regression | 883 passed; 27 existing skips |
| Final focused assistant/privacy/CSRF suite | 231 passed |
| Ruff / mypy / frontend TypeScript | Passed |
| Local Next.js production build | Passed |
| Cloud API and web image build | SUCCESS |
| Three assistant browser tests, repeated twice | 6 passed |
| Corrected candidate template/portal sequence | 26/26 HTTP 200, no degraded answers, history saved |
| Main V3 template/portal sequence | 11/11 HTTP 200, no degraded answers, history saved |
| Candidate functional/security groups | 15 passed |
| Main V3 functional/security groups | 16 passed |
| Final live Gemini probe | HTTP 200, non-degraded, history saved |
| Final live-revision HTTP 5xx log query | No matching entries in the 30-minute query window |

Live groups exercised sign-in, original evidence, history persistence across a new
sign-in, responsive actual UI, two-account history isolation, forged conversation
history, business switching, cross-business original denial, CSRF, test-export
restrictions, core pages, nine report APIs, invalid upload rejection, invoice-record
parity and unchanged financial totals. Three financial assistant answers (usable
ITC, cash requirement and sales GST liability) matched dashboard values.

Core page checks covered Business Profile, Account Settings, Bills & Vouchers,
Returns & Credit, Reports, Search and Help. Page-status checks do not certify every
possible action on those pages. No financial confirmation, filing, paid GSP call,
customer evidence mutation or unsolicited email was performed.

Unit/API privacy tests also cover different users within the same business, other
periods, revoked access, storage failures, pagination and scoped deletion. Those
tests use isolated repositories. Live privacy tests used the two existing synthetic
demo accounts and their authorized business memberships; no memberships were added.

## Timing and remaining limitations

The corrected candidate's 26 template/portal requests had median 3.276 seconds and
maximum 6.243 seconds. Main-URL samples had median 3.410 seconds and maximum 6.414
seconds. These are small functional samples, not load tests, guaranteed SLOs or a
controlled before/after comparison. They include persistence and authorization.

Gemini was intermittent during acceptance: an early grounded probe succeeded in
29.844 seconds, one later candidate request used the safe provider_unavailable
fallback, and a separate recovery attempt encountered a transport reset. The final
main-URL provider probe succeeded without fallback. This release does not establish
that every LLM request will succeed or meet a latency target. Provider failures
remain recoverable and do not disable deterministic template answers.

The 27 skipped backend scenarios remain unverified. Routing 120 questions is not
professional GST acceptance of every case. Specialist-form guidance directs users
to official instructions and needs case-specific professional review. No live
government submission is enabled. Real-customer global AI processing was not
authorized by this release; existing model-location restrictions remain intact.

## Deployment and preservation evidence

The initial Cloud Build submission could not read the shared default source
bucket. No bucket IAM was changed. The release used the existing V3-only build
bucket. The first successful build (`03a21a62-30b8-4611-b18e-4c4c17035c7c`) produced
an initial no-traffic candidate; its mobile failure prevented promotion. The
corrected build above was tested before the authorized main-URL promotion.

An acceptance-harness check was corrected to recognize the application's expected
error envelope for a blocked synthetic export; that restriction was not removed.
Diagnostic exception output was hardened to omit request/header dumps.

Saved before/after comparisons passed for `bills-voucher`, `bills-voucher-web`,
`gst-easy-v2-api` and `gst-easy-v2-web`: service specifications, traffic and IAM
unchanged. V3 IAM and all prior V3 revision tags were preserved. Apart from the
approved release revision/origin updates, critical V3 settings, identities,
secrets, resources, datasets and model configuration match the snapshot.
Both V3 queues were RUNNING. Existing build YAML files were unchanged.

Evidence directory: `artifacts/assistant-release-2026-10-29/`:

- `before.json`, `after.json`, `preservation.json`, `runtime-verification.json`
- `migration.json`, `build.json`, `api-candidate.json`, `web-main.json`
- `api-promotion.json`, `web-promotion.json`
- `diagnostics-candidate.json`, `diagnostics-live.json`
- `local-browser-tests.json`, `live-assistant-1440.png`, `live-assistant-390.png`
- Initial failed candidate evidence is retained separately.

Credentials were retrieved in memory from existing V3 Secret Manager references;
no plaintext credentials or browser storage-state files were committed.

## Rollback

If a regression requires rollback, route V3 API to `gst-easy-v3-api-00016-tuz` and
V3 web to `gst-easy-v3-web-00015-xih` using explicit revision allocations. Verify
the canonical pairing and auth. Preserve the additive history table and its
retention; do not delete user history or financial data. No V2 rollback is needed.
