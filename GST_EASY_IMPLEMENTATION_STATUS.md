# GST Easy V3 implementation status

Engineering preview in development. No claim of complete statutory compliance,
government filing, universal connectors or production certification.

| Area | Current status |
|---|---|
| Existing V2 workflows | Preserved in source; local regression tested, V3 live acceptance pending |
| Email outcomes | Gmail delivery and verified sign-in/dashboard owner-confirmed. Self-address delivery unexplained; recovery/bounce acceptance pending |
| Declared-rate GST comparison | Implemented and locally tested; legal rate selection not implemented |
| Correction/resubmission | Lifecycle and dedicated correction queue implemented; evidence-replacement, notifications and material-difference maker/checker policy pending |
| Bulk source intake | Staging, column mapping, exact canonical comparison, cross-source reference checks and audit snapshots implemented; promotion and large async imports incomplete |
| REST/MCP | Synthetic adapter tests pass; production OAuth/egress/management incomplete |
| Performance | Local CPU baseline measured; cloud SLO and cost acceptance pending |
| Manual return adjustments | Existing invoice edits/approval retained; comprehensive adjustment engine missing |
| GST legal registry / 50 scenarios | Review inventory prepared; formal rules and expected calculations unverified |
| Official export / submission | Not certified / disabled |
| V3 deployment | Independent services deployed and public smoke tests passed; full authenticated workflow acceptance pending |

See docs/v3 for per-area details and the review workbook for all 50 scenarios.

Latest deployed application commit: 899114f7bd44946904b80483a29d029a188c49a5.
Source mapping, exact reconciliation snapshots and private original-source access
and the correction queue are live in V3. Local gates: 507 backend tests, 79 browser
tests, 5 focused browser checks, Ruff, fresh-cache mypy, TypeScript and build
passed. Real isolated BQ/GCS service integration, correction SQL checks and nine
live access-boundary checks passed. These do not
establish full authenticated financial or external-provider acceptance.
