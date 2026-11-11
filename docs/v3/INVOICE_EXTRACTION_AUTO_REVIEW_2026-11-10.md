# Invoice extraction agent, review and V3 release

10 November 2026. This implementation includes the pending authentication repairs. Deployment evidence will be recorded in a separate release report after live acceptance.

## Root causes

- A global AI allowlist blocked ordinary customer businesses, while all failures were described as unreadable bills. The owner explicitly authorized global customer invoice extraction on 10 November. The new server-side `GEMINI_CUSTOMER_EXTRACTION_GLOBAL_ENABLED` setting applies only to extraction. Assistant authorization is unchanged.
- One invalid response field could discard the whole extraction and create a blank financial record. Valid fields are now retained; absent/invalid fields are tagged in existing document flags and shown blank for checking. Responses with no usable evidence become retained processing exceptions rather than invented invoices.
- Failed extraction was cached and marked completed, preventing a useful retry. Retryable file failures now stay separate, retain their originals and can be retried without replaying successful files. Corrupt extraction caches are discarded only during an explicit retry.
- Date-filter differences could hide an uploaded invoice from the selected month. Upload metadata and a dedicated notice identify the actual invoice period without changing dates or financial classification.
- Failed register requests could look like a genuine empty register. They now show an error and a functional retry action.

## Restricted extraction agent

`InvoiceExtractionAgent` receives one selected original and business GSTIN context. It has no SQL, storage-listing, browsing, invoice-write, confirmation or filing tools. SDK automatic function calling is explicitly disabled. The authenticated API and background worker retain membership, selected-business, private evidence and filing-lock controls.

Global processing means the necessary invoice contents are transmitted to the configured Google Vertex AI endpoint under the owner's explicit authorization. A dedicated agent is not an independent privacy guarantee; security is enforced by the backend, restricted model interface, private storage, safe logs and access checks. Provider data-handling terms still apply. No claim of zero external processing is made.

Provider failures have safe categories (policy/configuration, rate limit, timeout, unusable response and missing evidence). Raw provider output, credentials and original contents are not included in user-facing exceptions. Transient provider calls have at most two attempts; policy/access denial is not retried. A failed file does not prevent later valid files from processing.

## Cooperation with Auto Review

| Situation | Result and next action |
|---|---|
| Extracted values complete; Auto Review OFF | Normal manual confirmation; arithmetic/GST validation remains active |
| Auto Review ON; every hard gate and current approved policy passes | Canonical auto-confirmation with versioned audit |
| Missing/invalid extracted values | Retain readable fields; highlight uncertain fields; block both automatic and manual confirmation until those fields are explicitly completed/reviewed |
| Source GST/total is wrong | Preserve source evidence; report deterministic differences; require authorized correction/review |
| Correct arithmetic, but no current approved GST policy | Manual review; no invented statutory approval |
| Manual edit or confirmation wins a race | Preserve the newer version; cancel the stale automatic/re-extraction write |
| Confirmed, rejected, actively reviewed or locked invoice | Re-extraction is denied; use the existing governed correction/reopening flow |
| Provider unavailable or document unreadable | Retain original as a processing exception; show cause, original link and retry where appropriate |
| Invoice date differs from selected month | Show where it was recorded and provide direct review access; never rewrite its date to fit the filter |

Re-reading a pending original requires membership/write permission and an explicit current If-Match version. Original evidence and prior canonical versions remain in the audit. It does not silently re-enable Auto Review. A human correction does not inflate the model's confidence; a reviewer can confirm after the required field checks and financial validation, or request another extraction.

## Verification

- Final pre-release backend run before the last empty-response guard: 971 passed, 27 existing skips; an additional focused empty-response/security suite passed 77 tests. Consolidated final totals are recorded in the release report.
- Full browser suite before the last parser-only guard: 99 passed.
- TypeScript, Next production build, Ruff and mypy passed.
- Real Vertex AI probe: one newly generated synthetic PDF, no customer documents, all 10 checked identity/tax-total fields matched independent expected values, no field issues, approximately 7.151 seconds. This used the existing operator identity, not the Cloud Run runtime identity. It is a single provider sample, not a reliability or accuracy guarantee.
- Local tests cover PNG/JPEG/PDF previews, structured CSV/XLSX processing, response normalization, retry isolation, private original access, stale updates, locks, injection attempts, Auto Review and explicit field resolution. Cloud candidate/live tests must be recorded separately.

Field-issue metadata uses the existing document_flags list; the persisted strict invoice schema receives no new JSON fields. This preserves old-reader compatibility. No destructive migration, live filing or change to tax-rate/ITC calculations is included. The existing requirement for professionally approved Auto Review rules remains.

## Deployment controls

Target branch GST_NEW_V3; targets gst-easy-v3-api and gst-easy-v3-web only. Use immutable images from the reviewed commit, no-traffic candidates, live synthetic acceptance, canonical API/web pairing and explicit promotion. The owner authorized the public V3 rollout after testing. Preserve V2/older configurations, traffic, IAM, storage and data. Preserve previous revisions for rollback; retain additive evidence/audit/history.

Existing blank records are not mass-overwritten. Authorized users can open a pending bill and choose Re-read original bill. Partial uncertain fields must be checked against the original; the system does not promise perfect extraction of every blurred, incomplete or ambiguous document.
