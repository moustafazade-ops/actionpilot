"""Idempotent synthetic demo seed; never overwrites existing orders."""
from datetime import timedelta
from actionpilot.db import connect, initialize
from actionpilot.service import today


def seed_demo():
    initialize()
    with connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        if conn.execute('SELECT COUNT(*) FROM customers').fetchone()[0]:
            return
        conn.executemany('INSERT INTO customers VALUES (?, ?, ?)', [
            (i, f'Demo Customer {i}', f'customer{i}@example.test') for i in range(1, 6)
        ])
        tomorrow = today() + timedelta(days=1)
        slots = []
        for offset in range(3):
            day = (tomorrow + timedelta(days=offset)).isoformat()
            for j, (start, end, capacity, enabled) in enumerate([
                ('09:00', '12:00', 4, 1), ('12:00', '15:00', 1, 1),
                ('15:00', '18:00', 3, 0), ('18:00', '21:00', 0, 1),
            ]):
                slots.append((offset * 4 + j + 1, day, start, end, capacity, enabled))
        conn.executemany('INSERT INTO delivery_slots VALUES (?, ?, ?, ?, ?, ?)', slots)
        statuses = ['pending', 'scheduled', 'dispatched', 'delivered', 'cancelled'] * 2
        payments = ['paid', 'pending', 'failed', 'paid', 'refunded'] * 2
        orders = []
        for i in range(1, 11):
            slot = 2 if i == 2 else (1 if i in (3, 4) else None)
            orders.append((i, (i + 1) // 2, f'Demo Item {i}', 1000 + i * 250,
                           payments[i - 1], statuses[i - 1], slot))
        conn.executemany('INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?)', orders)


if __name__ == '__main__':
    seed_demo()
    print('Synthetic demo database initialized (existing data preserved).')
