from types import SimpleNamespace
from unittest.mock import Mock, MagicMock
import pytest
from fastapi import HTTPException
from app.services import auth_identity, auth_mail


@pytest.mark.parametrize('usable,expected', [(True,'provider_accepted'),(False,'expired')])
def test_expired_links_never_report_acceptance(monkeypatch, usable, expected):
    repo=Mock()
    repo.table.side_effect=lambda name:'project.finance.'+name
    repo.query.side_effect=[[{'status':'pending','purpose':'verify','email':'approved@example.test'}],
                            [],[{'id':'u','email_verified':False}],[],[1] if usable else [],[]]
    monkeypatch.setattr(auth_mail,'ready',lambda:SimpleNamespace(app_secret_key='s'*32))
    sender=Mock()
    monkeypatch.setattr(auth_identity,'send_link',sender)
    auth_mail.process(repo,'id')
    assert sender.call_count==int(usable)
    assert {p.name:p.value for p in repo.query.call_args.args[1]}['status']==expected


@pytest.mark.parametrize('status',['provider_accepted','expired','ignored','sent'])
def test_terminal_mail_not_resent(monkeypatch,status):
    repo=Mock();repo.table.return_value='project.finance.auth_outbox'
    repo.query.return_value=[{'status':status}]
    monkeypatch.setattr(auth_mail,'ready',lambda:None)
    auth_mail.process(repo,'id')
    assert repo.query.call_count==1


@pytest.mark.parametrize('refused',[{}, {'approved@example.test':(550,b'rejected')}])
def test_smtp_acceptance_is_not_delivery(monkeypatch,refused):
    settings=SimpleNamespace(smtp_sender='ai@example.test',smtp_host='smtp.example.test',
                             smtp_port=587,smtp_username='u',smtp_password='test')
    monkeypatch.setattr(auth_identity,'delivery_ready',lambda:settings)
    transport=MagicMock()
    smtp=transport.return_value.__enter__.return_value
    smtp.send_message.return_value=refused
    monkeypatch.setattr(auth_identity.smtplib,'SMTP',transport)
    if refused:
        with pytest.raises(HTTPException):auth_identity.send_email('approved@example.test','Test','Test')
    else:
        result=auth_identity.send_email('approved@example.test','Test','Test')
        assert result['status']=='provider_accepted'
        assert result['message_id'] and result['inbox_delivery_confirmed'] is False
        message = smtp.send_message.call_args.args[0]
        assert message['Date']
        assert message['Message-ID'] == result['message_id']


def test_smtp_timeout_is_retryable_and_does_not_log_link(monkeypatch, caplog):
    settings=SimpleNamespace(smtp_sender='ai@example.test',smtp_host='smtp.example.test',
                             smtp_port=587,smtp_username='u',smtp_password='not-a-real-secret')
    monkeypatch.setattr(auth_identity,'delivery_ready',lambda:settings)
    monkeypatch.setattr(auth_identity.smtplib,'SMTP',Mock(side_effect=TimeoutError('private provider details')))
    with pytest.raises(HTTPException) as exc:
        auth_identity.send_email('approved@example.test','Verify','private-token-value')
    assert exc.value.status_code == 503
    assert 'smtp_dispatch_failed' in caplog.text
    for sensitive in ['private-token-value','not-a-real-secret','private provider details','approved@example.test']:
        assert sensitive not in caplog.text


@pytest.mark.parametrize('purpose,path',[('verify','verify-email'),('reset','reset-password')])
def test_v3_links_use_correct_frontend_and_fragment(monkeypatch,purpose,path):
    base='https://gst-easy-v3-web-foovqasysa-el.a.run.app'
    monkeypatch.setattr(auth_identity,'delivery_ready',lambda:SimpleNamespace(auth_public_url=base))
    send=Mock()
    monkeypatch.setattr(auth_identity,'send_email',send)
    auth_identity.send_link('approved@example.test','synthetic-token',purpose)
    body=send.call_args.args[2]
    assert base+'/'+path+'#token=synthetic-token' in body
    assert '30 minutes' in body
    assert '?token=' not in body
    assert 'gst-easy-v2' not in body
