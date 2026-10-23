# Test results ? 23 October 2026
Latest backend suite: 654 passed, 47 skipped, 7 warnings. Earlier run: 637 passed, 61 skipped. Final policy transaction change: targeted 15 passed. Ruff app/tests passed. Mypy app passed (91 files). TypeScript and the final Next production build passed.

Production browser suite: 88 passed, one ambiguous test selector failed. Corrected selector rerun: all four Auto Review tests passed. The earlier development-server run had seven failures and is not counted as a clean production result. Final UI refresh/upload regression rerun: 14 passed.

The supplied scenario list contains 108 IDs. 61 have partial deterministic contract tests; 47 explicitly skip because their specialized fixtures/implementation are missing. None has formal legal acceptance. Five combined fault combinations run inside one test. The complete requested 15 combined cases are not yet implemented.

Logs: artifacts/auto-review-v3/intelligence-pytest.log, intelligence-tests.xml, intelligence-browser-production.log, intelligence-build-final.log. A sandbox-only attempt failed collection due native dependency access; rerunning with approved dependency access produced the backend result above.

Live candidate, provider extraction evaluation, all advanced valuations, load tests and complete acceptance remain pending. No skipped test is counted as passed.

Status: implementation candidate; not a complete Auto Review 2.0 release. Local tests are not legal acceptance or live provider acceptance. V2 is excluded.

Live first candidate: login, default OFF, policy persistence, three existing manual exceptions, responsive views, two future CSV uploads (inherited ON and explicit OFF), exact original bytes, unchanged confirmed financial records, deterministic assistant and reset OFF passed. Repeated model questions exposed the persistent auth-throttle defect; that sequence failed and triggered a repair. Final results follow below.

Parallel workspace loading: TypeScript and production build passed; 32 navigation, business-switching, revocation, report and intelligence browser tests passed.

Final complete local production-browser run: 89 passed (1.9 minutes), after correcting the synthetic backend SQL dispatcher to distinguish batch insertion from the embedded policy-version assertion. The preceding 87-pass/2-failure run exposed that test-fixture mismatch; the real cloud batch had already executed successfully. Evidence: intelligence-browser-complete.log.

## Final live assistant sequence

25 requests completed; HTTP statuses: {200: 25}. Only 7 were generated answers. Evidence-only fallbacks: {'provider_unavailable': 12, 'provider_rate_limit': 6}. Median response time 40.877 seconds. No application 429 lockout occurred after the dedicated budget repair. Generated answers returned after fallback responses, demonstrating recovery, but provider availability is NOT accepted as reliable. A separate minimal synthetic Vertex request with a 45-second timeout also failed with ServerError 504 after 43.008 seconds. Do not attribute every failure to chat history or claim 25 successful AI answers. Evidence: artifacts/intelligence-v3/assistant-sequence.json and provider-diagnostic.json.

Final review found and repaired loss of explicit upload-OFF intent during later existing-bill selection. Two backend regressions verify explicit exclusion versus default manual upload. A new browser regression checks that default OFF omits the explicit exclusion parameter.

Release regression after exclusion persistence fix: 654 backend tests passed, 47 scenario skips; Ruff and mypy passed; TypeScript and production build passed; all 90 browser tests passed (2.8 minutes). See intelligence-pytest-final.log, intelligence-build-exclusion.log and intelligence-browser-release.log.
