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
    with pytest.raises(ValueError):
        parse_gstr2b((ROOT/'gstr2b-duplicate-invalid.json').read_text(),profile,manifest['period'])
