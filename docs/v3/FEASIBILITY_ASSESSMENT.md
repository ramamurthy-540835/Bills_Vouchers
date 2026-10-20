# GST_NEW_V3 feasibility assessment

Assessment started 20 October 2026. Source: local and remote GST-EASY-V2 both at
`14df23a305826df0f5024ebd10705555045a9185`. V3 branch created from this commit;
untracked user-guide files retained. This is an initial source inspection, not V3 acceptance.

| Requirement group | Current classification | Evidence / acceptance gap |
|---|---|---|
| Existing identity, memberships, profiles, logo, website | IMPLEMENTED_NOT_VERIFIED | V2 evidence exists; new V3 runtime must be tested independently |
| Existing dashboard, bills, reports, search, assistant | IMPLEMENTED_NOT_VERIFIED | Canonical `app/gst` paths retained; prior V2 tests do not prove V3 |
| P0-A verification/recovery | PARTIALLY_IMPLEMENTED | `auth_mail.py` durable outbox, OIDC task, token digest, SMTP; no provider delivery-event evidence |
| P0-A inbox delivery | REQUIRES_EXTERNAL_PROVIDER | Approved test mailbox and sender-domain/provider access required |
| P0-B arithmetic comparison | PARTIALLY_IMPLEMENTED | Decimal line/head/total checks exist; fixed rate allowlist and generic tolerance are not a legal registry |
| P0-B governed override | NOT_IMPLEMENTED | Versioned edits/audits exist; no complete proposed/calculated/approved amount model or material-difference checker |
| P0-C three-app bulk import | NOT_IMPLEMENTED | Existing document multi-upload/template parsing is not transactional event consolidation |
| P0-D asynchronous extraction | IMPLEMENTED_NOT_VERIFIED | Durable jobs and Cloud Tasks exist; V3 measurements required |
| P0-D subsecond authenticated APIs | REQUIRES_ARCHITECTURE_CHANGE | BigQuery identity and transaction round trips must be measured; no microsecond end-to-end promise |
| P0-E rejection lifecycle | PARTIALLY_IMPLEMENTED | Free-text rejection + audit + version exist; explicit correction/resubmission history needs integration |
| P0-F working papers / locks | PARTIALLY_IMPLEMENTED | Existing `app/gst/returns.py`, filing workspace and transactional lock checks |
| P0-F manual return adjustments | NOT_IMPLEMENTED | Arbitrary total changes must remain prohibited |
| Official exports and submission | REQUIRES_EXTERNAL_PROVIDER | No approved GSP credentials/schema certification supplied; disabled until independent verification |
| REST/MCP connected systems | NOT_IMPLEMENTED | No approved client endpoint, OAuth issuer or field mapping supplied |
| Comprehensive statutory/rate registry | REQUIRES_LEGAL_VERIFICATION | Effective dates, amendments and CA-reviewed calculations missing |
| Taxpayer types / all return forms | PARTIALLY_IMPLEMENTED | Profile categories do not constitute implemented return schemas |
| IMS, ledgers, payment, refund, notices | REQUIRES_LEGAL_VERIFICATION | Internal calculations are not government ledger balances or portal decisions |
| Fifty scenarios | NOT_IMPLEMENTED | Each needs separate fixture, expected result, execution and legal review status |
| Due-date engine | REQUIRES_LEGAL_VERIFICATION | Existing display deadlines are not an effective-date notification engine |
| Security / current permissions | IMPLEMENTED_NOT_VERIFIED | Existing tenant-bound query and CSRF rules retained; new paths need tests |
| Independent V3 release | FEASIBLE_NOW | Requested service names absent on initial read-only inventory; isolation baseline in progress |
| Client-ready certification | BLOCKED | Depends on live provider, legal, security, load and client acceptance |

## Source findings that constrain design

- `validate_invoice.py` uses Decimal, but `RATES` is a fixed list and tolerance is
  one rupee. It must not be described as authoritative current GST classification.
- Invoice schema preserves originals via `extraction.raw_ref`, with immutable audit
  before/after payloads. Reuse these controls; do not introduce a second invoice store.
- Existing statuses are extracted, needs_review, confirmed and rejected. Additional
  workflow metadata should preserve these financial inclusion rules.
- `auth_mail.process` calls SMTP and then writes `sent`; that proves submission to
  SMTP at most, not inbox delivery. Expired-token and ignored-invitation paths also
  require explicit outcome handling.
- The existing global BigQuery transaction guards protect consistency but serialize
  activity. Measure contention before introducing caches or a transactional store.
- Historical files named `cloudbuild-v3*` and `deploy_v3.py` predate this request.
  They must not be reused blindly or target older services.

## Official-source investigation

GSTN's [GSP ecosystem](https://gstn.org.in/gsp-ecosystem) describes authorized API
access through the GSP ecosystem. No approved account or filing capability has been
demonstrated for this project.

The [MCP authorization specification](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization)
requires resource-bound token handling and validation. Discovery/OAuth integration,
issuer checks and customer consent must precede a live connector.

The India Code CGST Act result was found, but direct retrieval failed in this audit.
The GST tutorial index also failed retrieval. Neither is marked legally verified.
No rate, deadline, special scenario or official export schema is certified by this assessment.

## Delivery interpretation

21 October is a priority target for tested critical slices, not a promise that all
GST legislation, government workflows or enterprise integrations can be certified
in one day. Unknown or blocked capabilities remain unavailable, not decorative UI.
