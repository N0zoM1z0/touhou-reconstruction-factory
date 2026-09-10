# Agent Autonomy and Tool Composition

## Decision

The Factory exists to make a capable reconstruction agent more accurate,
efficient, resumable, and reviewable. It must not reduce the agent to a fixed
workflow containing only operations anticipated by the Factory authors.

The default GPT-web reconstruction surface is therefore:

- a registered live game repository, including its current dirty, untracked,
  and ignored state;
- broad composable Bash inside that repository;
- local Git commits as durable review checkpoints;
- target-attested IDA or Ghidra operations as high-value atomic tools;
- repository-native build, Wine, compiler, object-comparison, and Oracle scripts;
- replay receipts and the acceptance registry as a separate truth boundary.

Disposable source-only workspaces remain useful for explicitly isolated or
throwaway experiments. They are not the default reconstruction environment.

## The bitter lesson from the earlier repositories

TH04, TH08, TH095, and TH105 accumulated hundreds of useful `gpt-web:` commits.
The productive pattern was not a complete remote API designed in advance. It
was a strong model with Bash plus IDA/Ghidra, repository-local scripts, and Git.
The agent composed unanticipated investigations, repaired intermediate states,
and checkpointed coherent progress so later sessions could review, bisect,
continue, or roll back it.

The first Factory workspace implementation preserved isolation but removed
important capabilities: current local state, ignored targets and toolchains,
Wine prefixes, native analysis assets, and Git commits. The first TH105 Web test
showed the consequence directly: it could produce a plausible source diff and
find a semantic timer bug, but it could not run the modified source through the
VC8/Wine Oracle or leave a normal repository checkpoint.

The design correction is not to predict every missing operation and add another
narrow tool. It is to restore a general composition surface while retaining
stronger atomic tools where they materially improve evidence quality.

## Capability boundary versus truth boundary

These are intentionally different boundaries.

| State | Meaning | Exactness credit |
|---|---|---:|
| IDA/Ghidra result | Target-attested semantic hypothesis | None |
| Bash/build result | Engineering feedback observed in the live repository | None by itself |
| `gpt-web:` commit | Durable, reviewable source checkpoint | None by itself |
| Completed replay job | Execution reached a terminal state | None by itself |
| Passing Oracle receipt | The declared comparison passed for its bound inputs | Receipt scope only |
| Accepted current receipt | Truth Kernel admitted the result under current policy | Accepted scope only |

The Factory constrains the last two transitions rigorously. It does not use
those constraints as a reason to prevent source exploration, compilation,
experimentation, or local checkpoint creation.

## Atomic tools and Bash

Atomic tools and Bash are complements.

Use an atomic tool when it provides a valuable property that ad hoc shell text
does not: stable discovery, schema validation, target identity attestation,
durable replay state, bounded pagination, receipt construction, or acceptance
policy evaluation. Use Bash when the task needs composition, a repository-native
script, a new diagnostic, multiple Unix tools, or an operation the Factory did
not predict.

Adding an atomic tool must not silently prohibit the corresponding lower-level
work. A tool is an accelerator and evidence-strengthening interface, not a claim
that every legitimate workflow has been enumerated.

## Git checkpoint policy

GPT-web may edit and commit directly in a registered game repository. A good
checkpoint contains one coherent unit, stages only intended files, follows the
game's instructions, records checks actually run, and uses an English subject
beginning with `gpt-web:`.

Commands are deliberately non-transactional. A failed or timed-out command may
leave partial files, just as a local terminal would. The command record captures
before/after Git state and output; the agent must inspect the worktree before
retrying. This behavior preserves useful compilation artifacts and debugging
state instead of pretending failure rolled them back.

Factory-launched repository commands share the same advisory repository lock as
Factory replay, acceptance, snapshots, and analysis. This prevents two Factory
operations from silently racing. A normal local terminal or another program can
still change the repository because the Factory does not claim exclusive host
ownership; every bounded operation therefore records or rechecks current source
and Git identity.

The live provider does not offer network access, so it cannot publish with
remote `git push`. Local commit creation and remote publication are separate
operations.

## Shared tools and per-game state

Tool ownership has three layers:

| Layer | Examples | Preferred location |
|---|---|---|
| Immutable shared installation | Ghidra distribution, JDK, objdiff, compiler package archives | Factory-managed shared tool root |
| Game-selected declaration and wrapper | exact version/hash, target, command line, environment, Oracle stages | tracked game repository metadata/scripts |
| Mutable game state | Wine prefix, Ghidra/IDA database or project, build outputs, caches | game-local ignored state or a game-bound Factory state directory |

One Ghidra installation can serve multiple games. Each request must still select
a game/repository, target identity, and analysis project, and the result must be
attested against that target. Sharing the executable must not merge analysis
state or target identity.

Wine itself is a shared host runtime. A Wine prefix is stateful and remains
game/toolchain specific because registry contents, installed compiler files,
absolute paths, and concurrent `wineserver` state can differ. Compiler binaries
may be shared when their content identity is locked, while each game retains the
wrapper and environment declaration that selects them.

Existing repositories currently keep substantial assets under ignored `.tools`
directories. The live provider supports that layout immediately. Migration to a
shared store is an optimization: move one proven immutable component at a time,
retain content hashes and game wrappers, then replay the affected fixtures. It
must not be a prerequisite for useful reconstruction work.

The current TH04 and TH095 Ghidra bridges run as separate target-bound service
instances even though they select the same Ghidra/JDK versions and their Ghidra
`bom.json` files have the same SHA-256. That
is a bridge limitation, not the desired ownership model. The migration target
is one content-addressed immutable Ghidra/JDK installation selected by a Factory
analysis broker, with a separate project, target attestation, serialization
scope, and mutable state root for each game. Reusing an executable never reuses
or weakens target identity.

TH09 proves the corresponding IDA migration shape. The shared Factory MCP
launches `ida-pro-mcp` directly over stdio, while the private provider
registration supplies the target-specific repository and executable identity.
There is no `mcp_for_gptweb` checkout or per-game HTTP service. The native
provider offers composable IDA reads and database metadata edits, but it
re-attests the private PE and active mapped bytes on every request and never
offers target-byte patching. Thus autonomy over useful analysis state does not
weaken the target boundary.

## Migration principle

The legacy repository layouts are evidence-bearing migration inputs, not the
Factory's permanent schema. Compatibility code may read their current ledgers,
ignored `.tools` directories, global Wine prefixes, and provider conventions so
work can continue now. Core ontology, receipts, acceptance, jobs, repository
work, and provider identities must not encode those accidents as universal
concepts.

After the infrastructure is stable, each existing game can be migrated to one
Factory-authored repository profile. A target profile should declare, in one
place:

- target identity and provenance;
- platform and exact toolchain identities;
- shared immutable tool selections;
- game-local mutable state roots;
- analysis project and target binding;
- canonical build, comparison, and Oracle stages;
- claim, extent, and receipt interfaces;
- game-local knowledge input and checkpoint conventions.

Migration is allowed to change repository layout and scripts. It must preserve
or strengthen the evidence meaning, carry explicit unknowns forward, and prove
parity with historical fixtures before the old bridge is removed. Therefore a
new TH09 repository should start in the target format, while TH04, TH08, TH095,
and TH105 may temporarily use accurate per-repository compatibility profiles.

## Scope

The registered repository ID is the source-work selection boundary. The shared
Factory MCP serves every game, while adapters and provider registrations bind
the selected repository to its targets, toolchain family, analysis provider,
and replay workflow. Adding TH09 therefore means registering and adapting the
TH09 repository once; GPT-web continues to use the same MCP and prompt.
