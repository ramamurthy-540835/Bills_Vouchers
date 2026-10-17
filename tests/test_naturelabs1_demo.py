"""Independent fixture expectations checked against unchanged application rules."""
import json
from decimal import Decimal
from pathlib import Path

import pytest

from app.gst.schemas.invoice import GstInvoice
from app.gst.validate_invoice import validate_invoice
from app.gst.matching import parse_gstr2b
from app.gst.report import calculate
from app.gst.reconciliation import compare

ROOT=Path('demo bills/naturelabs1')


def test_extraction_requires_direction_and_note_type():
    from app.gst.extract import extraction_schema
    schema=extraction_schema()
    assert {'direction','invoice_type'} <= set(schema['required'])
    assert set(schema['properties']['direction']['enum'])=={'purchase','sale'}


def test_synthetic_pack_validates_and_matches_independent_expectations():
    manifest=json.loads((ROOT/'TEST_MANIFEST.json').read_text())
    profile=manifest['business']; invoices=[]
    for row in manifest['invoices']:
        invoice=GstInvoice(client_id='isolated-test',source_doc_id=row['invoice_number'],
            invoice_number=row['invoice_number'],invoice_date=row['invoice_date'],invoice_type=row['invoice_type'],
            direction=row['direction'],supplier_gstin=row['supplier']['gstin'],recipient_gstin=row['recipient']['gstin'],
            supplier_legal_name=row['supplier']['legal_name'],recipient_legal_name=row['recipient']['legal_name'],
            place_of_supply_state_code=row['place_of_supply_state_code'],totals=row['totals'],
            line_items=[{k:v for k,v in line.items() if k!='unit_price'} for line in row['line_items']])
        invoice=validate_invoice(invoice,profile,invoices,human_review=True)
        assert not invoice.review_reasons
        invoice.status=row['expected_status']
        invoices.append(invoice)
    statement=parse_gstr2b((ROOT/'gstr2b.json').read_text(),profile,manifest['period'])
    report=calculate(invoices,profile,statement)
    for key,value in report['totals'].items():
        assert value==Decimal(manifest['expected_kpis'][key]),key
    comparison=compare(invoices,statement)
    assert comparison['counts'].get('missing_book',0)+comparison['counts'].get('missing_statement',0)==manifest['expected_kpis']['unmatched_invoices']
    assert sum(v for k,v in comparison['counts'].items() if k not in {'exact','missing_book','missing_statement'})==3
    assert len(invoices)==23 and sum(i.status=='confirmed' for i in invoices)==20
    from app.gst.evidence import documents, confirmed_summary
    from app.services.gst.evidence_search import search_evidence
    assert search_evidence(documents(invoices,manifest['period']),'Fictional Customer')['total']==11
    summary=confirmed_summary(invoices)
    assert Decimal(summary['confirmed_sales'])==Decimal(manifest['expected_kpis']['confirmed_sales'])
    assert Decimal(summary['confirmed_purchases'])==Decimal(manifest['expected_kpis']['confirmed_purchases'])
    assert summary['pending_review_count']==2
    from app.gst.evidence import reconciliation_context
    context=reconciliation_context(invoices,statement,True)
    assert {row['invoice_number'] for row in context['cases'] if row['status']=='missing_statement'}=={'NL1-P-005','NL1-P-009'}
    assert len(context['cases'])==11
    assert reconciliation_context(invoices,[],False)=={'statement_imported':False,'cases':[]}
    from app.services.gst.assistant import grounded_context, status_answer
    grounded=grounded_context({'source':'canonical','period':manifest['period'],'sample':True,
                              'reconciliation':context},documents(invoices,manifest['period']),'review')
    pending=status_answer('Which invoices need review?',grounded)
    assert 'NL1-P-011' in pending['answer'] and 'NL1-S-012' in pending['answer']
    assert 'NL1-P-013' not in pending['answer']
    unmatched=status_answer('Which purchase invoices are unmatched?',grounded)
    assert 'NL1-P-005' in unmatched['answer'] and 'NL1-P-009' in unmatched['answer']
    assert all(number not in unmatched['answer'] for number in ['NL1-P-002','NL1-P-003','NL1-P-010','NL1-ONLY-001'])
    assert len(unmatched['sources'])==3
    assert status_answer('Change my invoices',grounded) is None
    grounded['sources'][0]['facts']['reconciliation']={'statement_imported':False}
    assert 'cannot be established' in status_answer('Which purchase invoices are unmatched?',grounded)['answer']
    from app.gst.report_details import project
    for kind,count in manifest['expected_report_rows'].items():
        _,rows,_,_=project(kind,invoices,profile,statement,True,manifest['period'])
        assert len(rows)==count,kind
    with pytest.raises(ValueError):
        parse_gstr2b((ROOT/'gstr2b-duplicate-invalid.json').read_text(),profile,manifest['period'])
