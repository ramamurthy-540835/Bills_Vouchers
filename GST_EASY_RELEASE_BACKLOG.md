# Remaining release backlog

The Phase 00-09 master prompt remains the acceptance contract. This list supersedes the initial inventory; implemented work is summarized in GST_EASY_MODULE_STATUS.md. Cross-cutting fixes do not waive earlier acceptance gates.

1. Phase 00: complete current cloud/schema/IAM inventory and reproducible release evidence. Keep historical baseline failures separate from current passing checks.
2. Phase 01: verify actual email verification/recovery/security notification delivery across recipient providers; configure and test approved SMS verification; review mobile-duplicate policy; measure registration/throttling concurrency and cost. SMTP is configured, but inbox delivery is not proven.
3. Phase 02: validate actual invitation delivery, private logo storage round trips, revoked-access UI and customer role policy.
4. Phase 03: validate deployed audited stale-job recovery with real queue delivery; inject failures around storage, enqueue, extraction and writes; verify durable refresh, live extraction and retention/restore policy.
5. Phase 04: obtain accountant examples and verified current rules; implement evidence-backed credit-ledger movements and line-level eligibility; extend supported statement sections/amendments/notes according to verified specifications. Auditable review acknowledgement is implemented; it does not resolve financial mismatches or override ITC.
6. Phase 05: add verified versioned GSTR-1/GSTR-3B exports and validators, nil-return coverage and accountant maker-checker acceptance. Canonical snapshots, locks and review-dependent stale-data prevention are implemented.
7. Phase 06: validate the new reporting center/exports with genuine evidence; complete dashboard-wide period coverage and drilldowns; validate scoped assistant behavior against prompt injection and genuine source evidence.
8. Phase 07: complete all visible-action/accessibility/refresh audits and actual notification journeys. Fifteen local browser scenarios pass, not the entire acceptance inventory.
9. Phase 08: replace overprivileged shared identity safely; measure API/query/AI/queue costs and latency; deliver alerts; implement and accept production backup/recovery strategy; obtain retention and independent security review. A synthetic 12-table snapshot restore and GCS object-copy restore passed on 15 October; this does not establish production RPO/RTO or scheduled backup coverage.
10. Phase 09: authorized genuine-client UAT, independent accountant acceptance, immutable release/rollback evidence and owner approval before production promotion.

External gates: verified email delivery, approved SMS configuration, accountant-approved calculations and current official schemas, retention policy, genuine customer evidence/UAT, owner production release authorization. Do not fabricate these approvals. Never submit actual returns, initiate payments, purge evidence or move production traffic under this development authorization.
