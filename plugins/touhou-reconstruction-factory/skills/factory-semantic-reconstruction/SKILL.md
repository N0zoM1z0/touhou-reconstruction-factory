---
name: factory-semantic-reconstruction
description: Run an autonomous campaign of bounded semantic reconstruction batches in an already reconstructed Touhou game while preserving applicable exact, historical-platform product, format, and runtime feedback. Use to recover evidence-backed types, names, owners, representations, and protocols in a registered live repository. Do not use for broad beautification, new-game scaffolding, ports, or cross-game knowledge publication.
---

# Factory Semantic Reconstruction

Follow `gpt-web-semantic-reconstruction-session-v2`, which extends
`gpt-web-reconstruction-session-v4`. Work autonomously in the registered live
game repository. The Factory supplies routing, target-bound analysis,
composable Bash, and independent replay; it does not decide meaning for you.

Also follow `worktree-recovery-and-analysis-artifacts-v1`. Do not assume this
skill was injected merely because the MCP app is connected. Read the Factory
contract/documentation paths named by the launch prompt when mounted; otherwise
the complete inline prompt remains authoritative.

When the selected game is TH095, read
[`references/th095-start.md`](references/th095-start.md) before changing source.

## Establish the semantic campaign

Require a game ID, one semantic objective, and a measurable campaign stop condition. A
scope hint, prior checkpoint, and evidence seed are optional.

1. Call `factory_describe`, `factory_list_repositories`, and
   `factory_get_repository_status`. Report the real branch, HEAD, upstream, and
   dirty/staged/untracked state. Preserve existing work.
2. Any non-clean state triggers a mandatory recovery review before a new batch
   is selected or edited, regardless of whether a disconnect is known. Inspect porcelain-v2
   status, complete staged/unstaged diffs, every relevant untracked path, the
   latest handoff and recent history, tests, and artifact manifests. Classify
   each path as recoverable current work, unrelated pre-existing work, generated
   ephemeral output, or unknown origin/intent. Finish/checkpoint recoverable work
   first; preserve/exclude unrelated work; never reset, delete, overwrite, or
   stage unknown work. Re-run this gate after a timeout, interrupted command, or
   unexpected status change. If an overlapping unknown cannot be isolated,
   report a concrete blocker.
3. Read `AGENTS.md`, the current handoff, architecture/workflow documents,
   semantic plan, latest committed semantic batch and named next batch,
   relevant source, ledgers, build scripts, and recent relevant history through
   `factory_repository_run_shell`. Do not redo a committed batch without new
   contradictory evidence.
4. Run the repository's target and tracking preflight. Attest the selected
   IDA/Ghidra provider before relying on it.
5. Inventory `.analysis/` total/top-level size without trusting its contents.
   Earlier artifacts are leads until their HEAD, target, database, tool, and
   command bindings are checked or reproduced.
6. Record the live status of function/extent exactness, production closure,
   runtime storage, and runtime scenario planes separately. Historical numbers
   orient the campaign but never replace a live check. Capture broad orientation
   once; later refresh only state invalidated by intervening changes.

Semantic reconstruction does not require a false whole-project exactness claim:
an explicit residual may remain unknown. It does require a target-specific
exact baseline plus compile/link closure and available runtime-owner feedback
from the corresponding historical-platform product. For Windows PE this is the
reconstructed Windows i386 product; for PC-98 it is the corresponding 16-bit
product/runtime environment. A modern port cannot substitute for either
prerequisite.

## Run a campaign of bounded batches

One batch is an inner transaction, not the session stop. After a successful
batch, refresh HEAD and worktree state, read the just-committed next-batch note,
and immediately select the next coherent family without asking the user for
permission. Continue until the supplied stop condition passes an independent
exit audit, a concrete evidence/tool boundary prevents useful progress,
continuation requires a materially different scope decision, or remaining
context cannot safely close another batch.

Under context pressure, finish or revert the active experiment, run its required
checks, write durable evidence, create a coherent checkpoint when warranted,
name the exact next batch, and only then hand off. Never leave useful work only
in chat context.

Call `factory_report_semantic_debt` for a repository-relative source scope when
useful. Its raw-member, absolute-address, anonymous-identifier, and opaque-
storage findings are lexical candidates only. Preserve its profile, scope,
HEAD/status binding, counts, pagination, skipped paths, and limitations in the
handoff. Never convert counts—including zero—into a completion percentage.

Supplement the router with broad composable Bash searches. It does not find all
numeric opcodes and operand selectors, stable resource IDs, flag namespaces,
duplicate owners, representation boundaries, or lifetime mistakes.
Prefer `git grep`/history for tracked content. For live untracked source, use
bounded `rg --hidden` searches excluding `.git`, `.analysis`, `build`, and
`.tools` unless a named ignored path is deliberately in scope. Never follow
repository-root symlinks because Wine `dosdevices/z:` can traverse the host.

For each loop, select one coherent owner, field, representation, or protocol
family. Prefer
multiple independent target-local consumers, bounded caller/owner scope,
existing focused exact units, high owner or pointer-width value, and no required
behavior change. State which adjacent files and families are excluded.

Do not begin with a repository-wide rename, several unrelated managers, a large
interpreter/control-flow rewrite, persistent-format redesign, or a meaning
supported only by another game.

## Build the evidence packet

For every proposed field, type, owner, or protocol value, inspect all relevant
target-local offsets, widths, signedness, reads, writes, bit operations, callers,
callees, strings, relocations, state transitions, lifetime, and storage identity.
Use `factory-analysis` for target-attested queries and record its attestation;
analysis carries zero exactness credit.

Classify meaning explicitly:

- **Observed:** directly present in the canonical target, target-bound analysis,
  exact code shape, or a bounded target/runtime observation.
- **Corroborated:** independent target-local users agree, or adjacent-game
  evidence agrees with target-local evidence.
- **Inferred:** target-local dataflow bounds a role without independent naming
  evidence; choose a neutral name and state the limitation.
- **Unknown:** only storage, width, alignment, lifetime, extent, or a weaker
  relationship is known; keep that uncertainty visible.

An adjacent game, decompiler label, numeric offset, visual observation, or
attractive English name is never sufficient by itself.

## Change natural source

Preserve the target ABI, offsets, widths, signedness, packing, bitfield behavior,
construction order, and translation-unit visibility. Prefer real canonical
owners, fields, aggregates, enums, bitfields, and explicit protocol types. Add
focused size/offset assertions for layout facts the batch relies on; remember
that an assertion proves layout, not meaning.

Keep serialized formats, instruction streams, tagged representations, and
platform ABI buffers byte-oriented when that is their real semantics. Do not
create duplicate globals for views inside an existing owner, hide unknown
meaning behind a union/accessor/cast, or combine typing with unrelated control-
flow and API redesign.

Use `factory_repository_run_shell` for edits and every unlisted in-repository
investigation. Broad Bash remains the primary composition surface; the semantic
router and other atomic tools add identity and convenience without restricting
your choices.

Use command-local temporary storage for one-shot analysis output. For multi-
command work, reuse one `.analysis/gpt-web/<campaign-id>/` scratch root and
create a manifest before its first large output. Record campaign/game identity,
starting/current HEAD, state, and each artifact's path, class, producer, input
binding, size, references, and disposition. Treat 256 MiB as a soft campaign
review budget and 64 MiB as the large-artifact threshold. Prefer bounded
provider queries and registered Ghidra/IDA/Wine state; do not copy a provider
database, Wine prefix, whole-program dump, or worktree per probe.

## Close the affected regression surface efficiently

Treat the target exact lane and the reconstructed historical-platform
product/runtime lane as the two independent semantic regression oracles. A
batch must preserve both when applicable. Their agreement reduces false
positives but does not prove the chosen English interpretation. Portable
products are later consumers after semantic readiness, not prerequisite
oracles.

- For a private field/name/expression change, run every affected exact unit and
  the smallest historical-platform compile/link surface that can expose the
  change. Keep broader product closure explicitly pending until the next
  campaign milestone when the repository does not require it immediately.
- For a shared header, layout, inline body, PCH, or owner change, replay every
  affected object, run the repository-required cold aggregate exact gate, cold
  compile/link the product, and exercise a bounded runtime transition when
  identity, lifetime, initialization, or behavior can change.
- For serialization, protocol, persistence, callback, rendering, input, or
  audio, strictly compare every touched function, run focused format/protocol
  tests, cold compile/link, and run the smallest relevant runtime/output check
  when available.

Use repo-native checks while source is dirty. Use `factory-replay` only for a
discovered claim eligible against committed source. A passing exact or product
receipt proves only its own claim; it does not verify the English interpretation.
When an applicable unit/provider is unavailable, report `unknown` or `not
applicable` with the reason instead of substituting a nearby green result.

If a broader regression fails, classify the failure before changing source.
Do not silently broaden the batch, weaken an oracle, or publish aggregate totals
from a stale baseline.

Use four feedback levels instead of rerunning the most expensive gate after
every edit:

1. **Edit loop:** syntax, layout assertions, smallest affected compile/object
   comparison, and only the analysis query needed to answer the current
   question.
2. **Batch closure:** every affected exact unit plus the affected native compile,
   link, format, or runtime surface.
3. **Immediate broad closure:** cold aggregate exact and whole-product gates for
   shared header/layout/PCH/inline/owner changes, sensitive protocols, or any
   focused result exposing cross-object risk.
4. **Campaign milestone:** close remaining repository-required aggregate exact,
   historical-platform product, and available runtime gates once for the current
   committed state.

Do not replay the full accepted Factory receipt set after every private
checkpoint when the next planned source commit would immediately stale it.
Issue claim-specific receipts at a meaningful current-source milestone and
query the registry in summary mode unless candidate-level rejection diagnostics
are needed. A deferred or stale receipt plane must remain explicitly non-current.

## Record and checkpoint

After checks pass, append one concise game-local batch record containing scope
and addresses; observed, corroborated, inferred, and unknown evidence; layout
and ABI facts; exact results; product/format/runtime results or unavailable
state; and the raw forms removed. Make no project-wide percentage claim.

Measure `.analysis/` growth before the checkpoint. Retain compact conclusions
in tracked evidence and delete only explicit current-session scratch paths whose
ownership, inactive producer, reproducibility/non-need, and lack of references
are established. Never bulk-delete `.analysis/`, delete by age alone, or touch
legacy-unknown/shared provider state. Update the manifest and report retained
bytes and large artifacts.

Update `.reconstruction/game-knowledge.json` only for a durable game-local fact,
recipe, pitfall, decision, or unknown. Keep `factory_publication="none"`. Never
edit or publish Factory cross-game knowledge.

Inspect the full worktree and staged diff, stage only the batch, and create an
English local commit whose subject begins `gpt-web:`. Exclude unrelated existing
work. Do not push. The checkpoint is review/resume state, not semantic or
exactness proof.

After the checkpoint, return to batch selection and continue. Do not turn the
normal completion of one reviewable unit into a campaign handoff.

## Handoff

Report the actual terminal condition; game/campaign objective; starting and
ending commit and dirty state; every completed checkpoint; selected and
excluded scope; router profile/scope/counts/limitations;
recovery classifications/actions/unknowns; starting and ending `.analysis/`
bytes, scratch-manifest state, and retained/removed artifact disposition;
target and analysis attestation; observed/corroborated/inferred/unknown evidence;
layout/ABI facts; changed files; checkpoint commits; tests actually run;
affected-oracle closure and explicitly deferred broad gates; every verification
plane; accepted receipt facts separately from semantic interpretation; retained
unknowns; and the exact next batch.
