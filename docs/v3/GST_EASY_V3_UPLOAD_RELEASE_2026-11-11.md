# GST Easy V3 upload, extraction and sign-in release

Release date: 11 November 2026. Scope: GST_NEW_V3 only.

## Release identity

- Application commit: `5e213a1890f9adfdc8daf297c7b3122238a607bb`, pushed and remote SHA verified before building.
- Cloud Build: `449040af-98dc-46fa-aaa3-182dde2ef826`, SUCCESS. Source was a Git archive of that exact commit.
- API image digest: `sha256:d4875f4d25f4d5c61a2002537dd07777d4e875c7702ea9326bf1b34cdb8189c3`.
- Frontend image digest: `sha256:95bc8380c7c31685a8033f435d1e63825fce7e98d403566265275537a6fb9287`.
- Tested candidate API: `gst-easy-v3-api-00022-ciy`; candidate frontend: `gst-easy-v3-web-00021-saw`.
- Main API: `gst-easy-v3-api-00023-yob`; main frontend: `gst-easy-v3-web-00022-vot`, each serving 100% after the owner-authorized rollout.
- Public application: https://gst-easy-v3-web-foovqasysa-el.a.run.app
- Frontend backend target and upload-worker target both resolve to the canonical V3 API. Candidate upload workers were explicitly routed to the candidate, avoiding accidental testing on the older API.
- Runtime dataset `gst_easy_v3_finance_analytics`, canonical GST dataset prefix `gst_easy_v3_`, private document bucket `aidirac-503309-gst-easy-v3-documents` verified.

The final documentation/orchestration commit may follow the application commit. It does not change the deployed application image. Existing build configurations were not modified.

## Problems repaired

1. Global model access previously excluded ordinary customer businesses. Following explicit owner authorization, a server setting now allows global customer **invoice extraction**. Assistant access rules were not broadened.
2. A malformed extracted field could discard all readable values. Parsing now retains valid fields, records missing/invalid fields, displays uncertain fields blank, and blocks confirmation until reviewed.
3. Failed extraction could produce an empty financial record or an unusable cached result. Files without usable evidence now remain separate processing exceptions with private original access and appropriate retry.
4. Re-extraction of a pending invoice now uses an authenticated, version-checked job. Confirmed, locked, rejected or concurrently edited invoices are protected.
5. Selected-month differences now have a clear notice; original invoice dates are preserved. Failed register requests show a retryable error rather than a false empty register.
6. Login throttling now distinguishes failed attempts from successful sign-ins and handles contention safely. Login recovery preserves input, exposes verification resend and uses fresh session navigation.

The extraction agent is a stateless structured document reader without database, browser, storage-listing, invoice-write or confirmation tools. Necessary document contents are transmitted to the configured Vertex AI endpoint under the owner's authorization. The agent itself is not a guarantee of zero external processing.

## Verification evidence

Local results on the release implementation:

| Check | Actual outcome |
|---|---|
| Backend pytest | 975 passed, 27 existing skipped |
| Ruff, app/tests | Passed |
| mypy | Passed, 96 source files |
| TypeScript | Passed |
| Next.js production build | Passed |
| Full browser regression run | 99 passed before final parser-only guard |
| Final focused UI regression | 6 passed |

Actual candidate tests used a separate, verified synthetic diagnostic owner and business. No existing demo or customer invoices were changed. Candidate acceptance passed:

- PDF, PNG and JPEG extracted identity/tax totals matched independent fixture values; review inputs received those values.
- Original PDF bytes matched the source SHA-256; failed originals remained accessible through authenticated endpoints.
- Deliberately incorrect GST was retained as source data and flagged for review.
- Blank image produced a processing exception and no blank invoice.
- Future-upload Auto Review inherited the explicit business choice, then safely required manual review when approved policy evidence was absent.
- Renamed duplicate did not create another invoice.
- Supported synthetic B2B GSTR-2B JSON imported; confirmed purchases contributed to the dashboard; all nine report APIs returned their expected contracts.
- Desktop/mobile overflow checks passed; no browser JavaScript errors were recorded; confirmed-invoice re-extraction was denied.
- Both existing demo logins, 26 consecutive assistant guide/template questions, persisted history after new sign-in, cross-user/cross-business history isolation and private original authorization passed.
- Existing demo invoice records and financial totals were unchanged. Synthetic official-export protection remained enabled.

One pre-promotion canonical smoke check returned HTTP 403 because it reached the old API before the new candidate origin was active. API-first promotion resolved this; canonical login, correct business and bills-page checks then passed. No authorization bypass was introduced.

### Final public-URL acceptance

All three final public-URL suites passed:

- `acceptance-live.json`: PDF/PNG/JPEG source values matched, wrong GST flagged without rewriting the source, blank original retained as an extraction exception, duplicates prevented, original PDF SHA-256 matched, valid PDF confirmed through the normal endpoint, all nine report APIs returned valid contracts, real review inputs populated, fitted PDF preview loaded, full-original link used the same authorized source, confirmed re-extraction denied, desktop/mobile checks passed, zero browser JavaScript errors.
- `acceptance-structured.json`: CSV created two independently reviewable invoices; two XLSX rows grouped into one invoice with two lines. Exact expected invoice totals and original-file SHA-256 checks passed. All three records remained unconfirmed and did not change confirmed purchase totals.
- `diagnostics-live.json`: both demo logins, eleven consecutive guide/template questions, history persistence after a new sign-in, cross-user and business-switch isolation, authorized original access, cross-tenant denial, core pages, all nine reports, unchanged existing demo invoices/totals, invalid-file rejection and three financial answers matching dashboard data passed. The live open-ended provider probe returned a nondegraded answer; the candidate equivalent used the safe `provider_unavailable` fallback. These are distinct observations, not a claim that model availability is resolved universally.

One local Playwright TLS connection dropped during a live report read. The diagnostic resumed using saved job IDs, with no re-upload or duplicate financial records, and completed successfully. The failed attempt remains in the evidence. Only safe diagnostic GET transport retries were added; mutation requests were not blindly replayed.

After both phases and the spreadsheet check, the isolated test business contained eleven canonical records, including two confirmed PDF fixtures. Confirmed purchases were **INR 2,360.00**; usable-credit summary **INR 180.00** corresponded to the single supported synthetic B2B statement imported in the candidate phase. Other test invoices remained pending. These are synthetic diagnostic results, not customer balances or authoritative ITC eligibility findings.

Final before/after checks passed for `bills-voucher`, `bills-voucher-web`, `gst-easy-v2-api` and `gst-easy-v2-web`: configuration, traffic and IAM were unchanged. V3 API/web IAM also remained unchanged. No V2 or older data/storage/queue mutation was performed by this release.

A bounded Cloud Logging query for V3 HTTP 5xx responses from **08:24 UTC to the check at 09:21 UTC on 11 November** returned **zero records** (query limit 100). This observation covers that release window only; it is not a perpetual uptime guarantee.

Machine-readable evidence and sanitized synthetic screenshots are stored locally under `artifacts/v3-upload-release-2026-11-10/`; earlier local gates are under `artifacts/diagnostics-2026-11-09/`. These artifacts are not a source of production credentials. Evidence includes `preservation.json`, `runtime-verification.json`, `live-review-1440.png`, `live-review-390.png`, `live-exceptions-mobile.png` and the three public-URL JSON reports above.

## Security and boundaries

- Existing authentication, CSRF, membership checks, private originals, filing locks, version guards and deterministic financial validation remain active.
- No government filing, fabricated GST verification or professional policy approval was enabled.
- Test writes are limited to the isolated synthetic diagnostic business, including a supported synthetic GSTR-2B statement and confirmed test invoice. Existing demo accounts retain their financial records.
- The authorized Gmail registration test was received and verified by the owner on 10 November. This confirms that mailbox delivery sample; SMTP acceptance alone is not proof of universal delivery. Sender-domain DMARC/DKIM review remains mail-administrator work.

## Remaining limitations

- Automatic confirmation requires all hard gates and applicable professionally approved GST policy evidence. Correct arithmetic alone is insufficient; missing policy evidence routes to manual review.
- Open-ended assistant provider calls can still return `provider_unavailable`; the tested safe response remains available and history is persisted. Deterministic/template and grounded financial responses are tested separately.
- Twenty-seven specialized scenario tests remain skipped. This release does not claim complete legal, extraction or statutory coverage.
- Clear synthetic samples are not proof that every blurred, cropped, handwritten or ambiguous real bill will extract accurately. Uncertain fields must be checked against retained evidence.
- Current BigQuery-backed requests and serial background processing still take seconds; no subsecond or heavy-load performance guarantee is made.
- No mass rewrite of historical incomplete invoices was performed. Authorized reviewers can use **Re-read original bill** on eligible pending records.

## Rollback

Retain previous main revisions `gst-easy-v3-api-00019-tid` and `gst-easy-v3-web-00019-bay`. Roll back frontend traffic first, then API traffic, to those explicit revision IDs if required. Do not delete evidence, audit events or newly created synthetic records. Existing invoice JSON compatibility is preserved by storing field issues in the existing document-flags structure. Candidate tags remain available for outstanding candidate tasks. No V2 or older service is a rollback target.
