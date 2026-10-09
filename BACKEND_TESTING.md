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

## Account authentication coverage

`tests/test_auth.py` uses real Argon2id hashes and isolated SQLite account files:
normalization/validation, password limits and mismatch, salted hashes, persistence,
case-insensitive duplicates, concurrent registration, uniform login errors, durable
attempt limits/expiry, TLS configuration and sanitized storage failures.
`tests/test_login.py` exercises the full Streamlit account flow, failures, repeated
navigation, new sessions, logout cleanup, Home reset for a different user and
rejection of legacy passwordless session flags. Hash upgrades and corrupt stored
hashes are covered as well. No SMTP or real user credentials
are used. `AUTH_DATABASE_URL` selects hosted PostgreSQL with no ephemeral fallback.

### PostgreSQL integration tests

Use a dedicated **disposable test database**, never your live account database:

```bash
AUTH_TEST_DATABASE_URL='postgresql://TEST_USER:TEST_PASSWORD@TEST_HOST/TEST_DB?sslmode=require' python -m pytest -q
```

`tests/test_auth_postgres.py` runs real persistence, duplicates, concurrent signup,
shared throttling and Streamlit sign-up/login checks. Without this environment
variable its four tests skip; all SQLite/service/UI/AI tests still run offline.
PostgreSQL verification for this branch used a temporary local PostgreSQL 16 server
behind a localhost TLS proxy because the test-only pgserver binary lacks native
TLS. Tests assert that the psycopg client uses TLS. No hosted provider credentials
were available, so production network/permissions/persistence need the documented
Cloud smoke test. The test runtime/proxy is not an app dependency or deployment.

## Limitations and handoff

- This is a synthetic demo, **not verified production customer isolation**.
  Any registered demo account can select another demo customer, and the demo
  admin tab displays all orders and audit logs. Service isolation applies only
  to the customer ID supplied by a trusted caller. Deployment needs real
  customer-account binding and admin authorization. Login authenticates accounts
  but preserves the synthetic selector and existing Admin view.
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

Account libraries and account tables are added; order/service/AI schemas and
confirmation rules are preserved. Never commit API keys, `.env`, Streamlit secrets,
generated databases or virtual environments.
