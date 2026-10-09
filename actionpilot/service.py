"""Ownership-scoped reads and transactional, explicitly confirmed mutations."""
from datetime import date as Date, datetime
from zoneinfo import ZoneInfo

from actionpilot.db import connect


class ActionError(ValueError):
    """An expected rejection safe to display to the demo user."""


MAX_SQLITE_ID = (1 << 63) - 1


def _validate_id(value, name):
    # SQLite coerces strings/floats/bools; enforce identity types before querying.
    if type(value) is not int or not 1 <= value <= MAX_SQLITE_ID:
        raise ActionError(f'{name} must be a positive signed 64-bit integer.')


def _parse_date(value):
    try:
        parsed = Date.fromisoformat(value)
        if parsed.isoformat() != value:
            raise ValueError
    except (ValueError, TypeError):
        raise ActionError('Date must be YYYY-MM-DD.') from None
    return parsed


def today():
    return datetime.now(ZoneInfo('Asia/Baku')).date()


def _order(conn, customer_id, order_id):
    _validate_id(customer_id, 'customer_id')
    _validate_id(order_id, 'order_id')
    row = conn.execute(
        'SELECT * FROM orders WHERE id = ? AND customer_id = ?',
        (order_id, customer_id),
    ).fetchone()
    if row is None:
        raise ActionError('Order not found for this customer.')
    return dict(row)


def get_order(customer_id, order_id):
    with connect() as conn:
        return _order(conn, customer_id, order_id)


def get_payment_status(customer_id, order_id):
    return get_order(customer_id, order_id)['payment_status']


# Dispatched orders still consume a slot; delivered/cancelled orders do not.
SLOT_QUERY = """
SELECT s.*, s.capacity - (
    SELECT COUNT(*) FROM orders o WHERE o.slot_id = s.id
    AND o.status IN ('pending', 'scheduled', 'dispatched')
) AS remaining_capacity
FROM delivery_slots s
"""


def get_available_slots(date):
    parsed = _parse_date(date)
    if parsed < today():
        return []
    with connect() as conn:
        rows = conn.execute(SLOT_QUERY + ' WHERE s.date = ? ORDER BY s.start_time', (date,))
        return [dict(row) for row in rows if row['enabled'] and row['remaining_capacity'] > 0]


def reschedule_order(customer_id, order_id, slot_id, confirmed, *, expected_order=None, expected_slot=None):
    if confirmed is not True:
        raise ActionError('Explicit confirmation is required.')
    _validate_id(customer_id, 'customer_id')
    _validate_id(order_id, 'order_id')
    _validate_id(slot_id, 'slot_id')
    with connect() as conn:
        # Serialize writers before checking capacity, including across app sessions.
        conn.execute('BEGIN IMMEDIATE')
        order = _order(conn, customer_id, order_id)
        if expected_order is not None and any(order[key] != expected_order[key] for key in ('status', 'slot_id')):
            raise ActionError('Order changed since the proposal. Prepare a new proposal.')
        if order['status'] not in ('pending', 'scheduled'):
            raise ActionError('Only pending or scheduled orders can be rescheduled.')
        slot = conn.execute(SLOT_QUERY + ' WHERE s.id = ?', (slot_id,)).fetchone()
        if slot is None:
            raise ActionError('Delivery slot not found.')
        if expected_slot is not None and any(slot[key] != expected_slot[key] for key in ('date', 'start_time', 'end_time')):
            raise ActionError('Delivery slot changed since the proposal. Prepare a new proposal.')
        if not slot['enabled'] or _parse_date(slot['date']) < today():
            raise ActionError('Delivery slot is unavailable.')
        if order['slot_id'] == slot_id:
            raise ActionError('Order is already assigned to this slot.')
        if slot['remaining_capacity'] <= 0:
            raise ActionError('Delivery slot is full.')
        conn.execute("UPDATE orders SET slot_id = ?, status = 'scheduled' WHERE id = ? AND customer_id = ?",
                     (slot_id, order_id, customer_id))
        conn.execute("""INSERT INTO audit_logs
            (customer_id, order_id, action, old_slot_id, new_slot_id, old_status, new_status, confirmed)
            VALUES (?, ?, 'reschedule_order', ?, ?, ?, 'scheduled', 1)""",
                     (customer_id, order_id, order['slot_id'], slot_id, order['status']))
        result = _order(conn, customer_id, order_id)
    # The connection context has committed before any success is returned.
    return result


def list_customers():
    with connect() as conn:
        return [dict(r) for r in conn.execute('SELECT * FROM customers ORDER BY id')]


def list_orders(customer_id):
    _validate_id(customer_id, 'customer_id')
    with connect() as conn:
        return [dict(r) for r in conn.execute('SELECT * FROM orders WHERE customer_id = ? ORDER BY id', (customer_id,))]


def admin_snapshot():
    with connect() as conn:
        return {
            'orders': [dict(r) for r in conn.execute('SELECT * FROM orders ORDER BY id')],
            'slots': [dict(r) for r in conn.execute(SLOT_QUERY + ' ORDER BY s.date, s.start_time')],
            'audit_logs': [dict(r) for r in conn.execute('SELECT * FROM audit_logs ORDER BY id DESC')],
        }
