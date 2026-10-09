"""Login tests use mocked SMTP; no real email or credentials."""
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from streamlit.testing.v1 import AppTest

import actionpilot.login as login


@pytest.fixture
def email_session(monkeypatch):
    state = {}
    monkeypatch.setattr(login.st, 'session_state', state)
    monkeypatch.setattr(login.st, 'secrets', {'EMAIL_USER': 'sender@gmail.com', 'EMAIL_PASS': 'test-app-password'})
    smtp = MagicMock()
    monkeypatch.setattr(login.smtplib, 'SMTP_SSL', smtp)
    smtp.return_value.__enter__.return_value.send_message.return_value = {}
    monkeypatch.setattr(login.time, 'time', lambda: 1000)
    return state, smtp


def test_send_uses_gmail_tls_and_saves_after_acceptance(email_session):
    state, smtp = email_session
    assert login.send_verification_code('  person@example.com  ')[0]
    args, kwargs = smtp.call_args
    assert args == ('smtp.gmail.com', 465)
    assert kwargs['timeout'] == 15 and kwargs['context'].check_hostname
    server = smtp.return_value.__enter__.return_value
    server.login.assert_called_once_with('sender@gmail.com', 'test-app-password')
    message = server.send_message.call_args.args[0]
    assert message['To'] == 'person@example.com'
    assert len(state['verification_code']) == 6 and state['verification_code'].isdigit()
    assert state['verification_code'] in message.get_content()
    assert state['verification_time'] == 1000
    assert state['verification_email'] == 'person@example.com'


@pytest.mark.parametrize('email', ['invalid', 'a@example.com\nBcc: b@example.com', '', 'a b@example.com'])
def test_invalid_email_never_sends(email_session, email):
    _, smtp = email_session
    assert not login.send_verification_code(email)[0]
    smtp.assert_not_called()


def test_missing_secrets_is_safe(email_session, monkeypatch):
    state, smtp = email_session
    monkeypatch.setattr(login.st, 'secrets', {})
    assert 'not configured' in login.send_verification_code('a@example.com')[1]
    assert 'verification_code' not in state
    smtp.assert_not_called()


@pytest.mark.parametrize('failure', [login.smtplib.SMTPAuthenticationError(535, b'private detail'), OSError('private detail')])
def test_failed_send_does_not_leave_a_verifiable_code(email_session, failure):
    state, smtp = email_session
    state['verification_code'] = '123456'
    smtp.return_value.__enter__.return_value.login.side_effect = failure
    ok, feedback = login.send_verification_code('a@example.com')
    assert not ok and 'private detail' not in feedback
    assert 'verification_code' not in state
    assert 'logged_in' not in state


def test_cooldown_and_new_code_invalidates_old_one(email_session, monkeypatch):
    state, smtp = email_session
    monkeypatch.setattr(login.secrets, 'randbelow', lambda n: 123456)
    login.send_verification_code('a@example.com')
    old = state['verification_code']
    assert not login.send_verification_code('b@example.com')[0]
    assert smtp.call_count == 1
    monkeypatch.setattr(login.time, 'time', lambda: 1060)
    monkeypatch.setattr(login.secrets, 'randbelow', lambda n: 654321)
    assert login.send_verification_code('b@example.com')[0]
    assert not login.verify_code('b@example.com', old)[0]


def test_correct_code_is_one_use_and_wrong_email_cannot_verify(email_session):
    state, _ = email_session
    login.send_verification_code('a@example.com')
    code = state['verification_code']
    assert not login.verify_code('b@example.com', code)[0]
    assert not state.get('logged_in')
    assert login.verify_code('a@example.com', code)[0]
    assert state['logged_in'] is True and state['login_email'] == 'a@example.com'
    assert 'verification_code' not in state
    assert not login.verify_code('a@example.com', code)[0]


def test_wrong_codes_exhaust_attempts(email_session):
    state, _ = email_session
    login.send_verification_code('a@example.com')
    for _ in range(5):
        ok, feedback = login.verify_code('a@example.com', '000000')
        assert not ok
    assert 'Too many' in feedback and 'verification_code' not in state
    assert not state.get('logged_in')


def test_five_minute_expiry(email_session, monkeypatch):
    state, _ = email_session
    login.send_verification_code('a@example.com')
    code = state['verification_code']
    monkeypatch.setattr(login.time, 'time', lambda: 1300)
    assert login.verify_code('a@example.com', code) == (False, 'Code expired')
    assert 'verification_code' not in state and not state.get('logged_in')


def test_login_gate_verify_dashboard_and_logout(tmp_path, monkeypatch):
    monkeypatch.setenv('ACTIONPILOT_DB_PATH', str(tmp_path / 'login.db'))
    monkeypatch.setattr(login.secrets, 'randbelow', lambda n: 234567)
    smtp = MagicMock()
    smtp.return_value.__enter__.return_value.send_message.return_value = {}
    monkeypatch.setattr(login.smtplib, 'SMTP_SSL', smtp)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'))
    app.secrets['EMAIL_USER'] = 'sender@gmail.com'
    app.secrets['EMAIL_PASS'] = 'test-app-password'
    app.run()
    assert not app.exception and not app.selectbox and not app.chat_input
    assert not (tmp_path / 'login.db').exists()  # gate runs before demo/database access
    app.text_input[0].set_value('a@example.com')
    next(b for b in app.button if b.label == 'Send code').click().run()
    assert not app.exception and app.success
    app.text_input[1].set_value('000000')
    next(b for b in app.button if b.label == 'Verify').click().run()
    assert 'Incorrect code' in app.error[0].value
    app.text_input[1].set_value('334567')
    next(b for b in app.button if b.label == 'Verify').click().run()
    assert not app.exception and app.session_state['logged_in'] is True
    next(b for b in app.button if b.label == 'Explore Dashboard').click().run()
    assert not app.exception and app.session_state['page'] == 'Dashboard'
    app.session_state['support_chat'] = {'pending': 'private test state'}
    next(b for b in app.button if b.label == 'Sign out').click().run()
    assert not app.exception and not app.selectbox and not app.chat_input
    assert 'logged_in' not in app.session_state and 'support_chat' not in app.session_state
