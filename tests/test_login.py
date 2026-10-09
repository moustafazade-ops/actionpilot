"""Streamlit account flow tests; no SMTP, secrets or remote services needed."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

from actionpilot.auth import AccountStore

PASSWORD = 'correct horse battery staple'
APP = str(Path(__file__).resolve().parents[1] / 'app.py')


def _app(tmp_path, monkeypatch):
    monkeypatch.setenv('ACTIONPILOT_DB_PATH', str(tmp_path / 'demo.db'))
    app = AppTest.from_file(APP, default_timeout=15)
    app.secrets['AUTH_SQLITE_PATH'] = str(tmp_path / 'accounts.db')
    return app.run()


def _signup(app, email='person@gmail.com', password=PASSWORD, confirmation=PASSWORD):
    app.text_input(key='signup_email').set_value(email)
    app.text_input(key='signup_password').set_value(password)
    app.text_input(key='signup_confirmation').set_value(confirmation)
    app.button(key='FormSubmitter:signup_form-Create account').click().run()
    assert not app.exception


def _login(app, email='person@gmail.com', password=PASSWORD):
    app.text_input(key='signin_email').set_value(email)
    app.text_input(key='signin_password').set_value(password)
    app.button(key='FormSubmitter:login_form-Log in').click().run()
    assert not app.exception


def test_login_gate_signup_login_session_and_logout(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    assert not app.exception and not app.selectbox and not app.chat_input
    assert [tab.label for tab in app.tabs] == ['Login', 'Sign Up']
    assert not (tmp_path / 'demo.db').exists()
    _signup(app)
    assert any('Account created' in message.value for message in app.success)
    assert 'logged_in' not in app.session_state
    assert not any(i.value for i in app.text_input if 'password' in (i.key or '') or i.key == 'signup_confirmation')
    _login(app, password='incorrect')
    assert app.error[0].value == 'Incorrect email or password.'
    _login(app)
    assert app.session_state['logged_in'] is True
    assert app.session_state['user_email'] == 'person@gmail.com'
    assert app.session_state['page'] == 'Home'
    assert any('person@gmail.com' in caption.value for caption in app.caption)
    assert not any(key in app.session_state for key in ('signin_password', 'signup_password', 'signup_confirmation'))
    next(b for b in app.button if b.label == 'Explore Dashboard').click().run()
    assert not app.exception and app.session_state['page'] == 'Dashboard'
    assert app.session_state['logged_in'] is True
    app.session_state['support_chat'] = {'pending': 'private test state'}
    next(b for b in app.button if b.label == 'Sign out').click().run()
    assert not app.exception and not app.selectbox and not app.chat_input
    assert 'logged_in' not in app.session_state and 'user_email' not in app.session_state
    assert 'support_chat' not in app.session_state
    # Account persists when the Streamlit session is entirely new.
    other = _app(tmp_path, monkeypatch)
    _login(other)
    assert other.session_state['logged_in'] is True


def test_signup_validation_and_duplicate_feedback(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    _signup(app, email='bad-email')
    assert 'valid email' in app.error[0].value
    _signup(app, confirmation='different password')
    assert 'do not match' in app.error[0].value
    _signup(app, password='short', confirmation='short')
    assert '15' in app.error[0].value
    _signup(app)
    _signup(app, email='PERSON@gmail.com')
    assert 'already exists' in app.error[0].value
    assert 'logged_in' not in app.session_state


def test_missing_config_fails_closed(tmp_path, monkeypatch):
    monkeypatch.delenv('AUTH_SQLITE_PATH', raising=False)
    monkeypatch.setenv('ACTIONPILOT_DB_PATH', str(tmp_path / 'demo.db'))
    app = AppTest.from_file(APP).run()
    assert not app.exception and not app.selectbox
    _login(app)
    assert 'not configured' in app.error[0].value
    assert not (tmp_path / 'demo.db').exists()


def test_legacy_email_code_session_cannot_bypass_password_login(tmp_path, monkeypatch):
    app = AppTest.from_file(APP)
    monkeypatch.setenv('ACTIONPILOT_DB_PATH', str(tmp_path / 'demo.db'))
    app.session_state['logged_in'] = True
    app.session_state['login_email'] = 'legacy@example.com'
    app.run()
    assert not app.exception and [tab.label for tab in app.tabs] == ['Login', 'Sign Up']
    assert 'logged_in' not in app.session_state
    assert not (tmp_path / 'demo.db').exists()


def test_database_error_does_not_expose_credentials_or_set_session(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    app.secrets['AUTH_DATABASE_URL'] = 'postgresql://private-user:private-password@127.0.0.1:1/accounts'
    _login(app)
    assert app.error[0].value == 'Account storage is temporarily unavailable. Please try again later.'
    assert 'logged_in' not in app.session_state


def test_logout_returns_to_home_for_next_account(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    _signup(app)
    _login(app)
    next(b for b in app.button if b.label == 'Explore Dashboard').click().run()
    next(b for b in app.button if b.label == 'Sign out').click().run()
    store = AccountStore(sqlite_path=tmp_path / 'accounts.db')
    store.sign_up('other@example.com', PASSWORD, PASSWORD)
    _login(app, email='other@example.com')
    assert app.session_state['page'] == 'Home'
    assert app.session_state['user_email'] == 'other@example.com'


def test_account_database_environment_and_secret_precedence(monkeypatch, tmp_path):
    from actionpilot import login
    environment_url = 'postgresql://test:test@localhost/environment?sslmode=require'
    secret_url = 'postgresql://test:test@localhost/secrets?sslmode=require'
    monkeypatch.setenv('AUTH_DATABASE_URL', environment_url)
    monkeypatch.setenv('AUTH_SQLITE_PATH', str(tmp_path / 'local.db'))
    monkeypatch.setattr(login.st, 'secrets', {})
    assert login.account_store().database_url == environment_url
    monkeypatch.setattr(login.st, 'secrets', {'AUTH_DATABASE_URL': secret_url})
    assert login.account_store().database_url == secret_url


def test_invalid_hosted_config_never_falls_back_to_sqlite(monkeypatch, tmp_path):
    import pytest
    from actionpilot import login
    from actionpilot.auth import AuthError
    path = tmp_path / 'accounts.db'
    monkeypatch.setattr(login.st, 'secrets', {
        'AUTH_DATABASE_URL': 'postgresql://test:test@localhost/accounts?sslmode=disable',
        'AUTH_SQLITE_PATH': str(path),
    })
    with pytest.raises(AuthError, match='TLS'):
        login.account_store()
    assert not path.exists()


def test_remember_me_restores_new_session_and_logout_revokes(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    _signup(app)
    app.checkbox(key='signin_remember').check()
    _login(app)
    token = app.session_state['remember_token']
    monkeypatch.setattr('actionpilot.login._remember_cookie', lambda: token)
    restored = _app(tmp_path, monkeypatch)
    assert not restored.exception
    assert restored.session_state['logged_in'] is True
    assert restored.session_state['user_email'] == 'person@gmail.com'
    assert not restored.text_input  # no password form on restored login
    next(b for b in restored.button if b.label == 'Sign out').click().run()
    assert not restored.exception
    assert 'logged_in' not in restored.session_state
    assert AccountStore(sqlite_path=tmp_path / 'accounts.db').restore_remember_session(token) is None
    other = _app(tmp_path, monkeypatch)
    assert 'logged_in' not in other.session_state
    assert [t.label for t in other.tabs] == ['Login', 'Sign Up']


def test_unchecked_remember_me_creates_no_persistent_session(tmp_path, monkeypatch):
    import sqlite3
    app = _app(tmp_path, monkeypatch)
    _signup(app)
    _login(app)
    assert 'remember_token' not in app.session_state
    with sqlite3.connect(tmp_path / 'accounts.db') as conn:
        assert conn.execute('SELECT count(*) FROM auth_remember_sessions').fetchone()[0] == 0


def test_failed_login_with_remember_me_does_not_create_token(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    _signup(app)
    app.checkbox(key='signin_remember').check()
    _login(app, password='incorrect')
    assert 'remember_token' not in app.session_state
    assert 'logged_in' not in app.session_state


def test_logo_replaces_text_brand_marks(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    assert any('alt="ActionPilot logo"' in m.value for m in app.markdown)
    _signup(app)
    _login(app)
    marks = [m.value for m in app.markdown if 'class="ap-brand"' in m.value]
    assert len(marks) == 3
    assert all('alt="ActionPilot logo"' in mark and '>AP</span>' not in mark for mark in marks)


def test_remembered_logout_can_retry_failed_revocation(tmp_path, monkeypatch):
    from actionpilot.auth import AuthError
    app = _app(tmp_path, monkeypatch)
    _signup(app)
    app.checkbox(key='signin_remember').check()
    _login(app)
    token = app.session_state['remember_token']
    with monkeypatch.context() as patch:
        def unavailable(self, token):
            raise AuthError('Account storage is temporarily unavailable. Please try again later.')
        patch.setattr(AccountStore, 'revoke_remember_session', unavailable)
        next(b for b in app.button if b.label == 'Sign out').click().run()
        assert not app.exception
        assert app.session_state['logged_in'] is True
        assert any('Could not revoke saved sign-in' in m.value for m in app.error)
    next(b for b in app.button if b.label == 'Sign out').click().run()
    assert 'logged_in' not in app.session_state
    assert AccountStore(sqlite_path=tmp_path / 'accounts.db').restore_remember_session(token) is None


def test_remember_cookie_uses_executable_component(monkeypatch):
    import actionpilot.login as login
    rendered = []
    monkeypatch.setattr(login.st, 'session_state', {'_cookie_write': 'a' * 64})
    monkeypatch.setattr(login.components, 'html',
                        lambda body, **kwargs: rendered.append((body, kwargs)))
    login._write_remember_cookie()
    assert len(rendered) == 1
    body, options = rendered[0]
    assert "document.cookie = 'actionpilot_remember=" + 'a' * 64 in body
    assert options == {'height': 0, 'width': 0}
