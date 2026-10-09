# ActionPilot pitch — six slides

Use the verified release and [PUBLIC_STREAMLIT_DEMO_URL] only after the Team Lead
supplies and checks it. This outline makes no adoption or performance claims.

## Slide 1 — Problem

**Headline:** Support requests need reliable facts and controlled actions.

- A delivery question can require order, payment and available-slot information.
- A generated answer alone cannot establish that a delivery change is valid.
- ActionPilot explores how conversational support can prepare reviewable actions
  while application logic remains responsible for authorization and execution.

Visual: one request → order/payment lookup → delivery decision. Present this as a
problem hypothesis, not customer research or quantified market evidence.

## Slide 2 — Solution

**Headline:** Retrieve facts, propose a change, ask for confirmation.

- Streamlit customer support UI plus an AI chat assistant.
- Order/payment lookup and delivery-slot discovery against SQLite.
- Reviewable proposals; explicit UI confirmation; transactional order + audit update.
- Manual support and a read-only demo admin view remain available.

Show synthetic Demo Customer 1 and order #1. State that the selector simulates
customer context; it is not production authentication.

## Slide 3 — AI workflow

**Headline:** The model plans tools; the application controls writes.

1. User asks in natural language.
2. OpenAI Chat Completions selects strict function calls.
3. Application binds calls to the selected demo customer and validates arguments.
4. Read/proposal tools return scoped facts; no model SQL or direct mutation.
5. The user confirms a proposal through the UI.
6. SQLite rechecks ownership/status/window/capacity, commits order and audit, then
   the application reports success.

Disclosure footer: default `gpt-4o-mini` (`OPENAI_MODEL` configurable), official
OpenAI SDK; tools `list_orders`, `get_order`, `get_payment_status`,
`get_available_slots`, `propose_reschedule`, `cancel_reschedule`. Actual hosted
model remains to be recorded. `reschedule_order` is application-owned execution.

## Slide 4 — Product demo

**Headline:** One conversation, one reviewable delivery change.

- Ask whether order #1 is paid and inspect the grounded answer.
- Inspect available slots using a real date shown in the running demo.
- Request a delivery change; show that the order is unchanged before confirmation.
- Cancel a proposal, then prepare a new one and explicitly confirm.
- Show the resulting order and audit entry only if the database confirms them.

Use DEMO_SCRIPT.md for a video under two minutes. If only localhost is available,
label it local; never substitute an invented public URL or fake a success screen.

## Slide 5 — Testing and security

**Headline:** Reported live checks and automated evidence have different scope.

- **Team-reported live testing: 12/12 passed.** Cases cover lookup/payment,
  delivery facts, proposals/confirmation, unauthorized requests, prompt injection,
  missing/ambiguous requests and a combined conversation.
- Transcripts, screenshots and audit evidence were not supplied; these live results
  are **not independently verified**.
- Previous Codex-reported automated runs: main suite 93 tests passed; preserved
  backend branch 153 passed. Counts refer to different snapshots and are not added.
- Automated AI tests use mocks; the backend branch's additional tests are not
  automatically evidence for the deployed main release.
- Safeguards: scoped queries, strict arguments, one-use confirmation, transactional
  revalidation and audit. No production authentication; demo admin is public.

Link TEST_RESULTS.md. Do not call the prototype fully secure or production-ready.

## Slide 6 — Feasibility and roadmap

**Headline:** A small working prototype with explicit next steps.

- Current stack: Python, Streamlit, SQLite, OpenAI SDK and pytest.
- Synthetic data: 5 customer contexts, 10 orders, 12 delivery slots; no real
  customer data, fine-tuning or retrieval corpus.
- Current release: one combined Streamlit process; no separate backend service.
- Next: reviewed PR integration, verified public demo, live evidence collection.
- Later: production authentication/admin roles, durable managed storage, operational
  monitoring, intraday delivery cutoffs and evaluation using permissioned data.

State that Streamlit Cloud's local SQLite is ephemeral and can reset on restart;
these roadmap items are proposed work, not delivered features. Disclose Codex
assistance in development/documentation; no unsupported savings or adoption figures.
