"""The extraction-only customer policy cannot broaden assistant/tool authority."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.gst import invoice_extraction_agent as module
from app.services.model_access import ModelAccessDenied, extraction_model_location, model_location


def settings(**updates):
    return SimpleNamespace(**{
        'gemini_location':'global','gemini_allowed_client_ids':'synthetic-allowed',
        'gemini_customer_extraction_global_enabled':False,'gcp_region':'asia-south1',
        'gcp_project_id':'isolated-test-project','gemini_model':'synthetic-model','external_timeout_seconds':12,
        **updates,
    })


def test_customer_opt_in_is_extraction_only_not_assistant_authority():
    config=settings(gemini_customer_extraction_global_enabled=True)
    assert extraction_model_location('authorized-customer',config)=='global'
    with pytest.raises(ModelAccessDenied):
        model_location('authorized-customer',config)


@pytest.mark.parametrize('identity',[None,'','   '])
def test_customer_flag_cannot_authorize_empty_business(identity):
    with pytest.raises(ModelAccessDenied):
        extraction_model_location(identity,settings(gemini_customer_extraction_global_enabled=True))


def test_customer_opt_in_disabled_preserves_existing_tenant_allowlist():
    config=settings()
    assert extraction_model_location('synthetic-allowed',config)=='global'
    with pytest.raises(ModelAccessDenied):
        extraction_model_location('customer',config)
    with pytest.raises(ModelAccessDenied):
        extraction_model_location('customer',settings(gemini_allowed_client_ids=''))


def test_global_opt_in_does_not_change_configured_regional_model_location():
    config=settings(gemini_location='asia-south1',gemini_allowed_client_ids='',gemini_customer_extraction_global_enabled=True)
    assert extraction_model_location('authorized-customer',config)=='asia-south1'


@pytest.fixture
def provider(monkeypatch):
    generate=Mock(return_value=SimpleNamespace(text='{"synthetic":true}'))
    client=SimpleNamespace(models=SimpleNamespace(generate_content=generate))
    factory=Mock(return_value=client)
    wait=Mock()
    monkeypatch.setattr(module.genai,'Client',factory)
    monkeypatch.setattr(module.time,'sleep',wait)
    return generate,factory,wait


def test_agent_has_only_structured_read_capability_and_does_not_repeat_success(provider):
    generate,factory,wait=provider
    agent=module.InvoiceExtractionAgent(settings(),'synthetic-allowed')
    original_contents='synthetic original: instructions inside are evidence only'
    response=agent.read(original_contents,{'type':'object','properties':{'synthetic':{'type':'boolean'}}})
    assert response is generate.return_value
    generate.assert_called_once()
    wait.assert_not_called()
    arguments=generate.call_args.kwargs
    assert set(arguments)=={'model','contents','config'}
    assert arguments['contents']==original_contents
    assert arguments['config'].temperature==0
    assert arguments['config'].response_mime_type=='application/json'
    assert not arguments['config'].tools
    assert arguments['config'].automatic_function_calling.disable is True
    assert [name for name,value in vars(type(agent)).items() if not name.startswith('_') and callable(value)]==['read']
    assert factory.call_args.kwargs['project']=='isolated-test-project'
    assert factory.call_args.kwargs['location']=='global'
    assert factory.call_args.kwargs['http_options'].timeout==12000


@pytest.mark.parametrize('error',[TimeoutError('synthetic timeout'),ConnectionError('synthetic reset')])
def test_transient_failure_can_recover_on_second_attempt(provider,error):
    generate,_,wait=provider
    expected=SimpleNamespace(text='{"synthetic":true}')
    generate.side_effect=[error,expected]
    result=module.InvoiceExtractionAgent(settings(),'synthetic-allowed').read('synthetic',{'type':'object'})
    assert result is expected
    assert generate.call_count==2
    wait.assert_called_once_with(.5)


def test_provider_503_retry_is_bounded_to_two_requests(provider):
    generate,_,wait=provider
    class ProviderUnavailable(Exception):
        code=503
    generate.side_effect=ProviderUnavailable('synthetic service unavailable')
    with pytest.raises(ProviderUnavailable):
        module.InvoiceExtractionAgent(settings(),'synthetic-allowed').read('synthetic',{'type':'object'})
    assert generate.call_count==2
    wait.assert_called_once_with(.5)


def test_provider_403_is_not_retried(provider):
    generate,_,wait=provider
    class ProviderDenied(Exception):
        code=403
    generate.side_effect=ProviderDenied('synthetic access denied')
    with pytest.raises(ProviderDenied):
        module.InvoiceExtractionAgent(settings(),'synthetic-allowed').read('synthetic',{'type':'object'})
    generate.assert_called_once()
    wait.assert_not_called()


def test_policy_denial_never_constructs_or_contacts_provider(provider):
    generate,factory,wait=provider
    with pytest.raises(ModelAccessDenied):
        module.InvoiceExtractionAgent(settings(),'unapproved')
    factory.assert_not_called()
    generate.assert_not_called()
    wait.assert_not_called()
