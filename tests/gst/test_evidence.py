import json

from app.gst.evidence import documents
from app.services.gst.assistant import grounded_context
from app.services.gst.evidence_search import search_evidence


def test_canonical_search_and_assistant_links_preserve_evidence_scope(invoice):
    invoice.extraction.raw_ref='gs://private-bucket/secret-object'
    evidence=documents([invoice],'2026-09')
    result=search_evidence(evidence,q=invoice.invoice_number,status='needs_review')
    assert result['total']==1
    assert result['results'][0]['href'].startswith('/bills?period=2026-09&invoice=')
    assert 'raw_ref' not in json.dumps(result)
    assert 'private-bucket' not in json.dumps(result)
    context=grounded_context({'period':'2026-09','source':'canonical','totals':{'cash_required':'0.00'}},evidence,'invoice')
    assert context['sources'][0]['label']=='Canonical financial summary'
    assert context['sources'][1]['href']==evidence[0]['href']
    assert context['sources'][1]['facts']['validation_status']=='needs_review'


def test_rejected_evidence_stays_distinct_from_confirmed(invoice):
    invoice.status='rejected'
    assert search_evidence(documents([invoice],'2026-09'),status='validated')['total']==0
