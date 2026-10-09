# Backend scope fix and code review — 2026-10-09

## Fixed: misleading ownership and generic access replies

With Demo Customer 1 selected, a request for Demo Customer 2 could cause the model
to call `list_orders`. The service correctly returned only customer 1's records,
but the rendered reply did not identify that restriction. A follow-up question
about access produced a generic fallback because raw model prose is deliberately
discarded to prevent fabricated facts and false action confirmations.

The application now handles explicit foreign-customer references and access
questions before model execution or order reads. Scope-only replies use the bound
customer ID, invalidate prior confirmation tokens, and retain bounded conversation
history. The argument-free `get_access_scope` tool supports other phrasing; normal
replies and no-tool fallbacks also state the current scope. User text and tool
arguments cannot establish or override identity. No raw model prose is displayed.

Regression coverage includes both reported prompts in sequence and in Streamlit,
customer switching, foreign/combined/spelled/ordinal/Unicode references, identity
override rejection, owned reads, pending-token invalidation, history retention,
invented order facts and fake action confirmations. Tests use real isolated SQLite
databases and mocked model responses; no live OpenAI behavior is claimed.

## Remaining finding: manual confirmation does not guard the reviewed window (P2)

`actionpilot/views.py:46` calls `reschedule_order(customer_id, order_id, slot_id,
confirmed)` without `expected_order` or `expected_slot`. If the slot changes after
it is displayed and before the transaction reads it, the service can commit a
different delivery window from the one reviewed by the user. Chat confirmation
already passes both snapshots and rejects that change.

Reproduced against an isolated synthetic database using the exact manual-call
signature: read slot 1 at 09:00, change its start to 08:00 before calling the
service, then confirm. The call succeeds with the 08:00 assignment. Ownership,
availability and capacity checks still apply; the missing guarantee is consent to
the displayed window. A frontend follow-up should retain the reviewed snapshots
in session state and pass them into the existing transaction guards. This fix does
not change the manual frontend flow.

## Demo boundary

The customer selector simulates a session, and Admin intentionally displays all
synthetic records. This is not production authentication or admin authorization.
The chat restriction applies to the currently selected assistant session. No claim
of application-wide production isolation is made.
