"""SQLite storage. Connections are short-lived and always enforce foreign keys."""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS delivery_slots (
    id INTEGER PRIMARY KEY, date TEXT NOT NULL,
    start_time TEXT NOT NULL, end_time TEXT NOT NULL,
    capacity INTEGER NOT NULL CHECK(capacity >= 0),
    enabled INTEGER NOT NULL CHECK(enabled IN (0, 1)),
    CHECK(start_time < end_time), UNIQUE(date, start_time, end_time)
);
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers(id),
    item TEXT NOT NULL, amount_cents INTEGER NOT NULL CHECK(amount_cents >= 0),
    payment_status TEXT NOT NULL CHECK(payment_status IN ('paid', 'pending', 'failed', 'refunded')),
    status TEXT NOT NULL CHECK(status IN ('pending', 'scheduled', 'dispatched', 'delivered', 'cancelled')),
    slot_id INTEGER REFERENCES delivery_slots(id)
);
CREATE INDEX IF NOT EXISTS orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS orders_slot ON orders(slot_id, status);
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    order_id INTEGER NOT NULL REFERENCES orders(id),
    action TEXT NOT NULL CHECK(action = 'reschedule_order'),
    old_slot_id INTEGER REFERENCES delivery_slots(id),
    new_slot_id INTEGER NOT NULL REFERENCES delivery_slots(id),
    old_status TEXT NOT NULL, new_status TEXT NOT NULL CHECK(new_status = 'scheduled'),
    confirmed INTEGER NOT NULL CHECK(confirmed = 1)
);
"""


def database_path():
    return Path(os.environ.get('ACTIONPILOT_DB_PATH', 'data/actionpilot.db'))


@contextmanager
def connect(path=None):
    db_path = Path(path) if path is not None else database_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def initialize(path=None):
    with connect(path) as conn:
        conn.executescript(SCHEMA)
