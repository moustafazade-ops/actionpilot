# Deployment and integration handoff

## Observed deployment status

The inspected main has an entry point `app.py`, pinned `requirements.txt`, and
no hosting manifest, Streamlit config, deployment workflow, or recorded public
URL. The runtime architecture is a **combined Streamlit application**: UI and
backend run in the same Python process and communicate by function calls.
This describes the code, not proof of any existing external deployment.

GitHub metadata/deployment API checks via `gh api` returned `Forbidden` in this
environment. No current frontend, backend or public demo URL was verified.
Nothing was deployed, repointed, restarted or changed on an existing host.
If a public demo already exists, keep its repository/branch/entry point unchanged
until the Team Lead verifies it and approves the release.

## Deployment architecture

Deploy **one application**, not two services. `app.py` and `chat_ui.py` render the
frontend; `agent.py`/`service.py` execute backend logic; SQLite stores demo data.
No external backend URL, CORS setup, HTTP API, FastAPI, React or Docker is needed.
Frontend and backend therefore share one verified demo URL when hosted.

Frontend workflow: Magomed PR → tests/review → Team Lead-approved main release →
existing Streamlit host deploys that release.
Backend workflow: Amin PR → tests/review → the same approved main release →
backend Python modules deploy with the frontend. Do not independently ship
incompatible UI/service versions. `feature/deploy` only prepares configuration;
it is not an auto-deployment trigger. GitHub CI never merges or deploys.

Use one instance with a writable SQLite file. Session-owned confirmation state and
local SQLite are unsuitable for uncoordinated replicated workers or separate
service instances. For the hackathon this combined setup preserves tested behavior.

## Reproducible setup on the selected existing host

Use Python 3.11 or 3.12 and the reviewed release commit. Local checks in this setup
use 3.12; GitHub CI prepares a 3.11/3.12 matrix.

```bash
git clone https://github.com/moustafazade-ops/actionpilot.git
cd actionpilot
git switch main
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python -m pytest -q
python -m actionpilot.seed
streamlit run app.py --server.address=0.0.0.0 --server.port=8501
```

For staging the deploy branch before any main merge, select `feature/deploy` in a
separate checkout; do not change the current public host's branch without approval.
The startup command runs both frontend and backend. The app also seeds an empty
database on first session; explicit seeding above verifies storage before launch.
Seeding is idempotent and never overwrites existing orders. No schema migration
is required for these deployment/documentation changes.

On an existing process-based host, configure its normal process supervisor to
restart this startup command on failure and use its existing TLS/reverse proxy.
If the host requires a different port, supply its required numeric port explicitly
instead of 8501. Streamlit must serve HTTP and WebSocket traffic through that proxy.

If the team already uses Streamlit Community Cloud, configure the existing app:
repository `moustafazade-ops/actionpilot`, reviewed stable branch `main`, entry
point `app.py`, compatible Python runtime, and App settings → Secrets. Initial
configuration/changes require the Team Lead's hosting account access and approval.
Do not create or replace a public app automatically. Hosting provider details and
credentials were not supplied here, so no hosting-specific deployment is claimed.

## Environment and secrets

| Configuration | Source | Behavior |
| --- | --- | --- |
| `OPENAI_API_KEY` | Host environment or Streamlit Secrets | Real OpenAI key; process environment wins. Missing key disables AI chat; manual UI/admin still work. Never commit or log it. |
| `OPENAI_MODEL` | Process environment | Defaults to `gpt-4o-mini`; choose a tool-capable model your account can access. |
| `ACTIONPILOT_DB_PATH` | Process environment | Defaults to `data/actionpilot.db`; use an existing host's writable persistent disk for continuity. |

`.env.example` is documentation only; `.env` files are not automatically loaded.
On Streamlit Community Cloud, top-level secrets are also exposed as environment
variables by the platform. For local Streamlit, `.streamlit/secrets.toml` is ignored
by Git; use it for the API key. Application key resolution reads this file directly.
Model/database settings are read from process environment by the code.

Ensure outbound HTTPS access to `api.openai.com`, a valid billed/API-enabled account
and access to the configured model. Do not supply a real key to pytest: AI responses
and HTTP transport are mocked. A successful mocked test is not a live API check.

## SQLite and demo lifecycle

Default data are synthetic: 5 customers, 10 orders and 12 slots. Initial slots cover
the next three Baku dates at seed time; an old persistent DB can have expired slots.
Before a new demo, inspect slot dates. If a fresh seed is needed, use a new staging
DB path and verify it, preserving the current demo DB until the Team Lead approves
switching. Do not reset live data as part of deployment setup.

Some Streamlit hosts have ephemeral disks. On those hosts demo changes may disappear
on restart/redeploy and the app re-seeds empty storage. State this to judges; use
an existing persistent volume only if continuity is required and already supported.
Single-instance SQLite serializes confirmed writes with `BEGIN IMMEDIATE`. Order
and audit commit together. Pending confirmations live only in server session and
can be lost safely on restart, requiring a new proposal.

## Verification before announcing a URL

1. Run `python -m pytest -q` against the exact release and record actual results.
2. Start the server and check `GET /_stcore/health`; expect HTTP 200 and `ok`.
3. From a browser, verify customer selection, owned order/payment details and admin.
4. Verify AI chat using the configured real key: scoped lookup, proposal,
   unconfirmed state, cancellation without mutation, then explicit confirmation
   with committed order and audit. A typed "yes" must not execute a change.
5. Check the **actual public URL** from outside the host, including WebSocket/chat
   interaction. A health response alone does not prove end-to-end functionality.
6. Record the URL, release SHA, Baku timestamp, test evidence and any limitations.

Example local health probe while the server is running:

```bash
curl --fail http://127.0.0.1:8501/_stcore/health
```

This endpoint is supplied by Streamlit; no new API server is needed. Provider TLS,
public networking and custom domains are configured through the existing host.
The customer selector and public admin view are demo-only: use synthetic records.

## Remaining manual approvals and repository settings

- Team Lead reviews the deployment PR; no automated merge or production deployment.
- Review Amin's existing PR #3 and any selectively restored frontend backup work.
- Enable GitHub Actions if disabled. New workflow jobs run only after a permitted
  push/PR; inspect actual run results, not the YAML as proof of success.
- After checks appear, configure main protection to require human review and both
  `pytest (Python 3.11)` and `pytest (Python 3.12)` jobs from `Python tests`.
- Supply the current hosting platform/app URL, account access, approved release,
  secure OpenAI key/model and writable storage path.
- Confirm public health and functionality; keep the prior release available through
  normal hosting rollback. Never reset a DB or roll source backwards without review.
