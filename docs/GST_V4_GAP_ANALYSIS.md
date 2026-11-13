# GST Easy V4 audit and Method A release scope

Audit baseline: `GSTv4` at `925a753807083ec550c8f7feec2b7584f1ee9860` before this change. Current V4 API revision: `gst-easy-v4-api-00002-97d`; web revision: `gst-easy-v4-web-00001-4pj`. The before-state is saved in ignored `artifacts/v4-audit/v4-current-before.json` for rollback and comparison.

## Module status from source inspection

| Area | Status | Evidence/limitation |
|---|---|---|
| Authentication and session | Existing / not fully re-verified in this work | Existing Firebase/token/session paths retained. Full live account matrix is not repeated here. |
| Email verification and recovery | Partial / external delivery dependent | Existing provider dispatch is present; inbox delivery depends on sender/provider and recipient policy. No delivery claim is made by this change. |
| Business profiles and switching | Existing | Membership-scoped profile and selected-business routes remain unchanged. |
| Dashboard and nine reports | Existing / not fully re-verified in this work | This change does not alter report calculations. |
| Invoice upload, extraction, review, Auto Review | Existing / partial | Canonical bill flow is present. Comprehensive OCR field accuracy across arbitrary real invoices is not established by these changes. |
| Deterministic GST/reconciliation | Existing / requires professional review | Decimal calculations and reconciliation are present. This patch does not certify statutory interpretations or ITC eligibility. |
| Return maker-checker snapshots | Existing / improved | Source-fingerprinted snapshot and separate preparer/reviewer flow retained; Method A adds a read-only validation endpoint and approved package/evidence actions. |
| GST Portal GSTR-1 export | Not verified | No official schema-compatible export is claimed. Current package uses guided worksheets. |
| GSTR-3B preparation | Partial | Internal summary and guided portal worksheet only; portal import compatibility is not established. |
| Official filing/acknowledgement verification | Not integrated | Taxpayer completes the portal steps. Evidence entered in GST Easy is customer-reported and unverified. |
| Live GSTN/GSP, live GSTR-2B, GSTIN lookup, e-invoice/e-way bill, external notifications | Disabled / not customer-facing | No provider adapters are installed. Feature gates fail closed; future lookup routes are not mounted in the customer API. |

## This change

- Adds deterministic return preparation checks and blocks preparation/package creation when configured blockers remain.
- Adds a private Method A package containing the approved immutable snapshot, validation/reconciliation evidence, CSV entry worksheets, warnings, and a hash manifest. It is **not** a GST Portal upload file.
- Adds private upload and audit of customer-provided acknowledgement evidence, and a filing reference/date record whose status is `customer_reported_unverified`.
- Removes the misleading legacy transition that could set `filed`/`locked` from a manually entered ARN. The legacy workbench is limited to preparation-artifact states.
- Keeps automatic GSTIN lookup controls and routes out of the customer surface. The official manual lookup link remains available.
- Adds default-false backend-only provider gates that remain unavailable even if a configuration flag alone is changed.

## Release limitations

This is not a claim that every V4 module has been fully acceptance-tested or that the current tax law, rates, GST Portal schemas, GSTR-1 JSON, GSTR-3B import formats, or ITC decisions have been legally certified. A qualified GST reviewer must approve applicable rule and table mappings. Until schema validation is completed, exports must remain labeled guided worksheets. The release must not report government filing as complete based on taxpayer-entered details.

See [Method A filing workflow](v4/METHOD_A_FILING.md) and [future-provider gates](v4/FUTURE_PROVIDER_GATES.md).
