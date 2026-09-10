# GPT-web semantic reconstruction campaign prompt

This prompt starts a persistent semantic campaign in a game repository
registered by the shared Touhou Reconstruction Factory MCP. The campaign is a
sequence of small, independently reviewable batches under
`gpt-web-semantic-reconstruction-session-v2`, which extends
`gpt-web-reconstruction-session-v4`.

## Ready-to-run TH095 campaign with the plugin installed

Select **@Touhou Reconstruction Factory**, then send:

```text
Use $factory-semantic-reconstruction to continue TH095 semantic reconstruction
as an autonomous campaign through the shared Factory workflow.

GAME_ID: th095
SEMANTIC_OBJECTIVE: Continue from the live committed semantic history. Repeatedly
select the highest-evidence bounded owner, field, representation, or protocol
family; recover maintainable meaning; validate it under the target-exact and
reconstructed Windows i386 feedback lanes; record the evidence; and create a
local checkpoint before proceeding to the next family.
SCOPE_HINT: Read the latest committed semantic record and its named next batch,
then verify that choice against live TH095 evidence. Prefer bounded families
with multiple TH095-local consumers and focused exact units. Do not redo an
already committed batch unless current evidence contradicts it.
STOP_CONDITION: Continue across multiple coherent batches. Do not stop merely
because one batch or checkpoint succeeded. Stop only when an independent
game-local semantic exit audit supports the campaign objective, a concrete
evidence/tool boundary prevents useful progress, continuation requires a
materially different scope decision, or remaining context cannot safely close
another batch. Under context pressure, first close or revert the active
experiment, run required checks, create a coherent checkpoint when warranted,
write the next batch into durable repo state, and then hand off.
RESUME_COMMIT: current
EVIDENCE_SEED: TH08 is workflow and adjacent-engine corroboration only. Require
TH095-local evidence for every accepted interpretation.

Communicate with me in Chinese. Write source, documentation, identifiers, and
Git commit messages in English. Work directly in the registered live TH095
repository with autonomous Bash, target-attested Ghidra, Wine/VC7.1, and
repo-native checks. Begin using tools after a compact orientation; do not spend
the session narrating a plan that can be tested.

Treat each batch as a small transaction: investigate one coherent family,
change natural source, run the narrowest fast feedback first, close its actual
regression surface, document observed/corroborated/inferred/unknown meaning,
inspect the complete diff, and create an English `gpt-web:` commit. Immediately
refresh live state and choose the next batch without asking me for permission.

Capture broad baselines once per campaign, not again before every edit. Use
focused syntax, compile, exact-unit, format, and runtime feedback inside each
batch. Run cold aggregate exact and whole-product gates immediately for shared
header/layout/PCH/owner or other cross-object risk, and at campaign milestones
and final handoff. Do not replay the entire accepted Factory receipt set after
every private checkpoint when the next source commit would immediately stale
it; issue current-source receipts at meaningful committed milestones and report
deferred or stale receipt planes accurately.

Use factory_report_semantic_debt only as a heuristic router and supplement it
with repository search, history, ledgers, and target evidence. Preserve all
existing dirty or untracked files and never stage unrelated work. Do not push.
Keep semantic interpretation, Git checkpoints, exact receipts, production
closure, runtime storage, and runtime scenarios as separate states. Unknown is
an accurate result. Portable Windows, Linux, and Web work begins only after
semantic readiness and cannot substitute for the historical-platform
prerequisite.
```

This is intentionally a campaign prompt, not a one-batch prompt. A successful
checkpoint closes the current inner transaction and starts the next selection
cycle. The current repository and its committed evidence decide what comes
next; the prompt does not freeze a stale address or candidate count.

## Standalone campaign without automatic skill selection

```text
Run an autonomous evidence-first semantic reconstruction campaign under
gpt-web-semantic-reconstruction-session-v2, extending the general
gpt-web-reconstruction-session-v4 live-repository contract.

Inputs
- GAME_ID: th095
- SEMANTIC_OBJECTIVE: Continue semantic reconstruction from the live committed
  history through successive evidence-backed owner/field/representation/protocol
  batches while preserving applicable target-exact and Windows i386 feedback.
- SCOPE_HINT: Inspect the latest committed batch and named next batch, then
  revalidate the choice from current source, history, ledgers, and target-local
  evidence. Prefer bounded high-evidence families; do not redo completed work
  without a contradiction.
- STOP_CONDITION: One batch is not a terminal condition. Continue until an
  independent semantic exit audit supports completion, a concrete blocker
  prevents useful progress, a materially different scope decision is required,
  or remaining context cannot safely close another batch.
- RESUME_COMMIT: current
- EVIDENCE_SEED: TH08 is workflow/corroboration only; TH095 is authoritative.

Communicate with the user in Chinese. Write source, documentation, identifiers,
and Git commit messages in English.

Campaign start
1. Call factory_describe, factory_list_repositories, and
   factory_get_repository_status for th095. Record the actual branch, HEAD,
   upstream relation, and dirty/staged/untracked state. Preserve existing work.
2. Through factory_repository_run_shell, read AGENTS.md, the current handoff,
   architecture/workflow documents, semantic record, relevant source and
   ledgers, build/oracle scripts, and recent semantic commits. Run the live
   target, tracking, and target-attested Ghidra preflight required by the repo.
3. Capture the live function/extent exactness, production closure, runtime
   storage, and runtime scenario planes separately. Historical totals orient
   work only. Do this broad orientation once and refresh only what a later
   source/tool/target change can invalidate.

Repeated bounded batch
1. Select the latest named next batch when current evidence still supports it;
   otherwise choose one coherent high-evidence family and state exclusions.
   `factory_report_semantic_debt` is an optional lexical router, never a progress
   metric. Supplement it with broad Bash and target-local analysis.
2. For every proposed meaning, inspect relevant target-local offsets, widths,
   signedness, reads/writes, callers/callees, strings, relocations, state
   transitions, lifetime, and storage owner. Target-attested IDA/Ghidra output
   is provisional and has zero exactness credit.
3. Classify meaning as observed, corroborated, inferred, or unknown. Adjacent
   games, decompiler labels, attractive names, and layout assertions cannot
   independently prove meaning. Use neutral names and retain opaque unknowns.
4. Make the narrowest natural C/C++ change. Preserve the historical ABI,
   layout, width, signedness, packing, bitfields, construction order, and
   translation-unit visibility. Keep genuine wire formats, instruction streams,
   tagged storage, and platform ABI buffers byte-oriented.
5. Use the feedback ladder. During editing run syntax/layout checks, the
   smallest affected compile/object comparisons, and focused analysis. Before
   the batch checkpoint replay every affected exact unit and run the affected
   historical-platform compile/link, format, or runtime checks. Shared headers,
   layout, PCH, inline bodies, ownership, persistence, callbacks, rendering,
   input, or audio trigger their broader cold gates immediately.
6. Record concise durable evidence and retained unknowns, inspect status and the
   complete working/staged diff, stage only intended files, and create one local
   English `gpt-web:` commit. Do not push.
7. Refresh the live HEAD and worktree, read the just-committed next-batch note,
   and immediately begin the next coherent batch. Do not ask whether to continue
   merely because the previous batch passed.

Milestone and receipt cadence
- Repo-native checks provide the fast inner feedback loop while source is dirty.
- Do not replay every accepted receipt after every private checkpoint if another
  planned source commit would immediately stale it.
- At shared/cross-object risk, a meaningful campaign milestone, or final
  handoff, run the repository-required cold aggregate exact gate and cold
  historical-platform whole-product build. Submit Factory replay only against
  the current committed source, then distinguish job completion, receipt pass,
  registry acceptance, and accepted-fact query.
- A deferred, unavailable, or stale plane must be reported as such. Never replace
  it with another green check.

Continue until a terminal condition is actually reached. If context is nearing
its limit, finish or revert the active experiment, preserve required checks and
evidence in the repository, create a checkpoint when coherent, name the next
batch, and hand off without leaving context-only work.

Final handoff: report the terminal condition; campaign objective; start/end
commit and dirty state; every completed checkpoint; selected and excluded
scope; target attestation; evidence classes and retained unknowns; checks by
feedback level; broad gates run or explicitly deferred; all verification planes;
accepted facts separately from semantic interpretation; and the exact next
batch. Never infer semantic completion from router counts or number of commits.
```
