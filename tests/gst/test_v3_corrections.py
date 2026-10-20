from decimal import Decimal
import pytest
from fastapi import HTTPException
from app.gst.comparison import compare_invoice, price_breakdown
from app.gst.correction import transition


@pytest.mark.parametrize('inclusive,price,discount',[(True,'118','0'),(False,'100','0'),(True,'129.80','11.80')])
def test_price_bases(inclusive,price,discount):
    result=price_breakdown(price,'18',inclusive,discount)
    assert result['taxable_value']=='100.00' and result['gst']=='18.00'
    assert result['legal_rate_verified'] is False


@pytest.mark.parametrize('value',[float('nan'),'NaN','Infinity','-1'])
def test_invalid_price(value):
    with pytest.raises(ValueError):price_breakdown(value,'18')


def test_comparison_preserves_evidence(invoice):
    original=invoice.model_copy(deep=True)
    invoice.line_items[0].cgst+=Decimal('100')
    result=compare_invoice(invoice,original)
    assert result['rows'][0]['classification'] in {'AMOUNT_MISMATCH','TAX_HEAD_MISMATCH'}
    assert result['approved_gst_amount'] is None
    assert result['legal_rate_verified'] is False
    assert original.line_items[0].cgst!=invoice.line_items[0].cgst


def test_rejected_correction_states_remain_financially_excluded(invoice):
    invoice.status='rejected';invoice.correction_state='rejected'
    requested=transition(invoice,'request-correction','maker','Correct the source transcription')
    assert requested.status=='rejected' and requested.version==invoice.version+1
    with pytest.raises(HTTPException):transition(requested,'resubmit','maker','Ready for review')
    requested.correction_state='corrected'
    submitted=transition(requested,'resubmit','maker','Corrected against original evidence')
    assert submitted.status=='needs_review' and submitted.correction_state=='resubmitted'
    assert submitted.extraction.raw_ref==invoice.extraction.raw_ref
    with pytest.raises(HTTPException):transition(submitted,'resubmit','maker','Repeated resubmission')


def test_rejection_reason_required(invoice):
    invoice.status='rejected'
    with pytest.raises(HTTPException):transition(invoice,'request-correction','u',' ')
