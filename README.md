# ActionPilot — milestone 1

A small, deterministic customer support demo built with Python 3.11+, Streamlit,
SQLite and pytest. It retrieves owned orders, reports payment status, lists
available delivery slots, and commits explicitly confirmed delivery reschedules.
All customers and orders are synthetic. No LLM, OpenAI SDK, authentication, or
payment processing is included in this milestone.

## Run

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python -m actionpilot.seed
streamlit run app.py
```

The app also initializes and seeds an empty database on first launch. Seeding is
idempotent and preserves existing data. Default storage is `data/actionpilot.db`.
To start a fresh demo, stop the app and remove this generated file, then restart.
Slots are generated for the next three days in Baku time at initial seeding.

Optional custom storage: export `ACTIONPILOT_DB_PATH=/path/to/demo.db` before
running the app or seed command. `.env.example` documents this variable; `.env`
files are **not** automatically loaded. No API key is required.

## Demo flow

1. Select Demo Customer 1 and order #1 (pending, paid).
2. Inspect order details and payment status.
3. Select tomorrow's 09:00–12:00 slot, check the explicit confirmation box,
   then click **Reschedule delivery**.
4. Inspect the updated order and Admin view's audit log.
5. Customer 2's orders illustrate blocked dispatched/delivered statuses.
   Tomorrow's midday slot is full, the afternoon slot is disabled, and the
   evening slot has zero capacity; none is offered as available.

The customer selector and read-only Admin view are demo controls, not access
security. The service nevertheless scopes every order read and mutation to the
supplied customer ID. Missing and foreign-owned orders produce the same error.

## API and rules

Functions are in `actionpilot/service.py`:

- `get_order(customer_id, order_id)` returns an order dictionary.
- `get_payment_status(customer_id, order_id)` returns a stored payment status.
- `get_available_slots(date)` accepts `YYYY-MM-DD` and returns enabled, non-full
  slots with remaining capacity; past dates return an empty list.
- `reschedule_order(customer_id, order_id, slot_id, confirmed)` requires the
  literal boolean `True`, and returns the database-confirmed order after commit.

Only `pending → scheduled` and `scheduled → scheduled` reschedules are allowed.
Dispatched, delivered and cancelled orders cannot move. Payment status is read
only and does not gate rescheduling. Assigning the same slot is rejected without
an audit entry. Active pending/scheduled/dispatched orders consume capacity;
delivered/cancelled orders do not. Date eligibility uses Asia/Baku and permits
same-day slots (no intraday dispatch cutoff is modeled in this MVP).

`BEGIN IMMEDIATE` serializes SQLite writers before the capacity check. Order
mutation and success audit insertion commit atomically; errors roll back both.
Moving an order automatically releases its previous slot because occupancy is
computed from current orders. Database foreign keys and CHECK constraints enforce
referential integrity and allowed stored values. Business rules apply through the
service; direct manual SQL is not a supported action interface. Audit logs record
successful reschedules, not denied attempts. SQLite lock or commit errors propagate
and the interface never reports success for them.

## Test

```bash
python -m pytest -q
```

Tests use isolated temporary databases, covering ownership, payment retrieval,
slot filtering, status restrictions, strict confirmation, atomic audit rollback,
capacity release, concurrent bookings, schema constraints, and the Streamlit
confirmation flow. No network access or external API is needed to run tests.

## Structure

```text
app.py                     Streamlit customer/admin interface
 actionpilot/              SQLite and business operations
   db.py                   schema, connection lifecycle
   seed.py                 5 customers, 10 orders, 12 slots
   service.py              scoped reads and transactional rescheduling
 tests/                    pytest service and Streamlit tests
 requirements.txt          Streamlit and pytest only
 pytest.ini                test discovery/import configuration
 .env.example              optional database path
 .gitignore                excludes local data, environments and secrets
```

Milestone 2 can add OpenAI tool calling on top of these service functions.
