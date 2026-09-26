import json
from decimal import Decimal
from types import SimpleNamespace
from app.gst.extract import extract
from app.gst.validate_invoice import validate_invoice


def test_mocked_vision_is_schema_parsed_and_low_confidence_review(monkeypatch,invoice,profile):
    import app.gst.extract as module
    payload=invoice.model_dump(mode='json')
    payload['confidence']='0.60'
    payload['client_id']='attacker'
    calls=[]
    def generate(**kwargs):
        assert kwargs['config'].temperature==0
        return SimpleNamespace(text=json.dumps(payload),usage_metadata=SimpleNamespace(prompt_token_count=12,candidates_token_count=7))
    monkeypatch.setattr(module.genai,'Client',lambda **kwargs:SimpleNamespace(models=SimpleNamespace(generate_content=generate)))
    result=extract(b'fake-image','bill.png','a','doc',profile,'gs://a/source',lambda a,b:calls.append((a,b)))[0]
    assert result.client_id=='a' and result.extraction.confidence==Decimal('0.60')
    assert 'low_confidence' in validate_invoice(result,profile).review_reasons
    assert 'low_confidence' not in validate_invoice(result,profile,human_review=True).review_reasons
    assert calls==[(12,7)]
