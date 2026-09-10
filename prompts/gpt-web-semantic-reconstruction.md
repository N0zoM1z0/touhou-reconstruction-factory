# GPT-web semantic reconstruction prompt

This prompt starts one bounded semantic batch in a game repository registered
by the shared Touhou Reconstruction Factory MCP. The session contract is
`gpt-web-semantic-reconstruction-session-v1`, extending
`gpt-web-reconstruction-session-v4`.

## Ready-to-run TH095 prompt with the plugin installed

Select **@Touhou Reconstruction Factory**, then send:

```text
Use $factory-semantic-reconstruction to begin TH095 semantic reconstruction
through the shared Factory workflow.

GAME_ID: th095
SEMANTIC_OBJECTIVE: Establish the live semantic-debt baseline, select one small
high-evidence canonical-owner or field family, and complete the first
evidence-backed semantic batch without regressing applicable exact or product
baselines.
SCOPE_HINT: Discover from the live repository. Prefer a bounded owner/field
family with multiple TH095-local consumers and focused exact units. Do not
start with the largest ECL interpreter, a persistent-format redesign, or a
repository-wide anonymous-field sweep.
STOP_CONDITION: One coherent batch has a durable evidence record separating
observed, corroborated, inferred, and unknown meaning; every applicable
affected exact/product/format/runtime check has been run and reported
independently; intended files are in one or more local English gpt-web:
checkpoint commits; unrelated pre-existing work remains preserved; and the
next batch is named.
RESUME_COMMIT: current
EVIDENCE_SEED: TH08 is workflow and adjacent-engine corroboration only. Require
TH095-local evidence for every accepted interpretation.

Communicate with me in Chinese. Write source, documentation, identifiers, and
Git commit messages in English. Work directly in the registered live TH095
repository with autonomous Bash, target-attested Ghidra, Wine/VC7.1, and
repo-native checks. Start by reading the repository rules and semantic plan,
inspecting current Git state, and running the required target/tracking/Ghidra
preflight. Use factory_report_semantic_debt as a heuristic router, never as a
progress metric, and supplement it with repository search and target evidence.
Preserve all existing dirty or untracked files and do not stage unrelated work.
Do not push. Keep semantic interpretation, Git checkpoints, exact receipts,
production closure, runtime storage, and runtime scenarios as separate states;
unknown is an accurate result. Treat TH095's target exact lane and reconstructed
Windows i386 product/runtime lane as the two independent semantic regression
oracles. Portable Windows, Linux, and Web work begins after semantic readiness
and cannot substitute for the i386 prerequisite.
```

The prompt deliberately lets GPT-web choose the first family from current
evidence. It does not freeze a stale filename, target address, or candidate
count into the workflow.

## Standalone prompt without automatic skill selection

```text
Run one autonomous evidence-first semantic reconstruction batch under
gpt-web-semantic-reconstruction-session-v1, which extends the general
gpt-web-reconstruction-session-v4 live-repository contract.

Inputs
- GAME_ID: th095
- SEMANTIC_OBJECTIVE: Establish the live semantic-debt baseline, select one
  small high-evidence canonical-owner or field family, and complete the first
  evidence-backed semantic batch without regressing applicable exact or
  product baselines.
- SCOPE_HINT: Discover. Prefer multiple TH095-local consumers, bounded owner
  scope, focused exact units, and no required behavior change. Avoid the
  largest ECL interpreter, persistent-format redesign, and broad anonymous-
  field sweeps as the first batch.
- STOP_CONDITION: One coherent batch is evidenced, validated, documented, and
  committed locally with an English gpt-web: subject; unrelated work is
  preserved; all verification planes and remaining unknowns are separate.
- RESUME_COMMIT: current
- EVIDENCE_SEED: TH08 is workflow/corroboration only; TH095 is authoritative.

Communicate with the user in Chinese. Write source, documentation, identifiers,
and Git commit messages in English.

1. Call factory_describe, factory_list_repositories, and
   factory_get_repository_status for th095. Report the actual branch, HEAD,
   upstream relation, and dirty/staged/untracked state. Existing work is live
   context: inspect and preserve it; do not reset, delete, or silently include
   it in a semantic commit.
2. Through factory_repository_run_shell, read AGENTS.md,
   docs/RE_HANDOFF.md, docs/ARCHITECTURE.md, docs/RE_WORKFLOW.md,
   docs/SEMANTIC_RECONSTRUCTION.md, the relevant source/ledgers/build scripts,
   and recent relevant history. Run:
     python3 scripts/verify-target.py
     python3 scripts/report-reconstruction-status.py --summary
     python3 scripts/validate-tracking.py --require-target
     python3 scripts/ghidra.py check
3. Record the live baseline of function/extent exactness, production closure,
   runtime storage, and runtime scenario validation independently. Historical
   totals are orientation only. Dirty/non-ignored state may make Factory replay
   ineligible; repo-native checks remain engineering feedback, not receipts.
   TH095 follows exact baseline -> reconstructed Windows i386 product closure
   and runtime-owner feedback -> semantic reconstruction -> portable products.
   Preserve the first two lanes as independent semantic regression oracles;
   never use a modern port to replace the i386 prerequisite.
4. Call factory_report_semantic_debt for th095/src. It is a lexical router
   bound to live HEAD/status with zero exactness and semantic-evidence credit.
   Page only as needed. Candidate counts—including zero—are not progress or
   completion. Supplement it with rg and other Bash searches for protocols,
   flags, owners, lifetime, and domain-specific debt the router cannot see.
5. Select one coherent owner, field, representation, or protocol family and
   state explicit exclusions. For every proposed meaning, inspect all relevant
   TH095 offsets, widths, signedness, reads/writes, callers/callees, strings,
   relocations, state transitions, lifetime, and storage owner. Use registered
   target-attested Ghidra operations. Analysis is provisional and has zero
   exactness credit.
6. Record meaning as observed, corroborated, inferred, or unknown. An adjacent
   game, decompiler label, numeric offset, visual observation, attractive name,
   or layout assertion is insufficient alone. Use a neutral name for bounded
   inference and retain opaque unknowns.
7. Make the narrowest natural C/C++ change. Preserve VC7.1 x86 ABI, layout,
   width, signedness, packing, bitfields, construction order, and translation-
   unit visibility. Prefer real owners/fields/aggregates/enums. Keep real wire
   formats, instruction streams, tagged representations, and platform ABI
   buffers byte-oriented. Do not create duplicate globals or mix unrelated
   control-flow/API redesign into the batch.
8. Match validation to the actual change surface. Replay every accepted unit in
   the affected object for private changes. Shared headers/layout/PCH/inline/
   owner changes require every affected object, the repository-required cold
   aggregate exact gate, and a cold product build. Serialization/protocol/
   persistence/callback/render/input/audio changes also require focused format
   tests and the smallest relevant runtime/output check when available. Report
   unavailable providers as unknown; never substitute another green check.
9. Append a completed entry to docs/SEMANTIC_RECONSTRUCTION.md only after the
   applicable checks pass. Update .reconstruction/game-knowledge.json only for
   concise durable game-local knowledge and keep factory_publication="none".
10. Inspect status, full diff, and staged diff. Stage only intended batch files
    and create a local English gpt-web: commit. Do not push. A commit is review
    state; an exact or product receipt proves only its own claim; neither proves
    the English semantic interpretation.

Handoff with session status; start/end commit and dirty state; selected and
excluded scope; router profile/scope/counts/limitations; target and Ghidra
attestation; observed/corroborated/inferred/unknown evidence; relied-on layout
facts; changed files and checkpoint hashes; commands/tests actually run;
affected-oracle closure; each verification plane; accepted facts separately
from semantic interpretation; retained unknowns; and the next useful batch.
```
