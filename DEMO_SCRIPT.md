# ActionPilot demo video — target 1 minute 55 seconds

This is a recording plan, not proof that any step passed. Show only actual observed
behavior. Rehearse before recording; if API latency pushes the runtime over two
minutes, shorten narration or disclose edited waiting time. Never fabricate outputs.

## Before recording

- Confirm the reviewed release, configured model and working API key privately.
- Use synthetic Demo Customer 1/order #1; inspect available dates/slots in advance.
- Keep API settings, secret files and credentials off-screen.
- Public URL is [PUBLIC_STREAMLIT_DEMO_URL] until supplied and verified. If recording
  localhost, label the video **local prototype demonstration**.
- Ensure the reviewed demo order is reschedulable. Do not reset the current public
  database without Team Lead approval; use a separate demo dataset if necessary.

| Time | Show | Suggested narration |
| --- | --- | --- |
| 0:00–0:12 | Title and actual running application | “ActionPilot is a customer-support prototype that retrieves order facts and prepares delivery changes for explicit approval. This demo uses synthetic data.” |
| 0:12–0:28 | Select Demo Customer 1. Ask “Is order 1 paid, and what is its status?” | “The model chooses support tools. The application supplies the customer context and retrieves facts from SQLite.” |
| 0:28–0:43 | Ask for slots on an available date shown in the app | “Available delivery windows come from the database, rather than an invented schedule.” |
| 0:43–0:59 | Request order #1's move to a displayed alternative slot. Show review controls | “A request creates a proposal. The model cannot execute SQL or directly change an order. Nothing is committed yet.” |
| 0:59–1:10 | Click Cancel proposal | “Cancellation discards the proposal without changing the order.” |
| 1:10–1:30 | Prepare a new proposal, review date/time, click Confirm delivery change | “Explicit UI confirmation invokes backend checks again, including ownership, status and capacity. We report success only after database commit.” |
| 1:30–1:43 | Show the actual updated order and admin audit row | “Here is the resulting order and audit record.” Say this only if they actually exist; otherwise explain the observed failure and retry safely. |
| 1:43–1:55 | Closing card: stack, evidence labels and limitations | “Built with Python, Streamlit, SQLite and OpenAI tool calling. The team reports 12 live scenarios passed; those records are not independently verified. This is a prototype: no production authentication, and Cloud SQLite is ephemeral.” |

## End card / caption disclosure

- Repository: https://github.com/moustafazade-ops/actionpilot
- Demo: [PUBLIC_STREAMLIT_DEMO_URL] — replace only after verification.
- Default model: `gpt-4o-mini`, configurable; caption the actual model used in the
  recording rather than assuming the default proves live configuration.
- Official OpenAI SDK; read/proposal/cancel tools, application-owned confirmation.
- Five synthetic demo customer contexts, ten orders, twelve slots; no real accounts
  or payment processing. The customer selector and admin view are demo controls.
- Codex-assisted development/documentation. TEST_RESULTS.md separates reported
  live checks from previous automated results.

Use the six-slide outline for a longer presentation, not extra video segments.
