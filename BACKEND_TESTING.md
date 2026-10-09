# Backend verification

## Reproduce

From the repository root, with Python 3.11+:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q actionpilot app.py tests
.venv/bin/python -m pip check
git diff --check
```

The full suite includes Streamlit AppTest, service transactions/concurrency, and
AI tool calling. Each test uses a temporary SQLite database. OpenAI completions
and HTTP transport are mocked; no valid API key or live request is needed.
Current exact results and tested runtime are in `TEST_RESULTS.txt`.

## Security and action checks

| Requirement | Enforcement and regression coverage |
| --- | --- |
| Customer-scoped access | Parameterized queries match both order and customer; list/payment/read/write tests reject foreign records. Service and agent reject coerced, overflowing and invalid IDs. Tools cannot supply customer identity. |
| Scope explanations | Both reported live prompts run in sequence in agent and Streamlit tests. Explicit foreign-customer requests and access questions return application-owned scope replies before model execution or order reads. Normal replies identify the selected customer. The argument-free scope tool rejects identity overrides; customer switching clears old history. |
| Explicit confirmation | Service accepts literal boolean `True` only. Chat uses an application-owned one-use token; typed confirmation, wrong/stale/replayed tokens and model mutation tools cannot execute. Streamlit tests exercise manual and chat confirmation. |
| Cancellation | Both cancellation paths discard proposals. Full database snapshots prove orders, slots and audit records remain unchanged; cancelled tokens cannot execute. |
| Availability at commit | `BEGIN IMMEDIATE` serializes writers before ownership, status, enabled/date/capacity checks. Tests cover concurrent last-place booking, filled/disabled slots and changed order/window after proposal. |
| Atomicity | Order update and audit insertion share one transaction. Forced audit failure proves rollback; failed confirmation consumes its token. |
| Errors/configuration | Invalid orders, IDs/dates, malformed/duplicate/oversized JSON, unknown tools, database read failures, missing/invalid keys, API authentication/rate-limit/connectivity/timeout/server failures, malformed responses and tool budgets are covered. API/database tool errors do not expose private details. |

## Limitations and handoff

- This is a synthetic demo, **not verified production customer isolation**.
  Anyone using the frontend can select another demo customer, and the public
  admin tab displays all orders and audit logs. Service isolation applies only
  to the customer ID supplied by a trusted caller. Deployment needs real
  authentication and admin authorization; coordinate that frontend work with
  Magomed. `app.py` and the frontend interface are unchanged by this branch.
- Python callers can invoke the service with `True`; the service is not an
  authentication boundary. The application must establish identity and consent.
- The manual form revalidates current availability/capacity but does not pass
  reviewed order/window snapshots. Chat confirmation does. A changed manual
  slot window between rendering and submission is a frontend follow-up for
  Magomed; no guarantee of manual reviewed-window freshness is claimed.
- Eligibility is checked by Baku calendar date. Same-day delivery times that
  have already passed and dispatch cutoffs are outside the existing rules.
- SQLite writer locking prevents oversubscription for service transactions on
  one database. Tests use threads and independent connections, not a distributed
  deployment or multiprocess load test. Direct external SQL can bypass business
  rules. Invalid stored dates are safely rejected, not repaired or migrated.
- Mocked API tests verify SDK serialization and error paths, not live model
  behavior, account access, network availability, or prompt reliability.
  The text classifier recognizes common English demo customer references; it is
  not a general language authorization system. Scoped service queries enforce
  ownership independently of request phrasing. See BACKEND_REVIEW.md for findings.
- Streamlit AppTest verifies interface flows; browser rendering and live AI
  behavior are not part of this automated suite. Missing/unwritable storage at
  initial app startup is not handled by a new recovery screen.

No new dependencies, production authentication, schema migrations or frontend
changes are introduced. Never commit API keys, `.env`, Streamlit secrets,
generated databases or virtual environments.
