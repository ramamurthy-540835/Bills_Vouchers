import asyncio
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.services.gst import account, profiles, routes


@pytest.mark.parametrize('value,expected',[
    ('', ''), (' Example.COM/about ', 'https://example.com/about'),
    ('https://www.example.com/path?q=1#contact','https://www.example.com/path?q=1#contact'),
    ('http://example.com','http://example.com'),
])
def test_website_normalizes_without_network(value,expected):
    assert profiles.website_url(value)==expected


@pytest.mark.parametrize('value',[
    None,{},'javascript:alert(1)','https://user:password@example.com',
    'https://localhost','http://127.0.0.1','http://[::1]',
    'https://company.internal','https://company.local','https://example.com:8080',
    'https://exa mple.com','https://example.com/\nheader','https://example.com\\@other.com',
    'ftp://example.com','https://bad..com','https://-bad.com',
])
def test_invalid_website_rejected(value):
    with pytest.raises(ValueError):profiles.website_url(value)


def test_company_checks_never_convert_format_or_legacy_flag_to_verification():
    result=profiles.company_checks({'gstin':'33ABCDE1234F1Z7','gstin_verified':True,'website_url':'https://example.com'})
    assert result['gstin_format_valid']
    assert result['government_verification']=='not_connected'
    assert result['website_ownership_verified'] is False
    assert profiles.company_checks({'website_url':'javascript:alert(1)'})['website_url']==''


def test_legacy_profile_cannot_forge_government_verification():
    result=profiles.prepare_profile({'gstin':'33ABCDE1234F1Z7','legal_name':'Synthetic',
        'gstin_verified':True,'website_url':'example.com'},'client','actor')
    assert result['gstin_verified'] is False
    assert result['website_url']=='https://example.com'


class Request:
    def __init__(self,body):self.body=body
    async def json(self):return self.body


def test_website_save_is_versioned_audited_and_cannot_set_verification(monkeypatch):
    repo=Mock();repo.table.side_effect=lambda name:'test.'+name
    user=SimpleNamespace(id='owner',role='client')
    monkeypatch.setattr(account,'active_client',lambda *args:SimpleNamespace(id='own'))
    monkeypatch.setattr(account,'can',lambda *args:True)
    monkeypatch.setattr(account,'get_settings',lambda:SimpleNamespace(gst_bills_enabled=False))
    monkeypatch.setattr(account.Medallion,'profile',lambda *args:{'profile_id':'old','legal_name':'Company'})
    result=asyncio.run(account.save_profile(Request({'client_id':'own','profile_id':'old',
        'website_url':'example.com','gstin_verified':True}),repo,user))
    assert result['saved']
    sql,params=repo.query.call_args.args
    assert 'profile_audit' in sql and 'BEGIN TRANSACTION' in sql and '@website_url AS website_url' in sql
    assert 'TRUE AS gstin_verified' not in sql
    assert next(p.value for p in params if p.name=='website_url')=='https://example.com'
    repo.reset_mock()
    with pytest.raises(HTTPException) as error:
        asyncio.run(account.save_profile(Request({'client_id':'other','website_url':'example.com'}),repo,user))
    assert error.value.status_code==403
    repo.query.assert_not_called()


def test_legacy_writer_cannot_bypass_canonical_profile_transaction(monkeypatch):
    repo=Mock();user=SimpleNamespace(id='accountant',role='tax_admin')
    monkeypatch.setattr(routes,'get_settings',lambda:SimpleNamespace(gst_bills_enabled=True))
    monkeypatch.setattr(routes,'_client_or_403',lambda *args:'own')
    with pytest.raises(HTTPException) as error:
        asyncio.run(routes.upsert_client_profile(Request({'client_id':'own','gstin_verified':True}),repo,user))
    assert error.value.status_code==409
    repo.update.assert_not_called();repo.insert.assert_not_called()
