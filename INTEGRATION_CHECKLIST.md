# ActionPilot integration and final submission checklist

Deadline: October 9, 2026, **20:00 Asia/Baku**. An unchecked item is pending, not
proof of completion. Team Lead controls merge and deployment decisions.

## Reviewed PR integration

- [ ] Inspect latest main and all intended PRs; preserve each developer's commits.
- [ ] Review Amin's backend PR #3 if still pending; do not assume its 153-test suite
  is on main. Obtain frontend/backend agreement for shared test/API changes.
- [ ] Review any frontend improvements restored from
  `backup/frontend-20261009-d229806`; do not restore them blindly.
- [ ] Review `feature/deploy` configuration/docs and its CI workflow.
- [ ] Review the feature/submission PR containing only these five Markdown files.
- [ ] Resolve conflicts deliberately, retaining both owners' intended behavior.
  Do not force-push/reset developer work or automatically merge PRs.
- [ ] Team Lead merges approved PRs to main, then records the final release SHA.
- [ ] Run `python -m pytest -q` on that exact integrated release; record actual
  counts, failures and environment. Review actual CI logs where available.
- [ ] Verify manual UI, AI chat, scoped tool calls, cancellation, explicit UI
  confirmation, execution-time checks and audit logging remain intact.

## Streamlit deployment and storage

- [ ] Identify the existing public app/hosting account and verify its URL before
  changing configuration. Preserve the working demo until release approval.
- [ ] Keep UI/backend together: repository `moustafazade-ops/actionpilot`, reviewed
  branch `main`, entry point `app.py`, supported Python runtime and dependencies.
- [ ] Team Lead approves deployment; no production deployment is triggered by
  this submission branch or documentation preparation.
- [ ] Ensure writable SQLite storage and idempotent synthetic initialization.
  Inspect slot dates; initial seed slots use the next three Baku dates.
- [ ] Document that SQLite on Streamlit Cloud's local disk is ephemeral and may
  reset on restart/redeploy. Do not promise durable data or multi-instance support.
- [ ] Check actual public `/_stcore/health`, browser rendering and WebSocket chat;
  a localhost or health-only check does not prove public end-to-end deployment.
- [ ] Replace **[PUBLIC_STREAMLIT_DEMO_URL]** with the verified public URL in all
  documents/captions and record release SHA + Baku verification timestamp.

## API secrets and mandatory disclosure

- [ ] Supply `OPENAI_API_KEY` through secure host environment/Streamlit Secrets;
  never Git, a PR, recording, screenshot or a test fixture with a real key.
- [ ] Record actual `OPENAI_MODEL`; default is `gpt-4o-mini`, configurable through
  process environment. Ensure billing, account/model access and outbound API access.
- [ ] Disclose official OpenAI SDK/tool calling and all exposed tools:
  `list_orders`, `get_order`, `get_payment_status`, `get_available_slots`,
  `propose_reschedule`, `cancel_reschedule`.
- [ ] Explain that model tools cannot accept customer identity, SQL or confirmation
  authority; application-owned `reschedule_order` commits only after UI approval.
- [ ] Disclose Python, Streamlit, SQLite and pytest; one combined process.
- [ ] Disclose generated synthetic data: 5 selectable demo customer contexts,
  10 orders, 12 slots. No production accounts, real customer/payment data, external
  retrieval corpus or fine-tuned model are represented.
- [ ] Disclose that user chat/scoped tool data are sent to OpenAI; avoid real PII.
- [ ] Disclose Codex-assisted development/documentation without asserting an
  unknown coding-model version.
- [ ] Explain missing production authentication/admin protection, ephemeral
  storage, session-local tokens, no intraday cutoff and no real payment processor.

## Live AI checks and evidence

- [ ] Reproduce payment/order lookup and delivery information without fabrication.
- [ ] Reproduce available-slot discovery and a proposal with no premature mutation.
- [ ] Reproduce cancellation and attempted rescheduling without confirmation.
- [ ] Reproduce explicit confirmation with actual committed order/audit evidence.
- [ ] Reproduce foreign-customer and prompt-injection requests using synthetic data.
- [ ] Reproduce missing/ambiguous requests and a multi-step support conversation.
- [ ] Add exact transcript, screenshot and relevant DB/audit evidence for each
  LIVE-01–LIVE-12 record, with reporter, URL, release SHA, model and Baku timestamp.
- [ ] Preserve the label **team-reported live testing: 12/12 passed** until independent
  reproduction exists. Do not represent the supplied report as verified security,
  public deployment proof, production authentication or measured accuracy.
- [ ] Keep historical Codex automated results separate from new live runs and
  branch-specific suites. Do not add overlapping counts or invent performance metrics.

## Final submission

- [ ] Finalize SUBMISSION.md and TEST_RESULTS.md with verified URL/release/model
  and clear reported-versus-reproduced evidence labels.
- [ ] Review all six slides in PITCH_OUTLINE.md for supported claims and disclosures.
- [ ] Record DEMO_SCRIPT.md in under two minutes; show observed results and actual
  confirmation controls; label any local recording or edited waiting time.
- [ ] Check no secrets appear in committed files, video, screenshots or PR text.
- [ ] Ensure repository access and submitted demo/video links work for judges.
- [ ] Record unresolved limitations plainly; do not call the prototype production-ready.
- [ ] Team Lead submits approved repository/demo/video before 20:00 Baku time.
