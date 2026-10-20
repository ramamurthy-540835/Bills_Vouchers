# GST Easy V3 implementation status

Engineering preview in development. No claim of complete statutory compliance,
government filing, universal connectors or production certification.

| Area | Current status |
|---|---|
| Existing V2 workflows | Preserved in source; local regression tested, V3 live acceptance pending |
| Email outcomes | Implemented and locally tested; SMTP accepted but authorized user confirmed nonreceipt |
| Declared-rate GST comparison | Implemented and locally tested; legal rate selection not implemented |
| Correction/resubmission | Implemented and locally tested; evidence-replacement and notifications pending |
| Bulk source intake | Persisted staging implemented; canonical multi-source consolidation incomplete |
| REST/MCP | Synthetic adapter tests pass; production OAuth/egress/management incomplete |
| Performance | Local CPU baseline measured; cloud SLO and cost acceptance pending |
| Manual return adjustments | Existing invoice edits/approval retained; comprehensive adjustment engine missing |
| GST legal registry / 50 scenarios | Review inventory prepared; formal rules and expected calculations unverified |
| Official export / submission | Not certified / disabled |
| V3 deployment | Independent services deployed and public smoke tests passed; authenticated live acceptance blocked by mail delivery |

See docs/v3 for per-area details and the review workbook for all 50 scenarios.
