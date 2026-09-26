"""Actual-client GST preparation, readiness and accountant working papers.

Gold supplies financial calculations. Bronze/Silver identify source-review gaps.
Monthly, quarterly and financial-year reports are not portal submissions.
"""
import csv
import hashlib
import io
import json
from typing import Any
from concurrent.futures import ThreadPoolExecutor
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import HTTPException
from google.cloud import bigquery

from .medallion import Medallion, clean, encode, param, period_value
from .rules import HEADS, ZERO, amount
from .validation import valid_gstin

ERROR_HELP = {
    'GSTIN_CHECKSUM': 'Correct the supplier GSTIN against the original invoice.',
    'INVOICE_NUMBER_MISSING': 'Enter the invoice number shown on the bill.',
    'INVOICE_DATE_MISSING': 'Enter the invoice date shown on the bill.',
    'INVOICE_OUTSIDE_PERIOD': 'Check the invoice date and the selected return period.',
    'LOW_CONFIDENCE': 'Review the extracted fields against the original bill.',
    'CENTRAL_STATE_TAX_DIFFER': 'Check why CGST and SGST differ on this invoice.',
    'TAX_SPLIT_INCONSISTENT': 'Check IGST versus CGST/SGST using the original invoice.',
    'TAX_RATE_INCONSISTENT': 'Check the tax rate against taxable value and tax amounts.',
    'LINE_TAX_TOTAL_MISMATCH': 'Make invoice-line tax totals agree with the invoice header.',
    'INVOICE_TOTAL_MISMATCH': 'Check that taxable value plus taxes agrees with the invoice total.',
    'LINE_TAXABLE_TOTAL_MISMATCH': 'Make line taxable values agree with the invoice subtotal.',
    'DUPLICATE_INVOICE': 'Resolve the duplicate supplier invoice before claiming credit.',
    'EXTRACTION_FAILED': 'Retry reading the source document or enter reviewed details.',
}


def reporting_periods(period, scope='month'):
    period_value(period)
    year, month = map(int, period.split('-'))
    if scope == 'month':
        return [period], period
    if scope == 'quarter':
        start = ((month-1)//3)*3+1
        return [f'{year}-{m:02d}' for m in range(start, start+3)], f'{year}-{start:02d} to {year}-{start+2:02d}'
    if scope == 'year':
        start_year = year if month >= 4 else year-1
        return [f'{start_year}-{m:02d}' for m in range(4,13)] + [f'{start_year+1}-{m:02d}' for m in range(1,4)], f'FY {start_year}-{str(start_year+1)[-2:]}'
    raise HTTPException(422, 'Choose month, quarter or year.')


def scoped_rows(repo, client_id, months, table):
    # Table identifiers are server constants. Every data query binds tenant and periods.
    return [dict(r.items()) for r in repo.query(
        f'SELECT * FROM `{repo.table(table)}` WHERE client_id=@client_id AND period IN UNNEST(@periods) LIMIT 20001',
        [param('client_id', client_id), bigquery.ArrayQueryParameter('periods', 'STRING', months)])]


def build_filing_workspace(repo, client_id, period, scope='month'):
    months, label = reporting_periods(period, scope)
    profile = Medallion(repo, client_id, period).profile() or {}
    tables = ['bronze_document', 'silver_invoice_header', 'silver_outward_invoice', 'silver_gstr2b_invoice',
              'gold_filing_summary', 'gold_itc_ledger', 'gold_gstr2b_match', 'gst_filing_status']
    with ThreadPoolExecutor(max_workers=4) as pool:
        values = list(pool.map(lambda table: scoped_rows(repo, client_id, months, table), tables))
    data = dict(zip(tables, values))
    from ...fixtures.red_taxi_sample import generate, is_synthetic
    from ...config import get_settings
    sample_months = []
    for month in months:
        summaries = [r for r in data['gold_filing_summary'] if r['period']==month]
        if any(not is_synthetic(r) for r in summaries):
            for table in tables:
                data[table] = [r for r in data[table] if r['period']!=month or not (
                    is_synthetic(r) or str(r.get('doc_id','')).startswith(('demo-','sample-'))
                    or str(r.get('invoice_no','')).startswith(('RTX-DEMO','RTX-SAMPLE')))]
        if str(profile.get('legal_name','')).lower()=='red taxi' and not any(not is_synthetic(r) for r in summaries) and (get_settings().demo_fallback or any(is_synthetic(r) for r in summaries)):
            fixture = generate(month,client_id,profile)
            for table in tables:
                data[table] = [r for r in data[table] if r['period']!=month] + fixture['tables'][table]
            sample_months.append(month)
    report = prepare_report(client_id, period, scope, months, label, profile, data)
    if sample_months or any(is_synthetic(r) for r in data['gold_filing_summary']):
        report.update(sample=True, mode='sample', demo_fallback=True, source='sample', sample_months=sample_months)
        report['profile'] = {**profile,'state_code':'33','filing_frequency':'monthly'}
        if scope=='month':
            from ...fixtures.red_taxi_sample import comparison_deltas, previous_period
            report['deltas'] = comparison_deltas(report['summary'],generate(previous_period(period),client_id,profile)['tables']['gold_filing_summary'][0])
    return report


def prepare_report(client_id, period, scope, months, label, profile, data):
    checks = []
    def issue(code, text, month=None, href=None, severity='blocker'):
        checks.append({'code': code, 'message': text, 'period': month, 'href': href, 'severity': severity})
    if not valid_gstin(profile.get('gstin')):
        issue('GSTIN_REQUIRED', 'Complete and verify this client’s GSTIN before filing.')
    frequency = str(profile.get('filing_frequency') or '').lower()
    if frequency not in {'monthly','quarterly','qrmp'}:
        issue('FREQUENCY_REQUIRED', 'Confirm monthly or quarterly QRMP filing frequency from the GST portal.')
    if profile.get('composition_flag') or profile.get('composition_scheme'):
        issue('COMPOSITION_UNSUPPORTED', 'Composition returns need a separate CMP-08/GSTR-4 workflow; do not use regular-return drafts.')
    if profile.get('has_rcm_supplies'):
        issue('RCM_REVIEW_REQUIRED', 'Reverse-charge supplies require separate tax-payment and credit verification.')
    if any(len(rows) > 20000 for rows in data.values()):
        issue('REPORT_LIMIT', 'This report exceeds 20,000 rows in a section. Export smaller periods; this report is incomplete.')
    if scope == 'quarter' and frequency == 'monthly':
        issue('MONTHLY_FILER', 'This client files monthly. This quarter is a review report, not one quarterly return.', severity='info')
    if scope == 'year':
        issue('ANNUAL_REVIEW', 'Financial-year consolidation is for annual review; it is not a completed GSTR-9/GSTR-9C return.', severity='info')
    by_summary: dict[str, Any] = {}
    for row in data['gold_filing_summary']:
        if row['period'] not in by_summary or str(row.get('computed_at')) > str(by_summary[row['period']].get('computed_at')):
            by_summary[row['period']] = row
    current = lambda r: r.get('run_id') == by_summary.get(r['period'], {}).get('run_id') and r['period'] in by_summary
    ledger = [r for r in data['gold_itc_ledger'] if current(r)]
    matches = [r for r in data['gold_gstr2b_match'] if current(r)]
    headers = {r['doc_id']: r for r in data['silver_invoice_header']}
    posted = {(r['period'], r['doc_id']) for r in ledger}
    documents = []
    for source in data['bronze_document']:
        header = headers.get(source['doc_id']) or {}
        doc = {**source, 'silver': header, 'stage': 'In ledger' if (source['period'], source['doc_id']) in posted else 'Awaiting review'}
        doc['review_url'] = f"/documents/{source['doc_id']}?period={source['period']}"
        doc['issues'] = [{'code': code, 'message': ERROR_HELP.get(code, code.replace('_',' ').capitalize())}
                         for code in header.get('validation_errors') or []]
        if not header or header.get('validation_status') != 'validated':
            issue('DOCUMENT_REVIEW', f"Review {source['original_filename']} before using its tax amounts.", source['period'], doc['review_url'])
        documents.append(doc)
    for row in matches:
        if row.get('match_status') == 'amount_mismatch':
            issue('AMOUNT_MISMATCH', f"Resolve the GSTR-2B difference for invoice {row.get('invoice_no')}.", row['period'])
    for row in ledger:
        if str(row.get('rule_ref','')).endswith('BASIS-MISSING'):
            issue('ATTRIBUTION_REQUIRED', f"Set the common-credit attribution basis for invoice {row.get('invoice_no')}.", row['period'])
    monthly = []
    for month in months:
        summary = by_summary.get(month)
        month_docs = [d for d in documents if d['period']==month]
        states = [r for r in data['gst_filing_status'] if r['period']==month and r.get('is_current')]
        status = max(states, key=lambda r: str(r.get('effective_from'))) if states else {'state':'draft'}
        outward_count = sum(r['period']==month for r in data['silver_outward_invoice'])
        two_b_count = sum(r['period']==month for r in data['silver_gstr2b_invoice'])
        if not summary:
            issue('GOLD_MISSING', 'No calculated figures. Review source records and run ITC computation.', month, f'/gst/filing?period={month}')
        if not outward_count:
            issue('SALES_NOT_IMPORTED', 'No sales register is available. Confirm nil sales or import the actual sales records.', month, f'/gst/filing?period={month}')
        if not two_b_count:
            issue('GSTR2B_NOT_IMPORTED', 'Import this period’s GSTR-2B or have the preparer verify the nil-credit position.', month, f'/gst/filing?period={month}')
        monthly.append({'period': month, 'documents':len(month_docs), 'review':sum(d['silver'].get('validation_status')!='validated' for d in month_docs),
                        'outward_count': outward_count, 'gstr2b_count': two_b_count, 'summary':summary, 'filing':status,
                        'href': f'/gst/filing?period={month}'})
    summary = None
    if by_summary:
        groups = {group: {h:sum((amount((row.get(group) or {}).get(h)) for row in by_summary.values()),ZERO) for h in HEADS}
                  for group in ('input_by_head','eligible_by_head','output_by_head','eco_by_head','cash_by_head','net_payable_by_head')}
        # Never offset a later month's credit against an earlier month's liability.
        # Consolidated reports add stored monthly estimates; they do not simulate filing.
        summary = {**groups, 'cash_required':sum((amount(row.get('cash_required')) for row in by_summary.values()),ZERO),
                   **{k:sum((amount(row.get(k)) for row in by_summary.values()),ZERO) for k in ('as_booked','restricted_2b','fully_compliant','if_late_file')},
                   'non_gst':sum((amount(row.get('non_gst')) for row in by_summary.values()),ZERO),
                   'credit_adjustments':{bucket:{h:sum((amount(row.get(f'{bucket}_{h}')) for row in ledger),ZERO) for h in HEADS}
                                         for bucket in ('blocked','deferred','reversal')}}
    issue('PORTAL_SCHEMA_UNVERIFIED', 'Portal-upload JSON is not verified for the current schema. Use working papers for preparation and verify the final return in the GST portal.')
    issue('PAYMENT_REVIEW', 'Opening credit/cash balances, payments, interest and late fees must be checked in the GST portal. Quarter/year cash figures add monthly estimates without inter-period credit carry-forward.', severity='info')
    return clean({'client_id':str(client_id), 'period':period, 'scope':scope, 'periods':months, 'period_label':label,
                  'profile':profile, 'source':'actual', 'sample':False, 'summary':summary,
                  'calculation_complete':len(by_summary)==len(months), 'monthly':monthly, 'documents':documents,
                  'ledger':ledger, 'matches':matches, 'outward':data['silver_outward_invoice'], 'gstr2b':data['silver_gstr2b_invoice'],
                  'checks':checks, 'portal_ready':False, 'ready_for_review':not any(c['severity']=='blocker' and c['code']!='PORTAL_SCHEMA_UNVERIFIED' for c in checks)})


def csv_bytes(rows, columns):
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction='ignore')
    writer.writeheader()
    for row in rows:
        safe = {}
        for key in columns:
            value = row.get(key, '')
            if isinstance(value, (dict,list)):
                value = encode(value)
            # Invoice text must not become executable spreadsheet formulae.
            if isinstance(value,str) and value.lstrip().startswith(('=','+','-','@')):
                value = "'"+value
            safe[key] = value
        writer.writerow(safe)
    return output.getvalue().encode('utf-8-sig')


def working_papers(report):
    if report.get('sample'):
        raise HTTPException(403, {'code':'sample_data_blocked','message':'Sample records cannot be exported as working papers.'})
    files = {'preparation.json':json.dumps(report,ensure_ascii=False,indent=2).encode('utf-8')}
    files['checks.csv'] = csv_bytes(report['checks'], ['severity','period','code','message'])
    files['itc_ledger.csv'] = csv_bytes(report['ledger'], ['period','doc_id','invoice_no','line_no','description','reason_code','rule_ref'] + [f'{b}_{h}' for b in ('eligible','blocked','deferred','reversal') for h in HEADS])
    files['reconciliation.csv'] = csv_bytes(report['matches'], ['period','invoice_no','supplier_gstin','match_status','delta','doc_id'])
    files['sales_register.csv'] = csv_bytes(report['outward'], ['period','invoice_no','invoice_date','recipient_gstin','place_of_supply','taxable_value',*HEADS,'eco_9_5'])
    files['gstr2b_register.csv'] = csv_bytes(report['gstr2b'], ['period','invoice_no','invoice_date','supplier_gstin','taxable_value',*HEADS])
    files['purchase_review.csv'] = csv_bytes([{**doc.get('silver',{}),'period':doc['period'],'doc_id':doc['doc_id'],'filename':doc['original_filename']} for doc in report['documents']], ['period','doc_id','filename','supplier_name','supplier_gstin','invoice_no','invoice_date','total','validation_status','validation_errors'])
    files['README.txt'] = ('GST preparation working papers — actual client records.\nNot a portal-upload return, payment receipt or filing acknowledgement.\nReview checks.csv. Unreviewed purchases are excluded from Gold calculations.\nQuarter/year figures consolidate available months; missing months are explicit.\nVerify opening balances, paid amounts and final liabilities in the GST portal.\n').encode('utf-8')
    files['manifest.json'] = json.dumps({'client_id':report['client_id'],'periods':report['periods'],'sample':False,'portal_ready':False,
        'sha256':{name:hashlib.sha256(payload).hexdigest() for name,payload in files.items()}},indent=2).encode()
    output = io.BytesIO()
    with ZipFile(output,'w',ZIP_DEFLATED) as archive:
        for name,payload in files.items():
            archive.writestr(name,payload)
    return output.getvalue()
