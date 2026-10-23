# Test results ? 23 October 2026
Latest backend suite: 661 passed, 47 skipped, 7 warnings. The latest targeted Auto Review/assistant/scenario run: 126 passed, 47 skipped. Earlier run: 637 passed, 61 skipped. Ruff app/tests passed. Mypy app passed (91 files). TypeScript and the final Next production build passed.

Production browser suite: 88 passed, one ambiguous test selector failed. Corrected selector rerun: all four Auto Review tests passed. The earlier development-server run had seven failures and is not counted as a clean production result. Final UI refresh/upload regression rerun: 14 passed.

The supplied scenario list contains 108 IDs. 61 have partial deterministic contract tests; 47 explicitly skip because their specialized fixtures/implementation are missing. None has formal legal acceptance. Five combined fault combinations run inside one test. The complete requested 15 combined cases are not yet implemented.

Logs: artifacts/auto-review-v3/intelligence-pytest.log, intelligence-tests.xml, intelligence-browser-production.log, intelligence-build-final.log. A sandbox-only attempt failed collection due native dependency access; rerunning with approved dependency access produced the backend result above.

Live candidate, provider extraction evaluation, all advanced valuations, load tests and complete acceptance remain pending. No skipped test is counted as passed.

Status: implementation candidate; not a complete Auto Review 2.0 release. Local tests are not legal acceptance or live provider acceptance. V2 is excluded.

Live first candidate: login, default OFF, policy persistence, three existing manual exceptions, responsive views, two future CSV uploads (inherited ON and explicit OFF), exact original bytes, unchanged confirmed financial records, deterministic assistant and reset OFF passed. Repeated model questions exposed the persistent auth-throttle defect; that sequence failed and triggered a repair. Final results follow below.

Parallel workspace loading: TypeScript and production build passed; 32 navigation, business-switching, revocation, report and intelligence browser tests passed.

Final complete local production-browser run: 90 passed (2.8 minutes), after correcting the synthetic backend SQL dispatcher to distinguish batch insertion from the embedded policy-version assertion and adding the default-manual-upload exclusion regression. The preceding 87-pass/2-failure run exposed that test-fixture mismatch; the real cloud batch had already executed successfully. Evidence: intelligence-browser-release.log.

## Final live assistant sequence

25 requests completed; HTTP statuses: {200: 25}. Only 7 were generated answers. Evidence-only fallbacks: {'provider_unavailable': 12, 'provider_rate_limit': 6}. Median response time 40.877 seconds. No application 429 lockout occurred after the dedicated budget repair. Generated answers returned after fallback responses, demonstrating recovery, but provider availability is NOT accepted as reliable. A separate minimal synthetic Vertex request with a 45-second timeout also failed with ServerError 504 after 43.008 seconds. Do not attribute every failure to chat history or claim 25 successful AI answers. Evidence: artifacts/intelligence-v3/assistant-sequence.json and provider-diagnostic.json.

Final review found and repaired loss of explicit upload-OFF intent during later existing-bill selection. Two backend regressions verify explicit exclusion versus default manual upload. A new browser regression checks that default OFF omits the explicit exclusion parameter.

Release regression after exclusion persistence fix: 654 backend tests passed, 47 scenario skips; Ruff and mypy passed; TypeScript and production build passed; all 90 browser tests passed (2.8 minutes). See intelligence-pytest-final.log, intelligence-build-exclusion.log and intelligence-browser-release.log.

## Final candidate acceptance

Candidate source `7133d767b5af2a5a67d34c1b5ca47f3ab4ccd6c9` was tested at the tagged V3 Intelligence URL. The acceptance script passed all listed assertions: authorization/login, default OFF and persistence, existing-bill batch behavior, explicit per-invoice exclusion retention, responsive presentation, unchanged confirmed financial status, future ON and explicit OFF upload handling with retained original bytes, deterministic assistant evidence, and final policy reset to OFF. The final measured login was 8.840 seconds and Bills navigation was 14.843 seconds in this single acceptance run; these are observations, not performance SLOs. Evidence: `artifacts/auto-review-v3/intelligence-live-acceptance.json`.

## Local follow-up after candidate deployment

The scenario test module is now self-contained, so its fixtures no longer depend on pytest collection order. Auto Review rules also reject untraceable policy sources: a rule must identify a reviewable official HTTPS source, legal basis, source version and source-check date before it can authorize confirmation. This is a governance/evidence gate only; effective-period CA/legal review remains required. The assistant now answers four exact canonical-summary intents without a model and uses a bounded process-local provider circuit breaker for repeated unavailable/rate-limited calls. No Cloud Run candidate was rebuilt or promoted for this local follow-up.
