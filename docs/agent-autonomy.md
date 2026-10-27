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
- repository-selected IDA or Ghidra operations as high-value atomic tools;
- repository-native build, Wine, compiler, object-comparison, and Oracle scripts;
- replay receipts and the acceptance registry as a separate truth boundary.

Disposable source-only workspaces remain useful for explicitly isolated or
throwaway experiments. They are not the default reconstruction environment.

## Keep exploration light

Every registered repository can read every other registered repository at
`/references/<id>`. New registrations join automatically; individual reference
allowlists are unnecessary. Only the selected repository is writable.

Ordinary Bash and analysis do not require complete environment scans,
implementation hash refreshes, complete ledger validation or full replay.
Ghidra discovery is static and useful queries run directly. Report what was
actually checked; keep explicit exactness verification separate and run only
the comparisons needed by the current work.

On 2026-10-27, a scoped public-relay smoke read actual source for all 156
directed pairs among thirteen registered repositories, confirmed read-only
reference access, and completed a useful query through all sixteen analysis
providers. It ran no whole-game build or replay. Detailed outputs remain in
ignored operator state; this observation is not a continuing health claim.

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

## Bitter lesson: a campaign is not one browser conversation

The early hand-written prompts were ugly but productive because they gave Web a
strong objective, broad autonomy, distrust of stale claims, fast Oracle
feedback, and frequent Git checkpoints. Later Factory prompts accidentally
coupled that useful open-ended campaign posture to one conversation: after a
successful batch or negative search they repeatedly ordered the model to keep
working in the same chat. Overnight use showed the operational failure. Long
tool histories and outputs eventually made the browser slow or unusable even
though the repository was healthy and the work could have continued in a fresh
conversation.

The corrected rule separates durations:

- the reconstruction or semantic campaign is long lived;
- a Git/evidence batch is one reviewable transaction; and
- a GPT-web conversation is an adaptive bounded delivery interval chosen by the
  agent from task difficulty, validation latency, browser responsiveness, and
  remaining reliable context.

The agent should make serious progress, but it is not required to finish the
campaign or a fixed number of batches in one conversation. It finishes or
reverts the active experiment, runs applicable checks, commits coherent work,
and writes a precise continuation handoff before the client becomes fragile.
The next conversation first audits live Git and dirty state, so a disconnect is
not required before handoff is appropriate.

An intentionally ambitious moving target can still be useful. The older TH04
prompt's 99% target helped sustain exploration because authored boundary
discovery could expand the denominator while exact reconstruction improved the
numerator. Exact-phase prompts may therefore use 99.5% reviewed authored
functions and bytes as campaign pressure, provided they name those denominators
and never reinterpret them as executable, product, or whole-game coverage.
Crossing the moving target grants Web no completion authority; the operator and
a later independent audit decide when to stop the campaign.

External chat scheduling is an operator concern. In this installation the
operator may use a browser userscript to submit subsequent conversations, but
that implementation is deliberately absent from prompts, skills, contracts,
and game ontology. The model only needs to know that work may continue in a
later conversation from repository state. Leaking a particular scheduler or
queue into the task prompt adds irrelevant mechanism, couples the workflow to a
personal client, and encourages the model to manage orchestration instead of
reconstruction.

## Capability boundary versus truth boundary

These are intentionally different boundaries.

| State | Meaning | Exactness credit |
|---|---|---:|
| IDA/Ghidra result | Repository-selected semantic hypothesis | None |
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
a game/repository, target identity, and analysis project, and report the selected context. Sharing the executable must not merge analysis
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

TH04 and TH095 can reuse their existing projects and query scripts directly
through the shared Factory launcher. A separate per-game HTTP service is not
required. The native Ghidra launcher reads the selected project without full
installation or target preflights. Native IDA similarly uses the selected
headless database and a metadata comparison, with no repeated mapped-byte scan.
Useful metadata edits remain available; analysis is always provisional.

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
parity with historical fixtures before the old bridge is removed. TH09 and
TH10 demonstrate starting directly in the target format, while TH04, TH08,
TH095, and TH105 may temporarily use accurate per-repository compatibility
profiles.

## Scope

The registered repository ID is the source-work selection boundary. The shared
Factory MCP serves every game, while adapters and provider registrations bind
the selected repository to its targets, toolchain family, analysis provider,
and replay workflow. TH09 and TH10 each required one Factory registration and
adapter-compatible repository; GPT-web continued to use the same MCP and prompt
family.
