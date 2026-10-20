from datetime import date
from decimal import Decimal
import pytest

from app.gst.intake import normalize
from app.gst.source_reconciliation import reconcile


def source(invoice, **changes):
    record = {'source_record_id':'vendor-1','event_type':'invoice','source_version':'1',
              'supplier_gstin':invoice.supplier_gstin,'customer_gstin':invoice.recipient_gstin,
              'invoice_number':invoice.invoice_number,'invoice_date':invoice.invoice_date.isoformat(),
              'trip_id':'trip-1','taxable_amount':str(invoice.totals.taxable_value),
              **{key:str(getattr(invoice.totals,key)) for key in ('cgst','sgst','igst','cess','invoice_total')}}
    record.update(changes)
    return {'status':'staged','payload':normalize('vendor',record)}


def run(invoice, record, related=(), invoices=None):
    return reconcile([record],related,[invoice] if invoices is None else invoices,invoice.client_id,
                     invoice.invoice_date.isoformat()[:7])['records'][0]


def test_exact_match_does_not_mutate_or_duplicate_invoice(invoice):
    invoice.status='confirmed'
    before=invoice.model_dump()
    result=run(invoice,source(invoice))
    assert result['status']=='matched' and result['invoice_version']==invoice.version
    assert invoice.model_dump()==before


@pytest.mark.parametrize('changes,status',[
    ({'supplier_gstin':''},'insufficient_identity'),
    ({'invoice_date':'bad'},'insufficient_identity'),
    ({'invoice_number':'other'},'source_only'),
    ({'invoice_total':'1.00'},'details_mismatch'),
    ({'invoice_date':'2025-09-01'},'outside_period'),
])
def test_no_amount_only_or_incomplete_identity_matching(invoice,changes,status):
    assert run(invoice,source(invoice,**changes))['status']==status


def test_tax_heads_and_date_require_review(invoice):
    invoice.status='confirmed'
    record=source(invoice,cgst=str(invoice.totals.cgst+Decimal('1')),sgst=str(invoice.totals.sgst-Decimal('1')))
    result=run(invoice,record)
    assert result['status']=='details_mismatch'
    assert result['differences']['cgst']=='1.00'
    later=date(invoice.invoice_date.year,invoice.invoice_date.month,2)
    assert run(invoice,source(invoice,invoice_date=later.isoformat()))['status']=='details_mismatch'


def test_missing_tax_values_and_rejected_records_not_fully_matched(invoice):
    record=source(invoice);del record['payload']['cess']
    assert run(invoice,record)['status']=='incomplete_amounts'
    invoice.status='rejected'
    assert run(invoice,source(invoice))['status']=='rejected_invoice'


def test_ambiguous_canonical_identity_is_never_chosen(invoice):
    other=invoice.model_copy(update={'invoice_id':'other'})
    assert run(invoice,source(invoice),invoices=[invoice,other])['status']=='ambiguous_invoice'


def test_conflicting_and_newer_source_versions(invoice):
    first=source(invoice)
    conflict=source(invoice,invoice_total='1.00')
    assert run(invoice,first,[conflict])['status']=='source_conflict'
    newer=source(invoice,source_version='2')
    assert run(invoice,first,[newer])['status']=='superseded_source'
    first['status']='duplicate_or_conflict'
    assert run(invoice,first)['status']=='duplicate_source'


def test_driver_event_links_through_unique_invoice_not_amount(invoice):
    invoice.status='confirmed'
    driver={'status':'staged','payload':normalize('driver',{'source_record_id':'driver-1',
        'event_type':'trip','trip_id':'trip-1','payment_amount':'1.00'})}
    assert run(invoice,driver,[source(invoice)])['status']=='linked_event'
    assert run(invoice,driver)['status']=='unlinked_event'
    driver['payload']['booking_id']='unresolved-booking'
    assert run(invoice,driver,[source(invoice)])['status']=='ambiguous_reference'


def test_conflicted_source_reference_cannot_be_ignored(invoice):
    invoice.status='confirmed'
    driver={'status':'staged','payload':normalize('driver',{'source_record_id':'driver-1','event_type':'trip','trip_id':'trip-1'})}
    assert run(invoice,driver,[source(invoice),source(invoice,invoice_total='1.00')])['status']=='ambiguous_reference'


def test_tenant_boundary_is_defended(invoice):
    foreign=invoice.model_copy(update={'client_id':'foreign'})
    with pytest.raises(ValueError):
        run(invoice,source(invoice),invoices=[foreign])


def test_credit_note_never_matches_tax_invoice(invoice):
    assert run(invoice,source(invoice,event_type='credit_note'))['status']=='source_only'
