# ActionPilot team workflow

Prepared on October 9, 2026. Deadline: **20:00 Asia/Baku**.

## Baseline and branch operations

Latest inspected main: `4dd5a1cd2795cac23fc88e0fe40fed6d8518e2d4`.
Both milestones, including AI chat and confirmed transactional rescheduling, are
already merged. Main is unchanged by this setup; no PR is merged automatically.

| Branch | Owner | Initial state / operation |
| --- | --- | --- |
| `feature/frontend` | Magomed | Old tip `d229806ba30c33303121b909751dd21678e24031` backed up to `backup/frontend-20261009-d229806`, then branch deleted and recreated at main `4dd5a1c`. GitHub PR search returned no frontend PR. |
| `feature/backend` | Amin | Original tip `03e95e3fd6dcb34623750f829f19cb6470b179b2` preserved exactly. Contains both milestones and extra validation/tests; PR #3 is for human review. |
| `feature/deploy` | Team Lead | Created from main `4dd5a1c`; adds this documentation, file map, deployment instructions, PR template, Streamlit config and test workflow. |

Each branch is a **complete application snapshot**, not a folder for a role.
Do not remove the other developer's code or copy milestones between branches.
The frontend backup and historical milestone branches are archival, not active
team branches. They remain available for recovery; backend is never reset or
force-pushed. `feature/integration` was only a temporary local branch and was
removed before any remote publication, following the revised request.

## File ownership

| Owner | Files | Coordination |
| --- | --- | --- |
| Magomed | `app.py`, `actionpilot/chat_ui.py`, UI styles/components, UI-specific cases in `tests/test_app.py` | Coordinate customer binding, key handling, proposal tokens and backend calls with Amin. |
| Amin | `actionpilot/db.py`, `seed.py`, `service.py`, `agent.py`, `__init__.py`, `tests/test_service.py`, `tests/test_agent.py` | Own business rules and AI orchestration; coordinate interface changes with Magomed. |
| Team Lead | `.github/**`, `.streamlit/config.toml`, `requirements.txt`, `.env.example`, `.gitignore`, `pytest.ini`, `TEAM_WORKFLOW.md`, `MILESTONE_FILE_MAP.md`, `DEPLOYMENT.md`, `SETUP_VERIFICATION.md` | Dependencies, config, CI, hosting and release reviews. |
| Shared | `README.md`, `TEST_RESULTS.txt`, `tests/test_app.py`, backend branch's `AGENTS.md` and `BACKEND_TESTING.md` | Agree changes in PRs; Amin owns security assertions, Magomed owns UI assertions. Preserve existing reports and instructions. |

GitHub usernames for Magomed and Amin were not supplied, so no invented CODEOWNERS
or automatic reviewer assignments are added. Configure reviewers manually.

## Stable frontend/backend interface

The app is one Streamlit Python process. `app.py` imports `service.py` and calls
`render_chat(customer_id)` from `chat_ui.py`. The chat adapter calls `SupportAgent`
from `agent.py`; it invokes `service.py`, which uses `db.py` and SQLite. There is
no HTTP backend or separate frontend API URL. The existing separation is adequate;
no framework migration or code refactor is needed.

| API | Inputs | Output / failure |
| --- | --- | --- |
| `list_customers()` | None | List of `{id, name, email}` synthetic customer dicts. |
| `list_orders(customer_id)` | Trusted application-selected ID | List of that customer's order dicts. |
| `get_order(customer_id, order_id)` | Trusted ID and order ID | Dict: `id`, `customer_id`, `item`, `amount_cents`, `payment_status`, `status`, `slot_id`; `ActionError` for missing/foreign order. |
| `get_payment_status(customer_id, order_id)` | Same ownership context | Stored string: `paid`, `pending`, `failed` or `refunded`. |
| `get_available_slots(date)` | ISO `YYYY-MM-DD` in Baku | Enabled/non-full slot dicts: `id`, `date`, `start_time`, `end_time`, `capacity`, `enabled`, `remaining_capacity`; past dates return `[]`. |
| `reschedule_order(customer_id, order_id, slot_id, confirmed, *, expected_order=None, expected_slot=None)` | Trusted IDs; literal `True`; optional reviewed snapshots | Committed order dict; ownership/status/date/window/capacity checks; atomic order+audit commit. `ActionError` for rejection, `sqlite3.Error` for DB failure. |
| `admin_snapshot()` | None | Dict with `orders`, `slots`, `audit_logs` lists. Read-only demo admin data. |
| `render_chat(customer_id)` | Trusted customer selector ID | Renders chat and binds server session to that customer; switches discard old context. |
| `create_client(api_key=None)` | Environment/secret key, never a model argument | Official OpenAI client; sanitized `AgentError` if missing. |
| `SupportAgent(customer_id, client, model=None)` | Trusted customer ID, client, optional model | Session-owned orchestrator. `ask(text)` returns grounded chat text; `.pending` is a Proposal or None. |
| `agent.confirm(token)` | Current proposal token from UI confirmation button | Revalidates and returns committed order, consumes token once; stale/cancelled/repeated tokens rejected. |
| `agent.cancel(token)` | Current proposal token | Clears proposal without an order mutation; returns None. |

Proposal fields are `token`, `order`, `slot`. Preserve these UI contracts. Customer
identity and confirmation authority never come from tool arguments. Model tools
are reads/proposals/cancellation only, never SQL or execution. Only pending and
scheduled orders may move. Active pending/scheduled/dispatched orders occupy
slots; delivered/cancelled do not. Use Baku dates and success only after commit.
The demo selector/admin page are not production authentication or authorization.
Amin's branch strengthens invalid-input handling without changing public function
signatures; review its PR separately rather than copying individual changes.

## Milestone history and integration

Milestone 1 (`fcd8e5e`, merged PR #1) added `db.py`, `seed.py`, service queries,
`reschedule_order`, ownership checks, capacity enforcement, confirmation and audit
logging, `app.py` and service/UI tests. Milestone 2 (`e51e03f`, merged PR #2) added
`agent.py`, `chat_ui.py`, strict tool validation, Proposal state, `ask`, `confirm`,
`cancel`, client construction, UI chat and mocked agent tests. `c8a98cb` added
SQLite-range/tool-argument safeguards, merged into main at `4dd5a1c`.
See MILESTONE_FILE_MAP.md for per-file evidence.

No application files were cherry-picked, merged or rewritten for this setup.
Recreated frontend contains both milestones from main. Its old UI improvements
are safe in the backup and **not automatically restored**: Magomed should inspect
that one commit, then apply chosen changes via a new reviewed commit/PR. Backend
already contains the milestones plus Amin's changes; no backend integration is
needed for milestone completeness. PR #3, backup UI improvements, and deployment
setup all require Team Lead review before reaching main.

## Start work simultaneously

Each developer uses an independent clone (never a shared working directory):

```bash
git clone https://github.com/moustafazade-ops/actionpilot.git
cd actionpilot
git fetch origin
```

Choose your branch:

```bash
# Magomed
git switch --track origin/feature/frontend
# Amin
git switch --track origin/feature/backend
# Team Lead
git switch --track origin/feature/deploy
```

Then each developer runs:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python -m pytest -q
streamlit run app.py
```

Existing clones: commit your own local changes first, then `git fetch origin`.
Magomed's old local frontend history must not be pushed back over the recreated
branch. Keep it under a new local archival branch and use a fresh clone for the
new frontend branch. Amin continues with `git pull --ff-only origin feature/backend`;
no reset is needed. Do not commit or print API keys.

For local UI+backend co-development, coordinate proposed API changes before
coding. Each role can run the full app from their own snapshot. Integration
happens through reviewed PRs, not live file sharing between branch checkouts.

## Commits, PRs and conflict resolution

1. Edit owned files; announce shared interface changes in the PR description.
2. Run the full tests, stage named files and inspect `git diff --cached`.
3. `git commit -m "Describe the resulting behavior"`.
4. `git push origin YOUR_BRANCH` (never force-push).
5. Open a PR to `main`; include actual test results and coordinated reviewers.
6. Team Lead checks CI and reviews safety/UX, then decides whether to merge.
   CI only tests; it never merges or deploys. Configure branch protection to
   require successful Python 3.11/3.12 tests and a human review once checks appear.

Do not mix frontend and backend changes merely to eliminate a conflict. Before
syncing, commit or stash your own changes and fetch. On your development branch,
merge `origin/main` only when the owners agree; resolve both sides deliberately,
run tests and push normally. `git merge --abort` returns to the pre-merge state
if resolution is uncertain. No `reset --hard`, force-push or blanket "ours/theirs"
resolution. Do not merge Amin's current branch into main during this setup.

## Deployment handoff

Read DEPLOYMENT.md. Keep UI and backend in the same Streamlit deployment, using
main as the stable release branch after reviewed merges. The Team Lead supplies
hosting access, secrets, a writable DB path, and approval to deploy. This setup
neither changes an existing host nor performs a production deployment. Verify
health, manual flows and AI confirmation before announcing a public demo URL.
