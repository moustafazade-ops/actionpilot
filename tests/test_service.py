from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import sqlite3
import pytest
from actionpilot.db import connect
from actionpilot.seed import seed_demo
from actionpilot.service import (
    ActionError, admin_snapshot, get_available_slots, get_order,
    get_payment_status, reschedule_order, today,
)


@pytest.fixture(autouse=True)
def demo(tmp_path, monkeypatch):
    monkeypatch.setenv('ACTIONPILOT_DB_PATH', str(tmp_path / 'demo.db'))
    seed_demo()


def audit_count():
    return len(admin_snapshot()['audit_logs'])


def test_seed_is_synthetic_and_idempotent():
    seed_demo()
    with connect() as conn:
        assert conn.execute('SELECT COUNT(*) FROM customers').fetchone()[0] == 5
        assert conn.execute('SELECT COUNT(*) FROM orders').fetchone()[0] == 10
        assert all(r[0].endswith('@example.test') for r in conn.execute('SELECT email FROM customers'))


def test_owned_order_and_payment():
    assert get_order(1, 1)['item'] == 'Demo Item 1'
    assert get_payment_status(1, 1) == 'paid'


@pytest.mark.parametrize('customer,order', [(2, 1), (1, 999), (999, 1)])
@pytest.mark.parametrize('operation', [get_order, get_payment_status])
def test_reads_enforce_ownership(customer, order, operation):
    with pytest.raises(ActionError, match='not found'):
        operation(customer, order)


def test_available_slots_filters_full_disabled_zero_capacity_and_past():
    slots = get_available_slots((today() + timedelta(days=1)).isoformat())
    assert [s['id'] for s in slots] == [1]
    assert slots[0]['remaining_capacity'] == 3  # dispatched counts, delivered does not
    assert get_available_slots((today() - timedelta(days=1)).isoformat()) == []
    assert get_available_slots((today() + timedelta(days=100)).isoformat()) == []


@pytest.mark.parametrize('value', ['bad', '2026-02-30', '20261010', None])
def test_invalid_date(value):
    with pytest.raises(ActionError, match='YYYY-MM-DD'):
        get_available_slots(value)


def test_confirmed_move_commits_and_audits():
    result = reschedule_order(1, 1, 5, True)
    assert result == get_order(1, 1)
    assert result['status'] == 'scheduled' and result['slot_id'] == 5
    log = admin_snapshot()['audit_logs'][0]
    assert (log['customer_id'], log['order_id'], log['old_slot_id'], log['new_slot_id']) == (1, 1, None, 5)
    assert (log['old_status'], log['new_status'], log['confirmed']) == ('pending', 'scheduled', 1)


def test_move_releases_old_capacity():
    reschedule_order(1, 2, 5, True)
    slots = get_available_slots((today() + timedelta(days=1)).isoformat())
    assert next(s for s in slots if s['id'] == 2)['remaining_capacity'] == 1


@pytest.mark.parametrize('confirmed', [False, None, 1, 'true'])
def test_explicit_boolean_confirmation(confirmed):
    with pytest.raises(ActionError, match='confirmation'):
        reschedule_order(1, 1, 5, confirmed)
    assert get_order(1, 1)['slot_id'] is None
    assert audit_count() == 0


@pytest.mark.parametrize('customer,order,slot,message', [
    (2, 1, 5, 'not found'), (1, 999, 5, 'not found'),
    (1, 1, 999, 'slot not found'), (1, 1, 2, 'full'),
    (1, 1, 3, 'unavailable'), (1, 1, 4, 'full'),
    (1, 2, 2, 'already assigned'), (2, 3, 5, 'Only pending'),
    (2, 4, 5, 'Only pending'), (3, 5, 5, 'Only pending'),
])
def test_invalid_mutations_leave_database_unchanged(customer, order, slot, message):
    before = admin_snapshot()
    with pytest.raises(ActionError, match=message):
        reschedule_order(customer, order, slot, True)
    assert admin_snapshot() == before


def test_past_slot_rejected():
    with connect() as conn:
        conn.execute('UPDATE delivery_slots SET date = ? WHERE id = 5', ((today() - timedelta(days=1)).isoformat(),))
    with pytest.raises(ActionError, match='unavailable'):
        reschedule_order(1, 1, 5, True)
    assert audit_count() == 0


def test_audit_failure_rolls_back_order():
    with connect() as conn:
        conn.execute("""CREATE TRIGGER reject_audit BEFORE INSERT ON audit_logs
                      BEGIN SELECT RAISE(ABORT, 'test failure'); END""")
    with pytest.raises(sqlite3.IntegrityError, match='test failure'):
        reschedule_order(1, 1, 5, True)
    assert get_order(1, 1)['slot_id'] is None
    assert audit_count() == 0


def test_concurrent_bookings_cannot_overfill():
    def book(customer, order):
        try:
            reschedule_order(customer, order, 6, True)  # capacity 1
            return 'success'
        except ActionError:
            return 'rejected'
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(book, 1, 1), pool.submit(book, 3, 6)]
        assert sorted(f.result() for f in futures) == ['rejected', 'success']
    assert audit_count() == 1
    with connect() as conn:
        assert conn.execute('SELECT COUNT(*) FROM orders WHERE slot_id = 6').fetchone()[0] == 1


def test_foreign_keys_and_status_constraints():
    with connect() as conn:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE orders SET status = 'bogus' WHERE id = 1")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute('UPDATE orders SET slot_id = 999 WHERE id = 1')
