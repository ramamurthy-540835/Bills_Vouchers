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
- [x] Reviewed application commit pushed and remote SHA verified.
- [x] Immutable Cloud Builds successful.
- [x] Both independent V2 services deployed and actual URLs verified.
- [x] Existing service/IAM baseline unchanged after deployment and configuration correction.
- [x] Owner supplied approved password, securely stored in V2 secret version 1.
- [x] Exactly three profiles and owner memberships provisioned.
- [x] Live login/logout, three-business switching, profile/logo, refresh and nine report checks passed.
- [x] Live platform-admin and unrelated-business access denied.
- [x] Profile screenshots at 1440px, 768px and 390px captured; desktop/mobile inspected, no horizontal overflow.
- [ ] Financial upload/extraction/reconciliation live acceptance after owner uploads.

Runtime isolation verified against actual deployed environment, including private API identity audience. Financial live acceptance remains pending user uploads by explicit instruction.
