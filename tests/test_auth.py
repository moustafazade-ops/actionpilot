"""Real account storage and password checks against isolated databases."""
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from actionpilot.auth import AccountStore, AuthError, normalize_email

PASSWORD = 'correct horse battery staple'


@pytest.fixture
def store(tmp_path):
    return AccountStore(sqlite_path=tmp_path / 'accounts.db')


def test_signup_hashes_password_and_persists_across_store_instances(store):
    assert store.sign_up('  Person@Gmail.com ', PASSWORD, PASSWORD) == 'person@gmail.com'
    with sqlite3.connect(store.sqlite_path) as conn:
        email, hashed = conn.execute('SELECT email, password_hash FROM auth_users').fetchone()
    assert email == 'person@gmail.com' and hashed.startswith('$argon2id$')
    assert PASSWORD not in hashed
    reopened = AccountStore(sqlite_path=store.sqlite_path)
    assert reopened.login('PERSON@gmail.com', PASSWORD) == email


def test_duplicate_email_cannot_replace_original_password(store):
    store.sign_up('person@example.com', PASSWORD, PASSWORD)
    with pytest.raises(AuthError, match='already exists'):
        store.sign_up('PERSON@example.com', 'another secure password', 'another secure password')
    assert store.login('person@example.com', PASSWORD) == 'person@example.com'


@pytest.mark.parametrize('email', ['', 'a..b@gmail.com', 'a@example..com', 'not-email',
                                  'a@gmail.com\nBcc: b@gmail.com', 'a@localhost'])
def test_invalid_email_is_rejected(email):
    with pytest.raises(AuthError, match='valid email'):
        normalize_email(email)


@pytest.mark.parametrize('password,confirmation', [('short', 'short'),
    (PASSWORD, 'does not match'), ('a' * 129, 'a' * 129)])
def test_invalid_signup_writes_no_account(store, password, confirmation):
    with pytest.raises(AuthError):
        store.sign_up('a@example.com', password, confirmation)
    assert not store.sqlite_path.exists()


def test_bad_credentials_are_indistinguishable(store):
    store.sign_up('person@example.com', PASSWORD, PASSWORD)
    messages = []
    for email, password in [('unknown@example.com', PASSWORD), ('person@example.com', 'incorrect')]:
        with pytest.raises(AuthError) as error:
            store.login(email, password)
        messages.append(str(error.value))
    assert messages == ['Incorrect email or password.'] * 2


def test_rate_limit_survives_new_session_and_expires(store, monkeypatch):
    monkeypatch.setattr('actionpilot.auth.time.time', lambda: 1000)
    store.sign_up('person@example.com', PASSWORD, PASSWORD)
    for _ in range(5):
        with pytest.raises(AuthError, match='Incorrect'):
            store.login('person@example.com', 'incorrect')
    reopened = AccountStore(sqlite_path=store.sqlite_path)
    with pytest.raises(AuthError, match='Too many'):
        reopened.login('PERSON@example.com', PASSWORD)
    monkeypatch.setattr('actionpilot.auth.time.time', lambda: 1300)
    assert reopened.login('person@example.com', PASSWORD) == 'person@example.com'


def test_concurrent_signup_has_one_winner(store):
    def attempt(_):
        try:
            return store.sign_up('person@example.com', PASSWORD, PASSWORD)
        except AuthError as error:
            return str(error)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, range(2)))
    assert results.count('person@example.com') == 1
    assert sum('already exists' in result for result in results) == 1


def test_storage_failure_is_sanitized(tmp_path):
    store = AccountStore(sqlite_path=tmp_path)  # directory cannot be an SQLite database
    with pytest.raises(AuthError, match='temporarily unavailable') as error:
        store.login('person@example.com', PASSWORD)
    assert str(tmp_path) not in str(error.value)


def test_password_hash_is_salted_per_user(store):
    store.sign_up('one@example.com', PASSWORD, PASSWORD)
    store.sign_up('two@example.com', PASSWORD, PASSWORD)
    with sqlite3.connect(store.sqlite_path) as conn:
        hashes = conn.execute('SELECT password_hash FROM auth_users').fetchall()
    assert hashes[0] != hashes[1]


def test_login_upgrades_an_outdated_hash(store):
    from argon2 import PasswordHasher
    store.sign_up('person@example.com', PASSWORD, PASSWORD)
    old_hash = PasswordHasher(memory_cost=1024, time_cost=1, parallelism=1).hash(PASSWORD)
    with sqlite3.connect(store.sqlite_path) as conn:
        conn.execute('UPDATE auth_users SET password_hash = ?', (old_hash,))
    assert store.login('person@example.com', PASSWORD) == 'person@example.com'
    with sqlite3.connect(store.sqlite_path) as conn:
        upgraded = conn.execute('SELECT password_hash FROM auth_users').fetchone()[0]
    assert upgraded != old_hash and 'm=19456,t=2,p=1' in upgraded


def test_corrupt_stored_hash_has_safe_login_failure(store):
    store.sign_up('person@example.com', PASSWORD, PASSWORD)
    with sqlite3.connect(store.sqlite_path) as conn:
        conn.execute('UPDATE auth_users SET password_hash = ?', ('private corrupted hash',))
    with pytest.raises(AuthError, match='^Incorrect email or password.$'):
        store.login('person@example.com', PASSWORD)


def test_no_implicit_ephemeral_storage():
    with pytest.raises(AuthError, match='not configured'):
        AccountStore()


def test_postgres_refuses_insecure_transport():
    with pytest.raises(AuthError, match='TLS'):
        AccountStore(database_url='postgresql://user:secret@host/db?sslmode=disable')


def test_remember_token_is_hashed_restores_and_revokes(store):
    from hashlib import sha256
    store.sign_up('person@example.com', PASSWORD, PASSWORD)
    token = store.create_remember_session(store.login('person@example.com', PASSWORD))
    with sqlite3.connect(store.sqlite_path) as conn:
        digest = conn.execute('SELECT token_hash FROM auth_remember_sessions').fetchone()[0]
    assert digest == sha256(token.encode()).hexdigest() and digest != token
    reopened = AccountStore(sqlite_path=store.sqlite_path)
    assert reopened.restore_remember_session(token) == 'person@example.com'
    assert reopened.restore_remember_session('0' * 64) is None
    reopened.revoke_remember_session(token)
    assert store.restore_remember_session(token) is None


def test_remember_session_expires_at_30_days(store, monkeypatch):
    from actionpilot.auth import REMEMBER_SECONDS
    monkeypatch.setattr('actionpilot.auth.time.time', lambda: 1000)
    store.sign_up('person@example.com', PASSWORD, PASSWORD)
    token = store.create_remember_session('person@example.com')
    monkeypatch.setattr('actionpilot.auth.time.time', lambda: 1000 + REMEMBER_SECONDS - 1)
    assert store.restore_remember_session(token) == 'person@example.com'
    monkeypatch.setattr('actionpilot.auth.time.time', lambda: 1000 + REMEMBER_SECONDS)
    assert store.restore_remember_session(token) is None


def test_remember_session_rejects_changed_password_and_deleted_account(store):
    store.sign_up('person@example.com', PASSWORD, PASSWORD)
    token = store.create_remember_session('person@example.com')
    with sqlite3.connect(store.sqlite_path) as conn:
        conn.execute('UPDATE auth_users SET password_hash = ?', ('changed hash',))
    assert store.restore_remember_session(token) is None
    token = store.create_remember_session('person@example.com')
    with sqlite3.connect(store.sqlite_path) as conn:
        conn.execute('DELETE FROM auth_users')
    assert store.restore_remember_session(token) is None


@pytest.mark.parametrize('token', [None, '', 'not-a-token', '<script>', 'a' * 65, 'A' * 64])
def test_invalid_remember_cookie_never_opens_storage(store, token):
    assert store.restore_remember_session(token) is None
    store.revoke_remember_session(token)
    assert not store.sqlite_path.exists()
