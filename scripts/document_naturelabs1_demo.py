"""Write the requested handoff from recorded execution evidence, never credentials."""
import json
from collections import Counter
from pathlib import Path

ROOT=Path('demo bills/naturelabs1')
ART=Path('artifacts/gst_easy_v2')


def main():
    manifest=json.loads((ROOT/'TEST_MANIFEST.json').read_text())
    state=json.loads((ART/'naturelabs1-processing.json').read_text())
    acceptance=json.loads((ART/'naturelabs1-acceptance.json').read_text())
    release=json.loads((ART/'naturelabs1-r4-deployment.json').read_text())
    assert all(state['kpi_comparison'].values()) and len(state['invoices'])==23
    assert acceptance['checks'].get('assistant_reconciliation_corrected') is True
    expected=manifest['expected_kpis']; actual=state['actual_kpis']
    extraction_counts=dict(Counter(value['extraction']['method'] for value in state['invoices'].values()))
    table='| KPI | Expected | Actual |\n|---|---:|---:|\n'+''.join(f'| {key} | {value} | {actual[key]} |\n' for key,value in expected.items())
    limits='''- Synthetic test rates and HSN assignments are assumptions, not certified tax advice. GSTIN-like identifiers are fictional fixtures, not government-verified registrations or proof of ownership.
- B2B-only statement parser: the purchase credit note is an unsupported reconciliation case, not a matched portal credit note. A duplicate-candidate statement is rejected, never persisted as a fake match.
- Existing synthetic-tenant restrictions block real return preparation, approvals, filing and financial exports. Read-only reports and calculations work; these restrictions were not bypassed.
- Email and mobile verification remain false. This explicit V2 operator-activated identity is not ownership/KYC verification.
- Local browser tests use designated synthetic fixtures; live evidence is recorded separately. Password changes, account deletion and production filing were not performed during live acceptance.
- AI is read-only and model-generated; cited evidence remains the authority. Search is bounded to the latest 500 canonical records per business/period.
'''
    overview=f'''# Nature Labs 1 V2 demonstration

Account: `naturelabs1@demo.com` (client role, one owner membership; no platform administration).

Live V2 URL: {acceptance['url']}

Business: **Nature Labs Synthetic Manufacturing Pvt Ltd**, trade **Nature Labs Industrial Manufacturing**. Chennai, Tamil Nadu, 600032. Website https://naturelabs-manufacturing.example.test. Complete stored profile and private logo; `is_test=true`, `gstin_verified=false`, profile source `SYNTHETIC_TEST_ONLY`.

Credentials: supplied password was received through hidden terminal input, stored in V2-only Secret Manager secret `gst-easy-v2-naturelabs1-password`, version 1, and hashed by the existing registration service. It is not included in this report or repository.

## Persisted documents

23 distinct invoice identities, each supplied as PDF, PNG and JPEG in `demo bills/naturelabs1/` (69 files). Exactly one representation per invoice was uploaded through `/api/gst/bills/upload`. Existing Cloud Tasks, Vertex AI extraction, private originals, review PATCH, confirmation and rejection routes were used. Authorized demo review corrected fields against generated originals; extraction provenance was retained. Twenty invoices confirmed (10 purchases and 10 sales including one credit note each), two left for review with an intentionally missing editable date, and one rejected with a recorded reason.

Original evidence and pending examples are preserved. No dashboard values were inserted. The earlier `naturelabs@demo.com` account was not populated or modified by this script.

Actual recorded extraction methods: `{json.dumps(extraction_counts)}`.

## Independent expected values versus live results

{table}

Expectations were calculated independently using Decimal in `generate_naturelabs1_demo.py`, then tested against the existing calculation engine and actual persisted live invoices. See `EXPECTED_RESULTS.xlsx` and `TEST_MANIFEST.json`.

## Deployment

Branch `GST-EASY-V2`; API source `{release['source_commit']}`; Cloud Build `{release['build_id']}`. API revision `{release['revision']}`; immutable image `{release['image']}`. Existing V2 frontend retained. Original production/preview services and IAM compared against preserved baselines.

## Limitations

{limits}
## Rollback

For application rollback, route **only gst-easy-v2-api** to the prior revision recorded in `artifacts/gst_easy_v2/naturelabs1-r4-deployment.json`. Do not alter original production services. Synthetic data is retained with audit evidence; rollback does not delete invoice originals or unrelated tenants. Account access can be revoked through the existing authorized membership/identity management process.
'''
    Path('GST_EASY_V2_NATURELABS1_DEMO_REPORT.md').write_text(overview,encoding='utf-8')
    reportrows='\n'.join(f'- {kind}: {row["row_count"]} actual report rows; export allowed: {row["can_export"]}.' for kind,row in state['reports'].items())
    checks='\n'.join(f'- {key}: {str(value) if not isinstance(value,dict) else "recorded in sanitized acceptance JSON"}.' for key,value in acceptance['checks'].items())
    Path('GST_EASY_V2_NATURELABS1_TEST_RESULTS.md').write_text(f'''# Nature Labs 1 test results

## Local automated gates

- Full pytest: 429 passed. Existing dependency deprecations and pytest cache-permission warning recorded.
- Ruff app/tests: passed.
- mypy app: passed, 80 source files.
- Frontend TypeScript: passed.
- Next.js production build: passed.
- Playwright local regression suite: 74 passed; includes synthetic tenant permissions, uploads, PDF/image previews, reports, profile management and mobile layouts.

## Actual live acceptance

No mocked network responses were used. See `artifacts/gst_easy_v2/naturelabs1-processing.json` and `naturelabs1-acceptance.json` for actual API outcomes and AI responses. Screenshots: `artifacts/gst_easy_v2/naturelabs1-*.png`.

## Issues found and corrected

- New demo identity required explicit V2-only operator activation; it remains unverified for email/mobile ownership.
- Customer names were absent from canonical search text; recipient names/GSTINs are now included in the already tenant-scoped adapter.
- The assistant lacked confirmed sales/purchase totals; it now receives signed confirmed-only Decimal aggregates.
- The extraction prompt assumed purchase bills. Direction and note type are now required, with selected-business context. Existing validation caught the misclassified sale; authorized review corrected it before confirmation.
- The first unmatched-invoice AI answer repeated line items and treated an unsupported credit note as unmatched. The assistant now receives the actual deduplicated reconciliation cases and explicit classification guidance; live semantic checks were rerun. Synthetic labeling is enforced in responses.
- A live GET connection reset interrupted report verification; safe reads were retried without re-uploading completed invoices. A browser network-idle wait timed out; visual verification uses actual component readiness instead.

{checks}

## Nine report data checks

{reportrows}

## Known restrictions and blocked actions

{limits}
Live AI limitations: {json.dumps(acceptance['limitations'])}
''',encoding='utf-8')
    Path('GST_EASY_V2_NATURELABS1_DEMO_GUIDE.md').write_text(f'''# Nature Labs 1 demonstration guide

1. Open {acceptance['url']} and sign in as `naturelabs1@demo.com` using the separately supplied password.
2. Select **October 2026**. GST Easy displays persisted invoice-derived KPI values, not sample frontend totals.
3. Open Business Profile from the account dropdown to see the fictional manufacturing profile, website and private logo. The account has exactly one business, so no business-switch selector is expected.
4. Open Bills & Vouchers: review 20 confirmed invoices, two pending examples and one rejected example. Click the fitted preview or **View Original Bill** for private original evidence.
5. Pending examples intentionally omit the editable invoice date. Their source documents retain the date. Completing and confirming them changes the demonstration totals; compare to the baseline before making such edits.
6. Open Reports and each of its nine entries. Back to Reports preserves the selected period. Synthetic financial exports remain restricted.
7. Open Returns & Credit for imported B2B statement comparisons, five exact matches, two amount/head discrepancies, the unsupported purchase credit note, and three unmatched records. Real return preparation/approval is intentionally restricted.
8. Search for `NL1-P-001`, a fictional supplier/customer, or use amount/status filters. Ask the read-only assistant about ITC, cash or confirmed sales; verify its citations.
9. The document pack is `demo bills/naturelabs1/`. Do not upload all three formats of the same invoice; they represent the same identity. `gstr2b-duplicate-invalid.json` is a negative test and should fail import.

All company identities, documents and values are synthetic. They are not valid for tax filing or government verification. The existing original demo account and real customer workspaces are separate.
''',encoding='utf-8')
    print('Generated the three requested handoff documents from recorded execution evidence.')


if __name__=='__main__':main()
