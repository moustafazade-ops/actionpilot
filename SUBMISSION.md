# ActionPilot — AI support with reviewable actions

## Submission details

- Repository: https://github.com/moustafazade-ops/actionpilot
- Public demo: **[PUBLIC_STREAMLIT_DEMO_URL]**
- Submission branch: `feature/submission`; submit the reviewed release SHA after merge.
- Deadline: October 9, 2026, **20:00 Asia/Baku**.
- Team: Magomed (frontend), Amin (backend/AI), Team Lead (integration/deployment).
- Status: working prototype in the repository; public deployment is not verified
  by this submission preparation. Do not present the placeholder as a live URL.

## Project description

ActionPilot is a hackathon customer-support prototype that uses OpenAI tool calling
to translate natural-language requests into customer-scoped order lookup, payment
status checks and delivery-change proposals. A user reviews the proposed delivery
window and explicitly confirms before the application attempts a transactional
change. SQLite verifies ownership, order status and slot capacity at execution time;
the order and audit record commit together before success is displayed.

The Streamlit app includes a customer selector, manual order/payment views,
rescheduling controls, conversational AI support and a read-only demo admin view.
The model can read and propose actions, but cannot execute SQL or directly modify
the database. Cancellation discards a proposal without changing an order.

This demonstrates an approach to support automation with application-enforced
checks. It is not a production enterprise deployment, payment processor or claim
of customer adoption, measured time savings, latency, throughput or accuracy.

## Setup

Use Python 3.11+; previous local verification used Python 3.12.

```bash
git clone https://github.com/moustafazade-ops/actionpilot.git
cd actionpilot
# Select the reviewed submission/release branch before running.
git switch feature/submission
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python -m actionpilot.seed
python -m pytest -q
streamlit run app.py
```

For real AI chat, supply `OPENAI_API_KEY` through the host's secure environment
settings or the gitignored `.streamlit/secrets.toml`. Never paste credentials into
Git, screenshots, chat examples or this document. Manual support works without a
key; AI chat is disabled until one is provided.

| Setting | Default / purpose |
| --- | --- |
| `OPENAI_API_KEY` | Required for live AI; environment takes precedence over Streamlit Secrets. |
| `OPENAI_MODEL` | Process environment; default `gpt-4o-mini`. Use a tool-capable model available to your account. |
| `ACTIONPILOT_DB_PATH` | Process environment; default `data/actionpilot.db`, requiring writable storage. |

`.env.example` documents variables; `.env` files are not automatically loaded.
The seed is synthetic and idempotent. Slots cover the next three Baku dates at
initial seeding, so check current availability before recording a demo.

## Mandatory technology, AI and data disclosure

| Component | Disclosure |
| --- | --- |
| Language | Python 3.11+; pinned dependencies are in `requirements.txt`. |
| Frontend/runtime | Streamlit 1.65.0; UI and backend run together in one Python process. No separate HTTP backend is implemented. |
| Database | SQLite via Python's standard library; tables for customers, orders, delivery slots and audit logs. |
| AI provider/model | OpenAI API through official Python SDK 2.54.0, Chat Completions with strict function/tool calling. Default runtime model is `gpt-4o-mini`, configurable with `OPENAI_MODEL`. Actual hosted/live model has not been supplied or verified for this document. |
| Model-exposed tools | `list_orders`, `get_order`, `get_payment_status`, `get_available_slots`, `propose_reschedule`, `cancel_reschedule`. None accepts customer identity, SQL or execution confirmation from the model. |
| Action execution | The UI calls application-owned confirmation with a one-use proposal token; backend `reschedule_order` revalidates and commits. It is not a model-exposed write tool. |
| Testing | pytest 9.1.1, isolated SQLite databases, mocked OpenAI responses and mocked SDK HTTP transport, plus Streamlit AppTest. See TEST_RESULTS.md for evidence labels. |
| Data | Locally generated synthetic data: 5 customers, 10 orders and 12 delivery slots. No real customer dataset, external training dataset, fine-tuning, vector database or RAG corpus is used by this implementation. |
| Data sent to OpenAI | User chat and scoped order/slot tool observations. Demo records are synthetic; avoid entering real personal or payment data. |
| Development assistance | Codex-assisted implementation, test development and documentation were used. Codex is not a runtime dependency. No specific underlying coding-model version is asserted. |

Synthetic demo accounts are selection contexts, **not authenticated logins**:

| Selector ID | Name | Synthetic email |
| --- | --- | --- |
| 1 | Demo Customer 1 | customer1@example.test |
| 2 | Demo Customer 2 | customer2@example.test |
| 3 | Demo Customer 3 | customer3@example.test |
| 4 | Demo Customer 4 | customer4@example.test |
| 5 | Demo Customer 5 | customer5@example.test |

## Limitations and honest evidence

- No production authentication or role-based admin protection: the customer
  selector and admin page are demo controls. Service ownership checks enforce the
  application-supplied context, not a verified real-world identity.
- SQLite on Streamlit Community Cloud uses ephemeral local storage; changes can
  be lost on restart/redeploy. No durable cloud database is configured here.
- Pending confirmation tokens are session-local and can disappear on restart.
  The current design targets one combined instance, not distributed deployment.
- Payment status is read-only synthetic data; no real payment integration exists.
- Same-day slot eligibility has no intraday dispatch cutoff. Fresh seed dates
  matter, and the manual form does not apply all reviewed-snapshot guards used
  by chat confirmation. These are known prototype limitations.
- The application renders replies from validated tool observations; it does not
  display arbitrary model prose as evidence that an action completed.
- API access depends on a valid key, account/model access and network availability.
- Twelve successful live scenarios and their descriptions were supplied by the
  team. Transcripts, screenshots and database audit evidence were not supplied.
  This documentation records team-reported results, not independent certification
  of those scenarios or live deployment.
- Historical automated results are evidence for their recorded code snapshots,
  not proof that every current branch or public host passed the same tests.

Before final submission, replace the demo URL, complete the live-test record,
record the deployed release SHA/model, and follow INTEGRATION_CHECKLIST.md.
