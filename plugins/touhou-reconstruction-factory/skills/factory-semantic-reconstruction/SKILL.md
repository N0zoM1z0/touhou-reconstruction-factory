---
name: factory-semantic-reconstruction
description: Recover evidence-backed types, names, owners, representations, and protocols in an already reconstructed Touhou game while preserving its applicable exact, product, format, and runtime baselines. Use for a bounded semantic reconstruction batch in a registered live repository. Do not use for broad beautification, new-game scaffolding, or cross-game knowledge publication.
---

# Factory Semantic Reconstruction

Follow `gpt-web-semantic-reconstruction-session-v1`, which extends
`gpt-web-reconstruction-session-v4`. Work autonomously in the registered live
game repository. The Factory supplies routing, target-bound analysis,
composable Bash, and independent replay; it does not decide meaning for you.

When the selected game is TH095, read
[`references/th095-start.md`](references/th095-start.md) before changing source.

## Establish the semantic session

Require a game ID, one semantic objective, and a measurable stop condition. A
scope hint, prior checkpoint, and evidence seed are optional.

1. Call `factory_describe`, `factory_list_repositories`, and
   `factory_get_repository_status`. Report the real branch, HEAD, upstream, and
   dirty/staged/untracked state. Preserve existing work.
2. Read `AGENTS.md`, the current handoff, architecture/workflow documents,
   semantic plan, relevant source, ledgers, build scripts, and recent relevant
   history through `factory_repository_run_shell`.
3. Run the repository's target and tracking preflight. Attest the selected
   IDA/Ghidra provider before relying on it.
4. Record the live status of function/extent exactness, production closure,
   runtime storage, and runtime scenario planes separately. Historical numbers
   orient the session but never replace a live check.

Semantic reconstruction does not require a false whole-project exactness claim:
an explicit residual may remain unknown. It does require a target-specific
exact baseline plus compile/link closure and available runtime-owner feedback
from the corresponding historical-platform product. For Windows PE this is the
reconstructed Windows i386 product; for PC-98 it is the corresponding 16-bit
product/runtime environment. A modern port cannot substitute for either
prerequisite.

## Route, then bound one batch

Call `factory_report_semantic_debt` for a repository-relative source scope when
useful. Its raw-member, absolute-address, anonymous-identifier, and opaque-
storage findings are lexical candidates only. Preserve its profile, scope,
HEAD/status binding, counts, pagination, skipped paths, and limitations in the
handoff. Never convert counts—including zero—into a completion percentage.

Supplement the router with broad composable Bash searches. It does not find all
numeric opcodes and operand selectors, stable resource IDs, flag namespaces,
duplicate owners, representation boundaries, or lifetime mistakes.

Select one coherent owner, field, representation, or protocol family. Prefer
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

## Close the affected regression surface

Treat the target exact lane and the reconstructed historical-platform
product/runtime lane as the two independent semantic regression oracles. A
batch must preserve both when applicable. Their agreement reduces false
positives but does not prove the chosen English interpretation. Portable
products are later consumers after semantic readiness, not prerequisite
oracles.

- For a private field/name/expression change, replay every accepted unit in the
  affected object and compile the complete declared production graph or the
  repository-defined equivalent.
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

## Record and checkpoint

After checks pass, append one concise game-local batch record containing scope
and addresses; observed, corroborated, inferred, and unknown evidence; layout
and ABI facts; exact results; product/format/runtime results or unavailable
state; and the raw forms removed. Make no project-wide percentage claim.

Update `.reconstruction/game-knowledge.json` only for a durable game-local fact,
recipe, pitfall, decision, or unknown. Keep `factory_publication="none"`. Never
edit or publish Factory cross-game knowledge.

Inspect the full worktree and staged diff, stage only the batch, and create an
English local commit whose subject begins `gpt-web:`. Exclude unrelated existing
work. Do not push. The checkpoint is review/resume state, not semantic or
exactness proof.

## Handoff

Report session status; game/objective; starting and ending commit and dirty
state; selected and excluded scope; router profile/scope/counts/limitations;
target and analysis attestation; observed/corroborated/inferred/unknown evidence;
layout/ABI facts; changed files; checkpoint commits; tests actually run;
affected-oracle closure; every verification plane; accepted receipt facts
separately from semantic interpretation; retained unknowns; and the next useful
batch.
