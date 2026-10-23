# Test results ? 23 October 2026
Latest backend suite: 652 passed, 47 skipped, 7 warnings. Earlier run: 637 passed, 61 skipped. Final policy transaction change: targeted 15 passed. Ruff app/tests passed. Mypy app passed (91 files). TypeScript and the final Next production build passed.

Production browser suite: 88 passed, one ambiguous test selector failed. Corrected selector rerun: all four Auto Review tests passed. The earlier development-server run had seven failures and is not counted as a clean production result. Final UI refresh/upload regression rerun: 14 passed.

The supplied scenario list contains 108 IDs. 61 have partial deterministic contract tests; 47 explicitly skip because their specialized fixtures/implementation are missing. None has formal legal acceptance. Five combined fault combinations run inside one test. The complete requested 15 combined cases are not yet implemented.

Logs: artifacts/auto-review-v3/intelligence-pytest.log, intelligence-tests.xml, intelligence-browser-production.log, intelligence-build-final.log. A sandbox-only attempt failed collection due native dependency access; rerunning with approved dependency access produced the backend result above.

Live candidate, provider extraction evaluation, all advanced valuations, load tests and complete acceptance remain pending. No skipped test is counted as passed.

Status: implementation candidate; not a complete Auto Review 2.0 release. Local tests are not legal acceptance or live provider acceptance. V2 is excluded.

Live first candidate: login, default OFF, policy persistence, three existing manual exceptions, responsive views, two future CSV uploads (inherited ON and explicit OFF), exact original bytes, unchanged confirmed financial records, deterministic assistant and reset OFF passed. Repeated model questions exposed the persistent auth-throttle defect; that sequence failed and triggered a repair. Repaired sequence pending.
