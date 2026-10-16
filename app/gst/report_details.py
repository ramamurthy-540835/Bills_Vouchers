"""Report projections of canonical evidence, not a second tax calculation engine."""
from decimal import Decimal
from typing import Any
from pathlib import PurePosixPath
from .report import calculate
from .reconciliation import compare
from app.services.gst.rules import HEADS

KINDS = {'credit','liability','cash','without_itc','pending','mismatches','unmatched','sales','purchases'}
ZERO = Decimal('0')


def money(value):
    return format(value, '.2f')


def project(kind, invoices, profile, statements, imported, month, reviews=()):
    calculation = calculate(invoices, profile, statements)
    decisions = calculation['decisions']
    confirmed = [inv for inv in invoices if inv.status == 'confirmed' and not inv.sample]
    purchase_lines = [(inv,line) for inv in confirmed if inv.direction=='purchase' for line in inv.line_items]
    by_invoice: dict[str, list[dict[str, Any]]] = {}
    for row in decisions:
        by_invoice.setdefault(row['invoice_id'], []).append(row)
    warnings = []
    if not imported:
        warnings.append(f'{month}: Statement not imported. Matching and usable positive credit have not been established.')
    rows = []
    summary = {}
    if kind in {'credit','without_itc'}:
        columns = ['Period','Invoice ID','Invoice number','Supplier','Description','Matching','Eligibility','Rule','Signed GST',
                   'Supplier GSTIN','Invoice date','HSN/SAC','Taxable value','CGST','SGST','IGST','Cess','GST rate','Credit evidence','Signed purchase value']
        for (inv,line),decision in zip(purchase_lines, decisions, strict=True):
            sign = Decimal('-1') if inv.invoice_type=='credit_note' else Decimal('1')
            candidates = [row for row in statements if row['supplier_gstin']==inv.supplier_gstin and
                          str(row['invoice_number']).strip().upper()==inv.invoice_number.strip().upper() and
                          str(row.get('invoice_date',''))==str(inv.invoice_date)]
            availability = 'Available in statement' if len(candidates)==1 and candidates[0].get('itc_available') is True else 'Not established or unavailable'
            if kind=='without_itc' and decision['eligibility']=='eligible' and (sign<0 or (decision['matching']=='matched' and availability=='Available in statement')):
                continue
            rows.append([month,inv.invoice_id,inv.invoice_number,inv.supplier_legal_name,line.description,
                decision['matching'] if imported else 'statement_not_imported',decision['eligibility'],decision['rule'],money(decision['tax']),
                inv.supplier_gstin,str(inv.invoice_date or ''),line.hsn_sac,money(sign*line.taxable_value),
                *[money(sign*getattr(line,h)) for h in ('cgst','sgst','igst','cess')],str(line.gst_rate),availability,
                money(sign*(line.taxable_value+sum((getattr(line,h) for h in HEADS),ZERO)))])
        summary = {'Recorded input tax':money(sum(calculation['credit_pools']['recorded'].values(),ZERO)),
            'Usable ITC estimate':money(calculation['totals']['eligible_credit']),
            'Non-eligible classified tax':money(sum((row['tax'] for row in decisions if row['eligibility']!='eligible'),ZERO)),
            'Matched available credit (signed)':money(sum(calculation['credit_pools']['matched'].values(),ZERO)),
            'Unmatched input tax':money(sum((row['tax'] for row in decisions if row['matching']=='unmatched'),ZERO)) if imported else 'Statement not imported'}
        if kind=='without_itc':
            summary = {f"Purchase value: {bucket}":money(sum((Decimal(row[-1]) for row in rows if row[6]==bucket),ZERO)) for bucket in sorted({row[6] for row in rows})}
            warnings.append('This report also includes eligible-classified lines whose credit is not established. The dashboard Purchases Without ITC metric includes only non-eligible classifications.')
            warnings.append('Zero-rate lines retain the existing NON-GST rule label; evidence does not distinguish exempt, zero-rated and non-GST supplies. No new tax classification is inferred.')
    elif kind in {'sales','purchases','liability','pending'}:
        columns = ['Period','Invoice ID','Version','Status','Direction','Supplier GSTIN','Supplier','Recipient GSTIN','Recipient',
            'Invoice number','Invoice date','Invoice type','GST rates','Eligibility','Matching','Source filename','Upload date',
            'Extraction confidence','Validation problems','Assigned reviewer','Taxable value','IGST','CGST','SGST','Cess','Invoice total']
        for inv in invoices:
            if kind=='pending':
                if inv.status not in {'needs_review','extracted'}:continue
            elif inv.status!='confirmed' or inv.direction!=('purchase' if kind=='purchases' else 'sale'):continue
            sign = Decimal('-1') if inv.invoice_type=='credit_note' else Decimal('1')
            line_decisions = by_invoice.get(inv.invoice_id, [])
            rows.append([month,inv.invoice_id,str(inv.version),inv.status,inv.direction,inv.supplier_gstin,inv.supplier_legal_name,
                inv.recipient_gstin,inv.recipient_legal_name,inv.invoice_number,str(inv.invoice_date or ''),inv.invoice_type,
                ', '.join(sorted({str(line.gst_rate) for line in inv.line_items})),
                ', '.join(sorted({row['eligibility'] for row in line_decisions})) or 'Not applicable',
                (', '.join(sorted({row['matching'] for row in line_decisions})) if imported else 'statement_not_imported') if inv.direction=='purchase' else 'Not applicable',
                PurePosixPath(inv.extraction.raw_ref).name if inv.extraction.raw_ref else 'Not recorded',
                'Not recorded',str(inv.extraction.confidence),'; '.join(inv.review_reasons) or 'None recorded','Not assigned',
                *[money(sign*getattr(inv.totals,h)) for h in ('taxable_value',*HEADS,'invoice_total')]])
        if kind=='pending':warnings.append('Upload time and reviewer assignment are not stored on the canonical invoice. They are shown as unavailable, not inferred from invoice dates.')
    elif kind=='cash':
        columns = ['Period','Scenario','Tax head','Available ITC','Output liability','Credit utilized from head','Credit applied to liability','Cash payable estimate','Credit remaining']
        for scenario,details in calculation['scenario_details'].items():
            for head in HEADS:
                rows.append([month,scenario,head.upper(),money(max(ZERO,calculation['credit_pools'][scenario][head])),
                    money(calculation['heads']['output'][head]),
                    money(sum((Decimal(row['amount']) for row in details['utilisation'] if row['from']==head),ZERO)),
                    money(sum((Decimal(row['amount']) for row in details['utilisation'] if row['to']==head),ZERO)),
                    money(details['cash_by_head'][head]),money(details['credit_carried'][head])])
        warnings.append('Independent monthly estimates, not government electronic ledgers. Opening balances and carry-forward are not included.')
    else:
        columns = ['Period','Case ID','Invoice ID','Supplier GSTIN','Invoice number','Invoice date','Comparison','Candidate count',
            'Taxable difference','IGST difference','CGST difference','SGST difference','Cess difference','Supplier',
            'Books taxable','Books IGST','Books CGST','Books SGST','Books cess','Statement taxable','Statement IGST','Statement CGST','Statement SGST','Statement cess',
            'Source','Review status','Statement evidence']
        review_map = {row['case_id']:row for row in reviews}
        invoice_map = {inv.invoice_id:inv for inv in invoices}
        if imported:
            for case in compare(invoices,statements)['cases']:
                missing = case['status'] in {'missing_book','missing_statement'}
                if kind=='unmatched' and not missing:continue
                if kind=='mismatches' and (missing or case['status']=='exact'):continue
                inv = invoice_map.get(case['invoice_id'])
                review = review_map.get(case['id'])
                # A prior review may be stale; the resolution UI rechecks its evidence fingerprint.
                state = (str(review['decision'])+' (verify current evidence)') if review else 'Not reviewed'
                candidates = case['statement_candidates']
                rows.append([month,case['id'],case['invoice_id'] or '',case['supplier_gstin'],case['invoice_number'],case['invoice_date'],case['status'],str(len(candidates)),
                    *[str((case['differences'] or {}).get(h) if (case['differences'] or {}).get(h) is not None else '') for h in ('taxable_value',*HEADS)],
                    inv.supplier_legal_name if inv else 'Not recorded',
                    *[str((case.get(source) or {}).get(h) if (case.get(source) or {}).get(h) is not None else '') for source in ('book_amounts','statement_amounts') for h in ('taxable_value',*HEADS)],
                    'Books' if case['status']=='missing_statement' else 'Statement' if case['status']=='missing_book' else 'Books and statement',state,
                    ', '.join(sorted({row['source_sha256'] for row in candidates if row.get('source_sha256')}))])
    return columns,rows,summary,warnings
