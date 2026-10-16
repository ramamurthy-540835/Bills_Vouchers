# V2 release checklist

- [x] Current local work preserved on GST-EASY-V2.
- [x] Historical handoff/source snapshot inspected.
- [x] New V2 build YAML; existing configurations unchanged.
- [x] 28 synthetic invoice identities generated in PDF/PNG/JPEG.
- [x] Logos, edge cases, supported statements and Decimal expectations generated.
- [x] No demo invoice/statement/financial seed performed.
- [x] Isolated datasets, private buckets, accounts, queue and secrets prepared.
- [x] Existing service configuration/IAM captured.
- [x] Backend full tests, Ruff, mypy, TypeScript and build passed.
- [x] Final browser rerun: 67 passed.
- [ ] Reviewed application commit pushed and remote SHA verified.
- [ ] Immutable Cloud Builds successful.
- [ ] Both independent V2 services deployed and actual URLs verified.
- [ ] Existing service/IAM baseline unchanged after deployment.
- [ ] Owner supplies approved password secret version.
- [ ] Exactly three profiles and owner memberships provisioned.
- [ ] Live login, switching, profile/logo and empty module checks passed.
- [ ] Financial upload/extraction/reconciliation live acceptance after owner uploads.

Do not convert pending checks into passed checks. Full presentation-ready acceptance depends on secure credential provisioning and real live tests.
