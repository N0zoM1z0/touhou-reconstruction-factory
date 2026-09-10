---
name: factory-replay
description: Operate verified Touhou reconstruction replays through the factory MCP. Use when the user asks to inspect registered reconstruction repositories, verify or replay a claim, resume or diagnose a durable factory job, or query accepted reconstruction facts. Do not use for editing game source or generic shell work.
---

# Factory Replay

Treat the factory as an evidence service, not as a claim generator. Imported
claims are candidates. A completed job is only execution state. Only a current
acceptance decision can promote a passing receipt into the Truth Kernel.
Live-repository commands, builds, and Git commits are development candidates,
never receipts; use `factory-reconstruction` for source work. Disposable
workspace results have the same evidence limitation.

## Operate

1. Call `factory_describe`, then `factory_list_repositories`. Use only a returned
   repository ID.
2. Call `factory_list_claims` for the selected repository. Never invent a claim
   ID or infer exactness from repository progress.
3. Before submission, state the repository, exact claim ID, and narrow proof
   scope. If no supported claim exists, report `unknown` and stop.
4. Call `factory_submit_replay` once with a stable, unique idempotency key. Reuse
   that key only when retrying the identical repository and claim. Retain and
   show the returned job ID.
5. Poll `factory_get_job` at a bounded cadence while the state is `queued`,
   `leased`, `running`, or `cancel-requested`. A later conversation can resume
   from the job ID; do not resubmit merely because the chat disconnected.
6. For a terminal job, distinguish all three layers:
   - execution state;
   - `receipt_verdict`;
   - `acceptance_decision`.
7. For failure or rejection, read `factory_get_job_events` and page the relevant
   artifact with `factory_get_job_output_page` until `next_offset` is null.
   Preserve `unknown`, stale, rejected, and unsupported outcomes exactly.
8. For a successful result, confirm it again through
   `factory_get_acceptance_registry`, `factory_query_accepted_facts`, or
   `factory_get_accepted_snapshot`. Report the job ID, receipt ID, registry ID,
   verdict, acceptance decision, covered extent, and oracle.

Do not call `factory_cancel_job` unless the user explicitly asks to cancel.
Never claim whole-image, ownership, linkage, or cross-build equivalence from a
standalone function result unless the returned claim and receipt prove it.

## TH105 smoke test

For the initial live check, select repository `th105`, list its claims with
`claim_type="codegen_exact"`, `limit=5`, and `offset=0`, and confirm that the
current adapter still exposes
`claim:th105-main:function:00401000:codegen-exact`. Submit that returned claim;
do not silently fall back to the remembered ID if discovery differs. The known
driver proves standalone VC8 function code generation only. It does not prove
LTCG physical ownership, linked-owner layout, or whole-image closure.

Finish with a compact result containing:

- repository and claim;
- job and terminal state;
- receipt verdict and acceptance decision;
- current registry/fact confirmation;
- explicit limitations or `unknown` fields.
