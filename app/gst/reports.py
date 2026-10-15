"""Read-only reports from canonical evidence; never a government filing adapter."""
import csv
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from io import BytesIO, StringIO
from xml.sax.saxutils import escape

from fastapi import HTTPException
from openpyxl import Workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE

from app.services.gst.medallion import param, period_value
from app.services.gst.rules import HEADS
from . import returns
from .reconciliation import compare
from .report import calculate

TITLES = {'purchases': 'Purchase register', 'sales': 'Sales register', 'invoices': 'Invoice listing',
          'tax': 'Tax-head summary', 'itc': 'ITC decisions', 'reconciliation': 'GSTR-2B reconciliation',
          'audit': 'Audit history'}
MAX_ROWS = 10000
NOTE = ('Canonical evidence only. Financial registers include confirmed invoices; invoice listing includes review states. '
        'Amounts are INR. Credit notes have negative signed values. Tax estimates are calculated separately for each month; '
        'they do not implement an opening/carry-forward credit ledger. This is a working report, not a GST filing export.')


def periods(period, scope):
    period = period_value(period)
    year, month = map(int, period.split('-'))
    if scope == 'month':
        return [period]
    if scope == 'quarter':
        first, count = (month-1)//3*3+1, 3
    elif scope == 'financial_year':
        year, first, count = year if month >= 4 else year-1, 4, 12
    else:
        raise HTTPException(422, 'Choose month, quarter or financial year.')
    if year < 1900 or year > 9998:
        raise HTTPException(422, 'Choose a supported reporting year.')
    return [f'{year+(first-1+i)//12:04d}-{(first-1+i)%12+1:02d}' for i in range(count)]


def safe_cell(value):
    text = str(value if value is not None else '')
    text = ILLEGAL_CHARACTERS_RE.sub(lambda match: f'\\u{ord(match.group()):04x}', text)
    if len(text) > 32767:
        raise HTTPException(422, 'A report field exceeds the spreadsheet cell limit. Shorten the source field before exporting.')
    # Leading whitespace must not hide a spreadsheet formula.
    return "'" + text if text.lstrip().startswith(('=', '+', '-', '@')) or text.startswith(('\t', '\r', '\n')) else text


def audit_rows(store, period, cutoff):
    rows = store.query(f'''SELECT source,reference,actor_id,action,reason,created_at FROM (
      SELECT 'bill' AS source,COALESCE(invoice_id,JSON_VALUE(after_payload,'$.job_id'),'') AS reference,
        actor_id,action,COALESCE(JSON_VALUE(after_payload,'$.reason'),'') AS reason,created_at
      FROM {store.table('ops','gst_bill_audit')}
      WHERE client_id=@client_id AND created_at<=@cutoff AND (
        COALESCE(SUBSTR(JSON_VALUE(after_payload,'$.invoice_date'),1,7),JSON_VALUE(after_payload,'$.selected_period'),JSON_VALUE(after_payload,'$.period'))=@period OR
        COALESCE(SUBSTR(JSON_VALUE(before_payload,'$.invoice_date'),1,7),JSON_VALUE(before_payload,'$.selected_period'),JSON_VALUE(before_payload,'$.period'))=@period)
      UNION ALL
      SELECT 'reconciliation',case_id,actor_id,decision,reason,created_at
      FROM {store.table('ops','gst_reconciliation_review')} WHERE client_id=@client_id AND period=@period AND created_at<=@cutoff
      UNION ALL
      SELECT 'return',COALESCE(snapshot_id,''),actor_id,action,reason,created_at
      FROM {store.table('ops','gst_return_audit')} WHERE client_id=@client_id AND period=@period AND created_at<=@cutoff
    ) ORDER BY created_at,source,reference,action LIMIT {MAX_ROWS+1}''',
        [param('period', period), param('cutoff', cutoff, 'TIMESTAMP')])
    return [[period, *[str(row[key] or '') for key in ('source','reference','actor_id','action','reason','created_at')]] for row in rows]


def build(store, period, scope, kind, profile_for):
    if kind not in TITLES:
        raise HTTPException(422, 'Choose a supported report.')
    selected = periods(period, scope)
    cutoff = datetime.now(timezone.utc)
    hashes = {month: returns.fingerprint(store, month) for month in selected}
    rows: list[list[str]] = []
    sources: list[list[str]] = []
    monthly_scenarios = []
    columns = []
    def add(row):
        rows.append([str(value if value is not None else '') for value in row])
        if len(rows) > MAX_ROWS:
            raise HTTPException(422, 'This report exceeds 10,000 rows. Select a shorter period; no partial export was generated.')
    for month in selected:
        invoices = sorted(store.list(month), key=lambda inv: (str(inv.invoice_date or ''), inv.invoice_number, inv.invoice_id))
        if any(inv.client_id != store.client_id for inv in invoices):
            raise HTTPException(403, 'Report evidence does not belong to the selected business.')
        if any(inv.sample for inv in invoices):
            raise HTTPException(403, 'Synthetic invoices cannot be included in customer reports.')
        if len(invoices)+len(sources) > MAX_ROWS or sum(len(inv.line_items) for inv in invoices) > MAX_ROWS:
            raise HTTPException(422, 'This report is too large. Select a shorter period.')
        sources.extend([[month, inv.invoice_id, str(inv.version), inv.status] for inv in invoices])
        if kind in {'purchases','sales','invoices'}:
            columns = ['Period','Invoice ID','Version','Status','Direction','Supplier GSTIN','Supplier','Recipient GSTIN','Recipient',
                       'Invoice number','Invoice date','Invoice type','Taxable value','IGST','CGST','SGST','Cess','Invoice total']
            for inv in invoices:
                if kind != 'invoices' and (inv.status != 'confirmed' or inv.direction != ('purchase' if kind == 'purchases' else 'sale')):
                    continue
                sign = Decimal('-1') if inv.invoice_type == 'credit_note' else Decimal('1')
                add([month, inv.invoice_id, inv.version, inv.status, inv.direction, inv.supplier_gstin, inv.supplier_legal_name,
                     inv.recipient_gstin, inv.recipient_legal_name, inv.invoice_number, inv.invoice_date, inv.invoice_type,
                     *[format(sign*getattr(inv.totals, head), '.2f') for head in ('taxable_value', *HEADS, 'invoice_total')]])
        elif kind in {'tax','itc'}:
            report = calculate(invoices, profile_for(month), store.matching_rows(month))
            monthly_scenarios.append({'period': month, **{key: format(value, '.2f') for key,value in report['scenarios'].items()}})
            if kind == 'tax':
                columns = ['Period','Tax head','Eligible credit estimate','Output liability','Cash payable estimate']
                for head in HEADS:
                    add([month, head.upper(), *[format(report['heads'][name][head], '.2f') for name in ('credit','output','cash')]])
            else:
                columns = ['Period','Invoice ID','Invoice number','Supplier','Description','Matching','Eligibility','Rule','Signed GST']
                for row in report['decisions']:
                    add([month, *[row[key] for key in ('invoice_id','invoice_number','supplier_name','description','matching','eligibility','rule','tax')]])
        elif kind == 'reconciliation':
            columns = ['Period','Case ID','Invoice ID','Supplier GSTIN','Invoice number','Invoice date','Comparison','Candidate count',
                       'Taxable difference','IGST difference','CGST difference','SGST difference','Cess difference']
            for case in compare(invoices, store.matching_rows(month))['cases']:
                add([month, case['id'], case['invoice_id'], case['supplier_gstin'], case['invoice_number'], case['invoice_date'],
                     case['status'], len(case['statement_candidates']),
                     *[(case['differences'] or {}).get(head) for head in ('taxable_value', *HEADS)]])
        else:
            columns = ['Period','Source','Reference','Actor ID','Action','Reason','UTC timestamp']
            for row in audit_rows(store, month, cutoff):
                add(row)
    if hashes != {month: returns.fingerprint(store, month) for month in selected}:
        raise HTTPException(409, 'Source evidence changed while generating this report. Please retry.')
    result = {'kind': kind, 'title': TITLES[kind], 'client_id': store.client_id, 'periods': selected,
              'generated_at': cutoff.isoformat(), 'columns': columns, 'rows': rows, 'source_invoices': sources,
              'source_hashes': hashes, 'monthly_cash_scenarios': monthly_scenarios, 'note': NOTE, 'row_count': len(rows)}
    result['report_hash'] = hashlib.sha256(json.dumps(result, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return result


def render(report, format):
    if format not in {'csv','xlsx','pdf'} or (format == 'pdf' and report['kind'] != 'tax'):
        raise HTTPException(422, 'Choose CSV or Excel. PDF is available for the tax-head summary.')
    metadata = [['Report', report['title']], ['Client ID', report['client_id']], ['Periods', ', '.join(report['periods'])],
                ['Generated UTC', report['generated_at']], ['Report SHA256', report['report_hash']], ['Scope', report['note']]]
    if format == 'csv':
        output = StringIO()
        writer = csv.writer(output)
        writer.writerows([[safe_cell(value) for value in row] for row in [*metadata, [], report['columns'], *report['rows']]])
        writer.writerow([])
        writer.writerow(['Source period','Source fingerprint'])
        writer.writerows(report['source_hashes'].items())
        return output.getvalue().encode('utf-8-sig'), 'text/csv'
    if format == 'xlsx':
        book = Workbook()
        sheet = book.active
        sheet.title = 'Report'
        for row in [report['columns'], *report['rows']]:
            sheet.append([safe_cell(value) for value in row])
        sheet.freeze_panes = 'A2'
        sheet.auto_filter.ref = sheet.dimensions
        meta = book.create_sheet('Provenance')
        for row in [*metadata, [], ['Period','Source fingerprint'], *report['source_hashes'].items()]:
            meta.append([safe_cell(value) for value in row])
        evidence = book.create_sheet('Source invoices')
        for row in [['Period','Invoice ID','Version','Status'], *report['source_invoices']]:
            evidence.append([safe_cell(value) for value in row])
        if report['monthly_cash_scenarios']:
            scenarios = book.create_sheet('Monthly cash scenarios')
            scenarios.append(['Period','Recorded credit','Matched credit','Eligibility checked','No credit'])
            for row in report['monthly_cash_scenarios']:
                scenarios.append([row[key] for key in ('period','recorded','matched','eligible','noCredit')])
        output_bytes = BytesIO()
        book.save(output_bytes)
        return output_bytes.getvalue(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    return pdf_summary(report, metadata), 'application/pdf'


def pdf_summary(report, metadata):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    buffer = BytesIO()
    styles = getSampleStyleSheet()
    # PDF contains English summary labels/amounts/identifiers; full Unicode registers use CSV/XLSX.
    def paragraph(value, style='BodyText'):
        text = str(value).encode('ascii', 'backslashreplace').decode()
        return Paragraph(escape(text), styles[style])
    story = [paragraph('GST Easy - tax-head summary', 'Title')]
    for key,value in metadata:
        story.append(paragraph(f'{key}: {value}'))
    story.append(Spacer(1, 14))
    table = Table([[paragraph(value) for value in row] for row in [report['columns'], *report['rows']]],
                  colWidths=[85, 65, 170, 160, 170], repeatRows=1)
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e5eef9')),
                              ('GRID',(0,0),(-1,-1),0.3,colors.grey),('VALIGN',(0,0),(-1,-1),'TOP')]))
    story.append(table)
    story.append(Spacer(1, 14))
    story.append(paragraph('Monthly cash estimates - four independent scenarios', 'Heading2'))
    for row in report['monthly_cash_scenarios']:
        story.append(paragraph(f"{row['period']}: recorded {row['recorded']}; matched {row['matched']}; eligibility checked {row['eligible']}; no credit {row['noCredit']} INR"))
    story.append(paragraph('Source fingerprints', 'Heading2'))
    for month, digest in report['source_hashes'].items():
        story.append(paragraph(f'{month}: {digest}'))
    def footer(canvas, doc):
        canvas.setFont('Helvetica', 8)
        canvas.drawString(36, 20, 'Working report - not a GST filing export')
        canvas.drawRightString(805, 20, f'Page {doc.page}')
    SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=36, rightMargin=36,
                      topMargin=30, bottomMargin=35).build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
