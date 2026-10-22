# V3 optional Auto Review

22 October 2026. Owner accepted the V2 candidate and requested integration and
push to `GST_NEW_V3`. This is a selective merge, not a replacement of V3 files.

## Behavior and preserved V3 features

- Invoice Auto Review defaults OFF, with backend policy/version/actor/time and
  audit persistence. OFF retains extraction and deterministic validation.
- Explicit opt-in plus Run Auto Review creates the existing durable, tenant-bound
  worker job. Stale versions, missing permission, locks, duplicate invoices,
  invalid arithmetic, missing evidence or unapproved GST policies prevent
  automatic confirmation. OFF does not undo a confirmed financial decision.
- Batch opt-in supports file-level exclusions. For several invoices inside one
  CSV/XLSX, leave batch OFF if row-level selection is required, then opt in each
  extracted bill. No global business preference is enabled.
- V3 rejection categories, correction queue, resubmission, source intake and GST
  comparison remain intact. Corrected/resubmitted bills require existing manual
  approval even if Auto Review is ON. A regression test covers this boundary.
- The frontend accepts same-service Cloud Run tagged backend URLs with their
  underlying service OIDC audience. Other-service/lookalike/insecure destinations
  remain denied; request origin checks remain enforced.

## Quality gates actually executed

- Backend pytest: **562 passed**, six existing deprecation warnings and one local
  pytest-cache permission warning. An initial sandbox DLL access failure was
  resolved by running with authorized installed-runtime access.
- Ruff: passed. mypy: passed, 89 files.
- TypeScript: passed.
- Next.js production build: passed (`--webpack` locally).
- Full local Playwright regression suite: **84 passed**, 1.9 minutes. Includes
  Auto Review, correction/resubmission, source intake, reports and permissions.
- No new legal/provider approval is inferred from local synthetic tests.

## Earlier local V3 work retained

The separately reviewed hardening changes cover bounded retries of explicitly
aborted BigQuery transactions, month-specific dashboard profiles, connector
response/cursor validation and bounded email-repair reservations. Their earlier
local reports remain historical records; this release authorization allows them
to be committed together with their tests and additive migration. Unrelated
untracked user-guide files are preserved and excluded from this feature commit.

## Release constraints

Use `scripts/release_v3_auto_review_candidate.py` to build the exact pushed commit
and deploy only `gst-easy-v3-api` and `gst-easy-v3-web` candidate tags. Existing
live traffic and V2/older deployments must remain unchanged. The build includes
only application/runtime files, excluding environment files and demo documents.

Apply reviewed additive migrations only to `gst_easy_v3_ops` and
`gst_easy_v3_finance_analytics`. Do not seed fabricated approved GST rules.
Unconfigured policies cause manual review. Email repair storage is additive;
this release does not claim new inbox/provider acceptance or trigger repair mail.

Record actual build, revision, URL and live checks in a separate deployment report
after execution. A candidate shares V3 data/storage; it is not a separate tenant
database. Live mutation tests must use only the authorized synthetic demo.
