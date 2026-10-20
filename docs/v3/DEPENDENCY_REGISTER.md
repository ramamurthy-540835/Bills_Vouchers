# V3 dependency register

User authorized ai@aidirac.com for verification, recovery, resend and expiry testing.
Synthetic Vendor/Customer/Driver APIs are authorized for connector development.
Formal GST acceptance remains pending an authorized specialist.

| ID | Owner | Technical reason / access | Cost implications | Legal implications | Fallback | Acceptance |
|---|---|---|---|---|---|---|
| EMAIL | Owner + email administrator | Authorized test inbox; sender-domain DNS; approved SMTP/provider account, delivery events and suppression diagnostics | Provider plan and message quotas | Consent for test mail; protect tokens and addresses | Local transport tests; no claim of delivery | Inbox receives correct V3 link; expiry/replay/resend and bounce tests |
| GSP | Owner + authorized provider | Provider contract, sandbox, taxpayer consent, form schemas, signing and acknowledgement APIs | Provider/API fees | GSTN authorization, DSC/EVC and taxpayer approval | Internal working papers; no live submission | Certified schema, independent expected return, explicit submission approval, official acknowledgement |
| LEGAL | Appointed GST reviewer/CA | Current effective rules, notifications, scenario-specific evidence and expected calculations | Professional review | No inferred eligibility, rates or deadlines | Mark scenarios REQUIRES_LEGAL_VERIFICATION; block unsupported automated conclusions | Signed review per rule version and scenario |
| REST | Customer integration administrator | Approved sandbox URL, read-only credential secret, record schema, incremental cursor and mapping | API quota and storage/processing | Data minimization and customer consent | Local contract fixtures | Live bounded import, duplicates/conflicts, revoke and tenant isolation |
| MCP | Customer integration administrator | Approved MCP server, OAuth issuer/resource, read-only tools, consent and callback registration | Provider/network costs | No token passthrough or arbitrary SQL | Adapter tests with explicitly mocked server | Audience/issuer validation, allowlisted tools, live sync and revoke |
| CLOUD | Project owner + release engineer | New V3 datasets/bucket/queues/SAs/secrets; quota and IAM | New Cloud Run, BQ, GCS, Tasks, AI usage | Separate tenant resources; no production data copies | Local tests and release scripts | Before/after preservation, independent services, runtime isolation proof |
| LOAD | Owner + engineer | Approved concurrency, dataset size, spend ceiling and representative workload | Load/AI/BQ spend can be material | Synthetic data only | Bounded local arithmetic and contract benchmarks | Reproducible p50/p95/p99, error rate, resource/cost metrics |
| ACCEPTANCE | Owner + reviewer + QA | Authorized realistic client scenarios and signoff | Staff time | Synthetic demo is not production certification | Explicit limited-preview status | All applicable gates and blockers reviewed |

Credentials must use new V3 Secret Manager resources. V3 has a newly generated session
secret. The existing approved SMTP sender credential was read into a separate V3-only
secret without logging it or changing the original secret, versions or IAM.
Do not change V2 IAM, send mail to unapproved customers, or invoke paid GSP services.
SMTP configuration is not proof of inbox delivery. Delivery to the subsequently
authorized Gmail recipient and verified sign-in/dashboard were owner-confirmed.
Self-address nonreceipt, recovery, bounce and complaint acceptance remain pending.
