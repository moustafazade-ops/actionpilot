# Verified milestone file map

Inspected main: `4dd5a1cd2795cac23fc88e0fe40fed6d8518e2d4`.
Milestone origins verified with `git show --stat`: M1 `fcd8e5e` (PR #1), M2
`e51e03f` (PR #2), post-M2 fixes `c8a98cb` (merge `4dd5a1c`). Historical branches
still exist, but code distribution follows functionality, not milestone number.

| File path | Origin | Functionality | Responsible developer | Intended branch | Present? | Additional integration needed? |
| --- | --- | --- | --- | --- | --- | --- |
| `app.py` | M1, expanded M2 | Streamlit customer/order/admin views; calls chat renderer | Magomed | `feature/frontend` | Main + all three branches | No; old frontend improvements are backed up for review. |
| `actionpilot/chat_ui.py` | M2 | Chat controls, secrets adapter, session context, confirmation/cancellation screens | Magomed; Amin reviews binding/security | `feature/frontend` | Main + all three branches | No; preserve agent API. |
| `actionpilot/db.py` | M1 | Schema, foreign keys, connection/transaction context | Amin | `feature/backend` | Main + all three branches | No. |
| `actionpilot/seed.py` | M1 | Idempotent 5-customer/10-order/12-slot synthetic seed | Amin | `feature/backend` | Main + all three branches | No. |
| `actionpilot/service.py` | M1; snapshot guards M2 | Scoped orders/payments/slots, atomic confirmed reschedule and audit, admin queries | Amin | `feature/backend` | Main + all three branches | No milestone gap; Amin's added validation awaits PR review. |
| `actionpilot/agent.py` | M2; argument fixes after M2 | Official SDK, tools, read/proposal orchestration, one-use confirmation tokens | Amin | `feature/backend` | Main + all three branches | No milestone gap; Amin's further hardening is preserved. |
| `actionpilot/__init__.py` | M1 | Python package marker | Amin | `feature/backend` | Main + all three branches | No. |
| `tests/test_service.py` | M1 | Ownership, transitions, capacity, rollback/concurrency tests | Amin | `feature/backend` | Main + all three branches | No; additional backend tests remain on Amin's branch. |
| `tests/test_agent.py` | M2; post-M2 fixes | Mocked AI/SDK, authorization, invalid args, confirmation/cancellation/stale state | Amin | `feature/backend` | Main + all three branches | No; preserve additional backend tests. |
| `tests/test_app.py` | M1, expanded M2 | Manual/AI UI tests; customer binding and confirmed interaction flow | Magomed + Amin | Both feature branches, coordinate | Main + all three branches | Both branches previously edited this file; review chosen backup UI changes against Amin's tests before integration. |
| `requirements.txt` | M1; SDK added M2 | Pinned Streamlit, pytest and official OpenAI SDK | Team Lead with Amin | `feature/deploy` | Main + all three branches | No dependency changes needed for setup. |
| `pytest.ini` | M1 | Test discovery/import paths | Team Lead with Amin | `feature/deploy` | Main + all three branches | No. |
| `.env.example` | M1, expanded M2 | Safe DB/key/model configuration template | Team Lead | `feature/deploy` | Main + all three branches | No real secrets. |
| `.gitignore` | Initial repo; M1 database exclusions | Exclude keys, envs, generated databases | Team Lead | `feature/deploy` | Main + all three branches | No changes required. |
| `README.md` | Initial repo, M1/M2 and fixes | App setup, API and feature documentation | Shared; Team Lead release owner | `feature/deploy` | Main + all three branches | Coordinate backend branch's own README addition. |
| `TEST_RESULTS.txt` | M1, updated M2/fixes | Historical verification results | Shared; test authors | All role branches | Main + all three branches | Do not overwrite Amin's expanded report; new setup results are in a separate file. |
| `AGENTS.md` | Amin's `03e95e3` | Backend working instructions | Amin + Team Lead | `feature/backend` | Backend only | Review with PR #3; not copied or modified. |
| `BACKEND_TESTING.md` | Amin's `03e95e3` | Backend test handoff | Amin | `feature/backend` | Backend only | Review with PR #3; not copied or modified. |
| `.github/workflows/tests.yml` | This setup | Python 3.11/3.12 pytest CI; no deployment/merge job | Team Lead | `feature/deploy` | Deploy branch | Review PR before adoption by main. |
| `.github/pull_request_template.md` | This setup | Validation and ownership checklist | Team Lead | `feature/deploy` | Deploy branch | Review PR. |
| `.streamlit/config.toml` | This setup | Headless startup; usage telemetry disabled | Team Lead | `feature/deploy` | Deploy branch | Review PR; no hosting destination configured. |
| `TEAM_WORKFLOW.md` | This setup | Ownership, branch and interface contracts | Team Lead | `feature/deploy` | Deploy branch | Review PR. |
| `MILESTONE_FILE_MAP.md` | This setup | This provenance map | Team Lead | `feature/deploy` | Deploy branch | Review PR. |
| `DEPLOYMENT.md` | This setup | Combined deployment, secure config and health verification | Team Lead | `feature/deploy` | Deploy branch | Hosting access/secrets/approval still required. |
| `SETUP_VERIFICATION.md` | This setup | Actual setup tests, SHA checks and limitations | Team Lead | `feature/deploy` | Deploy branch | CI/public hosting results are reported only after verified runs. |

Main contains both milestones. No milestone source needs copying/cherry-picking.
The recreated frontend starts with the complete working main UI including AI chat;
backend retains the complete main application plus Amin's commits. No production
hosting or application-source changes are part of this setup.
