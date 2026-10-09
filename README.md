# ActionPilot — AI customer support demo

Python 3.11+, Streamlit, SQLite, the official OpenAI Python SDK, and pytest.
Milestone 2 adds conversational order lookup, payment status checks, and delivery
reschedule proposals to the existing manual support and read-only admin views.
All 5 customers and 10 orders are synthetic. No payment processing is included.

## Run

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python -m actionpilot.seed
streamlit run app.py
```

The app initializes and seeds an empty database on first launch. Seeding preserves
existing data. Storage defaults to `data/actionpilot.db`. To start a fresh demo,
stop the app, remove this generated database file, and restart. Initial seeding
creates enabled, full, disabled, and zero-capacity slots for the next three days
in Baku time. No database migration is needed from milestone 1.

## Product workspace

The app opens on **Home**, with a live, read-only preview of the selected synthetic
customer's first order and tomorrow's delivery availability. **Launch AI Assistant**
opens chat alongside the existing manual order controls; **Explore Dashboard** opens
owned order cards, actual order counts and delivery planning. Both calls to action
use the same Streamlit application.

The sidebar connects **Home**, **AI Assistant**, **Dashboard** and **Admin**.
Customer selection carries across pages. Changing customers clears the previous
chat and pending proposal, including when switching from Home or Admin. Navigating
between pages for the same customer preserves chat and proposals; the service still
rejects a stale proposal if an order changes before confirmation. Admin remains
read only and shows all synthetic demo records with committed reschedule audit logs.

The shared dark design uses local CSS and native Streamlit widgets, with no external
fonts, frontend framework or extra runtime dependencies. On mobile, panels stack
with the assistant first and navigation available through Streamlit's sidebar.
Amounts remain labeled in cents because the database does not specify a currency.

Captured desktop/mobile views are in [docs/screenshots](docs/screenshots/README.md).

## Enable real AI chat

Set `OPENAI_API_KEY` in the process environment, or in the gitignored
`.streamlit/secrets.toml` file:

```toml
OPENAI_API_KEY = "your-key-here"
```

Do not commit credentials. The environment takes precedence over Streamlit
secrets. `.env.example` documents configuration; `.env` files are not auto-loaded.
No API key is needed for manual support, admin views, or tests.

Optional environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `OPENAI_MODEL` | `gpt-4o-mini` | Cost-efficient OpenAI model with tool calling; configure another supported model if needed for your account. |
| `ACTIONPILOT_DB_PATH` | `data/actionpilot.db` | SQLite database path. |

The agent uses `OpenAI.chat.completions.create` with strict function schemas.
It sends the customer's chat and scoped synthetic order/slot observations to
OpenAI. Requests have a 20-second timeout, no automatic retries, at most six
model rounds per turn, and up to six complete turns of API conversation history.
API errors (including invalid credentials, rate limits, connectivity, or model
access problems) are sanitized and displayed without printing keys or raw errors.
If the key is missing, chat is disabled and manual support remains available.

## Demo

1. Select **Demo Customer 1** in the Home preview, then **Launch AI Assistant**.
   The sidebar also lets you choose the demo session's customer context.
2. In chat, try “Show my orders”, then “Is order 1 paid?”
3. Try “What delivery slots are available tomorrow?”
4. Try “Move order 1 to tomorrow's morning delivery slot”.
5. Review the exact order, date and time, then click **Confirm delivery change**.
   Until that click, nothing is written. The Admin view shows the committed order
   and its audit record. **Cancel proposal** discards the proposal without changing
   the order.

The manual selector, order details, payment status, reschedule form, and read-only
Admin view from milestone 1 are preserved. Tomorrow's midday slot starts full,
the afternoon slot is disabled, and the evening slot has zero capacity. Dispatched,
delivered and cancelled orders demonstrate blocked transitions.

## Authorization and confirmation

The customer selector simulates authenticated customer context for this hackathon
MVP; it is not production authentication. The application binds the agent to that
server-side customer ID. Every order tool calls the existing ownership-scoped
service with that ID. No tool accepts a `customer_id`, `confirmed`, or SQL argument.
The model cannot select another customer's context or execute a database mutation.
Switching customers discards the previous chat transcript, agent and proposal.

Explicit requests for another demo customer and access-permission questions are
answered by the application before calling the model or reading orders. The reply
identifies the selected customer and explains the demo selector's session scope.
Normal order replies also identify that scope, so selected-customer results cannot
silently appear to belong to a requested foreign customer. Common numbered,
spelled-out and ordinal demo customer references are recognized conservatively;
ownership-scoped service queries remain the authorization boundary for all wording.

The model may use only `get_access_scope`, `list_orders`, `get_order`, `get_payment_status`,
`get_available_slots`, `propose_reschedule`, and `cancel_reschedule`. Unknown tools,
extra arguments, malformed JSON, invalid IDs and dates are rejected. IDs must fit
SQLite's positive signed 64-bit range; tool arguments are limited to 4,096 characters. Tools return
only scoped records or safe errors. The application renders readable replies from
validated tool results rather than displaying model-generated claims about facts
or completed actions. `get_access_scope` takes no arguments and renders the trusted
application customer context. When the model requests no tool, chat explains the
actual customer scope, shows supported tasks
and requests an order/date as needed. This keeps replies grounded in the database.

A proposal holds the order and delivery window reviewed by the user and a random
one-use token in the server session. **Confirm delivery change** consumes that
token and calls the existing transactional rescheduling service. Typed “yes” or
“confirm” cannot execute it. New chat requests invalidate old proposals; they may
prepare a fresh proposal that needs a new review. Chat cancellation cancels only
the proposal, never the order. Repeated, cancelled, wrong and stale tokens cannot
execute. Failed execution also consumes the proposal, requiring a fresh review.

Inside `BEGIN IMMEDIATE`, the service checks ownership, current status, target
availability/date and capacity again. It also checks that the order assignment
and delivery window still match the reviewed proposal. Concurrent changes or a
slot filling between proposal and confirmation are safely rejected. The order
update and audit log commit atomically. Only after commit does the app display
“Database confirmed”. Confirmation invokes no LLM call.

## Existing service API and rules

Functions in `actionpilot/service.py`:

- `get_order(customer_id, order_id)` returns an owned order dictionary.
- `get_payment_status(customer_id, order_id)` returns stored payment status.
- `get_available_slots(date)` accepts `YYYY-MM-DD`, returning enabled, non-full
  slots with remaining capacity; past dates return an empty list.
- `reschedule_order(customer_id, order_id, slot_id, confirmed)` requires literal
  boolean `True`, and returns the committed order. Optional keyword-only
  `expected_order` and `expected_slot` guard the AI proposal against stale data.

Allowed transitions are `pending → scheduled` and `scheduled → scheduled`.
Dispatched, delivered and cancelled orders cannot move. Payment status is read
only and does not gate rescheduling. Same-slot assignments are rejected without
an audit entry. Pending/scheduled/dispatched orders consume capacity;
delivered/cancelled orders do not. Moving an order releases old capacity because
occupancy is computed from current orders. Asia/Baku date eligibility permits
same-day slots; intraday dispatch cutoffs are outside this MVP.

Foreign keys and CHECK constraints enforce referential integrity and stored values.
Business rules apply through the service; manual SQL is not an action interface.
Audit logs record successful reschedules, not rejected attempts. Database failures
roll back the order and audit log together.

## Test

See [BACKEND_TESTING.md](BACKEND_TESTING.md) for reproducible backend checks,
security coverage and the demo authentication/frontend limitations.

```bash
python -m pytest -q
```

Tests run in isolated temporary SQLite databases without an OpenAI key or network
access. Milestone 1 service/UI tests are preserved. Milestone 2 tests mock typed
OpenAI responses and the SDK's HTTP transport, covering scoped reads, invalid and
unauthorized tools, proposals, unavailable slots, one-use confirmation,
cancellation, stale execution state, rollback, API/configuration failures, bounded
loops, context retention, and the Streamlit chat/confirm/cancel/customer-switch
flow. `TEST_RESULTS.txt` records the actual verification run. A live OpenAI request
requires a valid key, model access and network access to `api.openai.com`.

## Structure

```text
app.py                     Streamlit manual/customer/admin interface
 actionpilot/
   db.py                   SQLite schema and connection lifecycle
   seed.py                 5 synthetic customers, 10 orders, 12 slots
   service.py              ownership checks and transactional actions
   agent.py                OpenAI tool loop, validation and confirmation state
   chat_ui.py              chat interface and server-side customer binding
   views.py                Home, assistant, dashboard and admin page views
   ui.py                   reusable cards, badges, icons and navigation helpers
   dashboard.css           shared responsive dark design system
 tests/
   test_service.py         existing operation and concurrency tests
   test_agent.py           mocked AI and SDK transport tests
   test_app.py             manual and AI Streamlit interface tests
 requirements.txt          Streamlit, pytest, official OpenAI SDK
 pytest.ini                test discovery/import configuration
 .env.example              safe configuration template
 .streamlit/config.toml     native Streamlit dark theme
 docs/screenshots/          actual UI captures, including a labeled mocked AI test
 TEST_RESULTS.txt          actual verification results
 .gitignore                excludes data, environments and secrets
```

## Team and deployment handoff

See [TEAM_WORKFLOW.md](TEAM_WORKFLOW.md) for branch ownership and stable interfaces,
[MILESTONE_FILE_MAP.md](MILESTONE_FILE_MAP.md) for verified milestone provenance,
[DEPLOYMENT.md](DEPLOYMENT.md) for the combined Streamlit release workflow, and
[SETUP_VERIFICATION.md](SETUP_VERIFICATION.md) for actual setup verification.
These additions are prepared on `feature/deploy` for human review; they do not
automatically merge code or deploy the public demo.
