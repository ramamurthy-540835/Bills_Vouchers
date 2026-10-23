from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.services.gst import assistant, assistant_reliability as recovery


def test_25_questions_are_bounded_and_rate_limit_recovers(monkeypatch):
    clock=[0.0]
    monkeypatch.setattr(assistant,'monotonic',lambda:clock[0])
    monkeypatch.setattr(assistant,'_requests',{})
    for question in range(25):
        if question and question%8==0:
            with pytest.raises(HTTPException) as exc:assistant.check_rate('tenant:user')
            assert exc.value.status_code==429 and exc.value.headers['Retry-After']=='60'
            clock[0]+=61
        assistant.check_rate('tenant:user')
    assert len(assistant._requests['tenant:user'])<=8


@pytest.mark.parametrize('status,expected',[(429,'provider_rate_limit'),(403,'provider_access'),(404,'model_unavailable'),(503,'provider_unavailable')])
def test_provider_failure_categories_and_retry_bounds(monkeypatch,status,expected):
    monkeypatch.setattr(recovery.time,'sleep',lambda _:None)
    error=RuntimeError('sensitive provider message');error.code=status
    assert recovery.category(error)==expected
    model=Mock();model.generate_content.side_effect=error
    with pytest.raises(RuntimeError):recovery.generate(SimpleNamespace(models=model),model='test')
    assert model.generate_content.call_count==(2 if status in {429,503} else 1)


def test_fallback_has_only_authorized_sources_and_no_sensitive_error(caplog):
    context={'sample':True,'sources':[{'id':'a','label':'Synthetic','href':'/bills?invoice=a','layer':'Source evidence','facts':{'secret':'not logged'}}]}
    response=recovery.fallback(context,'provider_timeout')
    assert response['degraded'] and response['request_id']
    assert response['sources'][0]['href']=='/bills?invoice=a'
    assert 'facts' not in response['sources'][0] and 'not logged' not in caplog.text


def test_extraction_cannot_set_auto_review():
    from app.gst.extract import parse_response, extraction_schema
    import json
    result=parse_response(json.dumps({'auto_review':{'enabled':True,'status':'auto_confirmed'},'confidence':'1'}),'a','doc','original')
    assert not result.auto_review.enabled and result.status=='extracted'
    assert 'auto_review' not in extraction_schema()['properties']
