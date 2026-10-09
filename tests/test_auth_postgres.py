"""Opt-in tests against a dedicated disposable PostgreSQL database with TLS."""
from concurrent.futures import ThreadPoolExecutor
import os
from uuid import uuid4

import pytest

from actionpilot.auth import AccountStore, AuthError

pytestmark = pytest.mark.skipif(not os.environ.get('AUTH_TEST_DATABASE_URL'),
                               reason='Set AUTH_TEST_DATABASE_URL to a disposable TLS PostgreSQL database')
PASSWORD = 'correct horse battery staple'


def _store():
    return AccountStore(database_url=os.environ['AUTH_TEST_DATABASE_URL'])


def test_postgres_signup_persistence_duplicate_and_login():
    store = _store()
    email = f'{uuid4().hex}@example.com'
    assert store.sign_up(email, PASSWORD, PASSWORD) == email
    assert _store().login(email.upper(), PASSWORD) == email
    with pytest.raises(AuthError, match='already exists'):
        _store().sign_up(email, PASSWORD, PASSWORD)
    with pytest.raises(AuthError, match='Incorrect'):
        _store().login(email, 'wrong')
    with store._connection() as conn:
        hashed = conn.execute('SELECT password_hash FROM auth_users WHERE email = %s', (email,)).fetchone()[0]
        assert hashed.startswith('$argon2id$') and PASSWORD not in hashed
        assert conn.pgconn.ssl_in_use is True


def test_postgres_registration_race():
    email = f'{uuid4().hex}@example.com'
    def signup(_):
        try:
            return _store().sign_up(email, PASSWORD, PASSWORD)
        except AuthError as error:
            return str(error)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(signup, range(2)))
    assert results.count(email) == 1
    assert sum('already exists' in result for result in results) == 1


def test_postgres_throttle_survives_new_connections():
    email = f'{uuid4().hex}@example.com'
    _store().sign_up(email, PASSWORD, PASSWORD)
    for _ in range(5):
        with pytest.raises(AuthError, match='Incorrect'):
            _store().login(email, 'wrong')
    with pytest.raises(AuthError, match='Too many'):
        _store().login(email, PASSWORD)


def test_streamlit_signup_and_login_use_postgres(tmp_path, monkeypatch):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv('ACTIONPILOT_DB_PATH', str(tmp_path / 'demo.db'))
    email = f'{uuid4().hex}@example.com'
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'))
    app.secrets['AUTH_DATABASE_URL'] = os.environ['AUTH_TEST_DATABASE_URL']
    app.run()
    assert not app.exception
    app.text_input(key='signup_email').set_value(email)
    app.text_input(key='signup_password').set_value(PASSWORD)
    app.text_input(key='signup_confirmation').set_value(PASSWORD)
    app.button(key='FormSubmitter:signup_form-Create account').click().run()
    assert not app.exception and app.success
    app.text_input(key='signin_email').set_value(email)
    app.text_input(key='signin_password').set_value(PASSWORD)
    app.button(key='FormSubmitter:login_form-Log in').click().run()
    assert not app.exception and app.session_state['logged_in'] is True
    assert app.session_state['user_email'] == email and app.session_state['page'] == 'Home'
    assert _store().login(email, PASSWORD) == email
