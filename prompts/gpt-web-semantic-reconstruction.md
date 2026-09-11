# GPT-web semantic reconstruction campaign prompt

This prompt starts a persistent semantic campaign in a game repository
registered by the shared Touhou Reconstruction Factory MCP. The campaign is a
sequence of small, independently reviewable batches under
`gpt-web-semantic-reconstruction-session-v3`, which extends
`gpt-web-reconstruction-session-v4`. The mandatory companion contract is
`worktree-recovery-and-analysis-artifacts-v1`; no prompt assumes that ChatGPT
successfully loaded a bundled skill.

## Ready-to-run TH095 campaign with the plugin installed

Select **@Touhou Reconstruction Factory**, then send:

```text
Continue TH095 semantic reconstruction as an autonomous campaign through the
shared Factory workflow. Use $factory-semantic-reconstruction if it is actually
available, but do not depend on the skill body being loaded.

Before editing, try to read these Factory-controlled paths through
factory_repository_run_shell:
- /home/pentester/coding/codex_ida/touhou-reconstruction-factory/contracts/gpt-web-reconstruction-session-v4.json
- /home/pentester/coding/codex_ida/touhou-reconstruction-factory/contracts/gpt-web-semantic-reconstruction-session-v3.json
- /home/pentester/coding/codex_ida/touhou-reconstruction-factory/contracts/worktree-recovery-and-analysis-artifacts-v1.json
- /home/pentester/coding/codex_ida/touhou-reconstruction-factory/docs/semantic-reconstruction.md
- /home/pentester/coding/codex_ida/touhou-reconstruction-factory/docs/worktree-recovery-and-analysis-artifacts.md
If those read-only paths are not mounted, report that once and continue under
this complete inline prompt. Never invent missing rules or stop merely because
automatic skill loading failed.

GAME_ID: th095
SEMANTIC_OBJECTIVE: Continue from the live committed semantic history. Repeatedly
select the highest-evidence bounded owner, field, representation, or protocol
family; recover maintainable meaning; validate it under the target-exact and
reconstructed Windows i386 feedback lanes; record the evidence; and create a
local checkpoint before proceeding to the next family.
DEFAULT_PHASE_STATE: active-incomplete. GPT-web has no authority to declare the
semantic phase ready, complete, closed, or ready for porting.
SCOPE_HINT: Read the latest committed semantic record and its named next batch,
then verify that choice against live TH095 evidence. Prefer bounded families
with multiple TH095-local consumers and focused exact units. Do not redo an
already committed batch unless current evidence contradicts it.
RESUME_AUDIT: Treat every prior semantic-readiness, completion, closure, or exit-
audit statement as an untrusted hypothesis. Before following its proposed next
state, actively try to falsify it with current TH095-local evidence. Search for
a missed consumer/producer, owner/lifetime relation, protocol domain, persistent
or ABI boundary, runtime gap, or portability hazard outside the prior audit's
enumerated scope. One counterexample reopens the claim and becomes work. If one
bounded route finds none, immediately rotate to another coverage surface and
continue working in the same conversation; absence of a found counterexample
never changes active-incomplete and is not a handoff boundary.
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

This campaign is deliberately open-ended. Do not create a semantic-readiness or
completion checkpoint. A local evidence plateau is a routing event, never a
reason to stop: rotate among structural raw/unknown storage, canonical owners
and lifetimes, weak APIs and identifiers, primary and sibling interpreter
protocols, flags/state/resource/sound/replay domains, persistent formats and ABI
boundaries, portability hazards, and historical-platform runtime gaps. Keep
working until I explicitly interrupt or redirect the campaign, or an unavoidable
connection/tool/context boundary requires a durable continuation handoff. Such a
handoff pauses execution and does not close the phase.

Capture broad baselines once per campaign, not again before every edit. Use
focused syntax, compile, exact-unit, format, and runtime feedback inside each
batch. Run cold aggregate exact and whole-product gates immediately for shared
header/layout/PCH/owner or other cross-object risk, and at campaign milestones
and final handoff. Do not replay the entire accepted Factory receipt set after
every private checkpoint when the next source commit would immediately stale
it; issue current-source receipts at meaningful committed milestones and report
deferred or stale receipt planes accurately.

Use factory_report_semantic_debt only as a heuristic router and supplement it
with repository search, history, ledgers, and target evidence. Any non-clean
worktree is a mandatory recovery gate even when no disconnect is known. Before a
new batch, review complete staged/unstaged diffs, relevant untracked files,
handoff/history, tests, and manifests; classify every path as recoverable,
unrelated, generated-ephemeral, or unknown. Finish/checkpoint recoverable work
first, preserve/exclude unrelated work, and never delete/reset/overwrite/stage
unknown work. Do not push.

Treat `.analysis/` as non-authoritative bounded workspace. Inventory its size at
campaign start. Use command-local temporary storage for one-shot output or one
manifested `.analysis/gpt-web/<campaign-id>/` root for multi-command work. Reuse
bounded queries/provider state instead of accumulating whole-program exports,
Wine-prefix copies, analysis-database copies, or probe worktrees. At each
checkpoint retain compact tracked conclusions and remove only proven current-
session ephemeral paths with no active producer or reference. Never bulk-delete
`.analysis/` or touch legacy-unknown/shared provider state. Report starting and
ending bytes plus every retained large artifact.

Keep semantic interpretation, Git checkpoints, exact receipts, production
closure, runtime storage, and runtime scenarios as separate states. Unknown is
an accurate result. Do not begin portable Windows, Linux, or Web work inside
this campaign; a later independent Codex or human review decides whether the
semantic prerequisite is satisfied.
```

This is intentionally a campaign prompt, not a one-batch prompt. A successful
checkpoint closes the current inner transaction and starts the next selection
cycle. The current repository and its committed evidence decide what comes
next; the prompt does not freeze a stale address or candidate count.

## Standalone campaign without automatic skill selection

```text
Run an autonomous evidence-first semantic reconstruction campaign under
gpt-web-semantic-reconstruction-session-v3, extending the general
gpt-web-reconstruction-session-v4 live-repository contract, with mandatory
worktree-recovery-and-analysis-artifacts-v1. Do not assume a bundled skill was
loaded. Before editing, try to read these Factory-controlled paths through
factory_repository_run_shell:
- /home/pentester/coding/codex_ida/touhou-reconstruction-factory/contracts/gpt-web-reconstruction-session-v4.json
- /home/pentester/coding/codex_ida/touhou-reconstruction-factory/contracts/gpt-web-semantic-reconstruction-session-v3.json
- /home/pentester/coding/codex_ida/touhou-reconstruction-factory/contracts/worktree-recovery-and-analysis-artifacts-v1.json
- /home/pentester/coding/codex_ida/touhou-reconstruction-factory/docs/semantic-reconstruction.md
- /home/pentester/coding/codex_ida/touhou-reconstruction-factory/docs/worktree-recovery-and-analysis-artifacts.md
If unavailable, report that once and continue under this complete inline prompt.

Inputs
- GAME_ID: th095
- SEMANTIC_OBJECTIVE: Continue semantic reconstruction from the live committed
  history through successive evidence-backed owner/field/representation/protocol
  batches while preserving applicable target-exact and Windows i386 feedback.
- DEFAULT_PHASE_STATE: active-incomplete. GPT-web cannot close the semantic
  phase or authorize porting.
- SCOPE_HINT: Inspect the latest committed batch and named next batch, then
  revalidate the choice from current source, history, ledgers, and target-local
  evidence. Prefer bounded high-evidence families; do not redo completed work
  without a contradiction.
- RESUME_AUDIT: Treat every prior readiness/completion/exit-audit statement as
  an untrusted hypothesis. First try to falsify it with current TH095-local
  evidence and coverage outside its enumerated scope. One counterexample
  invalidates inherited closure and becomes work. If one bounded route finds no
  counterexample, immediately rotate coverage and continue working in the same
  conversation; the phase remains active-incomplete and the negative result is
  not a handoff boundary.
- RESUME_COMMIT: current
- EVIDENCE_SEED: TH08 is workflow/corroboration only; TH095 is authoritative.

Communicate with the user in Chinese. Write source, documentation, identifiers,
and Git commit messages in English.

Campaign start
1. Call factory_describe, factory_list_repositories, and
   factory_get_repository_status for th095. Record the actual branch, HEAD,
   upstream relation, and dirty/staged/untracked state. Preserve existing work.
2. If the tree is non-clean, complete a recovery review before selecting or
   editing a new batch. Inspect porcelain-v2 status, complete staged and
   unstaged diffs, every relevant untracked path, the latest handoff/history,
   tests, and artifact manifests. Classify paths as recoverable current work,
   unrelated pre-existing work, generated ephemeral output, or unknown. Adopt
   and finish/checkpoint recoverable work first; preserve/exclude unrelated
   work; never delete, reset, overwrite, or stage unknown work. Re-run this gate
   after interrupted commands or unexpected status changes.
3. Through factory_repository_run_shell, read AGENTS.md, the current handoff,
   architecture/workflow documents, semantic record, relevant source and
   ledgers, build/oracle scripts, and recent semantic commits. Run the live
   target, tracking, and target-attested Ghidra preflight required by the repo.
4. Inventory `.analysis/` total/top-level size without trusting old contents.
   Use temporary one-shot output or one manifested
   `.analysis/gpt-web/<campaign-id>/` scratch root. Treat 256 MiB as a soft
   campaign review budget and 64 MiB as the large-artifact threshold. Reuse
   bounded provider queries and never copy Wine prefixes or analysis databases
   per probe. Only delete proven current-session ephemeral paths with no active
   producer/reference; leave shared and legacy-unknown content untouched.
5. Capture the live function/extent exactness, production closure, runtime
   storage, and runtime scenario planes separately. Historical totals orient
   work only. Do this broad orientation once and refresh only what a later
   source/tool/target change can invalidate.
6. Adversarially review the latest readiness, completion, or exit-audit claim
   before trusting its handoff. Try to find a current target-local counterexample
   in a subsystem or debt class the prior audit did not enumerate. Prior prose
   is orientation, not phase state.

Repeated bounded batch
1. Select the latest named next batch when current evidence still supports it;
   otherwise choose one coherent high-evidence family and state exclusions.
   `factory_report_semantic_debt` is an optional lexical router, never a progress
   metric. Supplement it with broad Bash and target-local analysis. Keep each
   search bounded: prefer git grep/history for tracked content and exclude .git,
   .analysis, build, and .tools from live rg searches unless a named ignored
   path is the explicit subject. Never follow repository-root symlinks; Wine's
   dosdevices/z: may otherwise traverse the host filesystem.
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
   complete working/staged diff, measure `.analysis/` growth, remove only proven
   current-session ephemeral scratch, stage only intended files, and create one
   local English `gpt-web:` commit. Do not push.
7. Refresh the live HEAD and worktree, read the just-committed next-batch note,
   and immediately begin the next coherent batch. Do not ask whether to continue
   merely because the previous batch passed.
8. When one route yields no actionable change, rotate across structural layout,
   canonical ownership/lifetime, weak APIs/identifiers, interpreter and sibling
   protocols, flags/state/resource/sound/replay domains, persistent formats/ABI,
   portability hazards, historical-platform runtime gaps, and adjacent-game
   readability challenges. Keep searching and working in the same conversation;
   do not turn a plateau or self-audit into a readiness commit or handoff.

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

Continue open-endedly within semantic reconstruction. Stop executing only when
the user explicitly interrupts or redirects the campaign, a concrete tool or
connection boundary prevents further work in this conversation, remaining
context cannot safely close another batch, or the next action would leave the
semantic phase and enter porting. At such a boundary, finish or revert the active
experiment, preserve required checks and evidence in the repository, create a
checkpoint when coherent, name the next coverage route, and hand off without
leaving context-only work. The handoff status remains active-incomplete.

Continuation handoff: report the execution boundary; campaign objective; start/end
commit and dirty state; every completed checkpoint; selected and excluded
scope; target attestation; evidence classes and retained unknowns; checks by
feedback level; broad gates run or explicitly deferred; all verification planes;
accepted facts separately from semantic interpretation; and the exact next
batch. Include recovery classifications/actions, starting/ending `.analysis/`
bytes, manifest state, and retained/removed artifact disposition. Explicitly
state that GPT-web did not close the semantic phase. Never infer completion from
router counts, no new commit, a self-audit, an evidence plateau, or any number of
commits.
```
