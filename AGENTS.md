# ActionPilot

Synthetic customer-support demo; preserve the working Streamlit interface.
Python 3.11+, SQLite, OpenAI SDK, pytest. Dependencies are pinned in requirements.txt.

- `app.py`: manual support and read-only demo admin; avoid edits unless essential
  and coordinate any such change with Magomed.
- `actionpilot/db.py`, `seed.py`: short-lived connections, schema, synthetic seed.
- `actionpilot/service.py`: customer-scoped queries and atomic confirmed writes.
- `actionpilot/agent.py`: model read/proposal tools; application-owned confirmation.
- `actionpilot/chat_ui.py`: binds agent to selected customer, renders chat controls.

Setup: `python3 -m venv .venv`, then
`.venv/bin/python -m pip install -r requirements.txt`.
Run: `.venv/bin/python -m actionpilot.seed`, `.venv/bin/streamlit run app.py`.
Test: `.venv/bin/python -m pytest -q` (isolated DBs and mocked OpenAI).
See `BACKEND_TESTING.md` for verification scope and limitations.

Scope all order reads/writes to the trusted customer ID. Never expose identity,
SQL or execution/confirmation flags as model tool arguments. Require literal True
for service confirmation and a one-use token for chat confirmation. Revalidate
ownership/status/window/capacity under BEGIN IMMEDIATE, commit order and audit
together, return success after commit. Cancellation must never write.

The customer selector and public admin view are demo features, not production
authentication/authorization. Same-day intraday cutoffs are not implemented.
Never commit keys, secrets, generated DBs or environments. Sanitize API errors.
