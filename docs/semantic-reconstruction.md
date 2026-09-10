# Semantic Reconstruction Workflow

## Scope

Semantic reconstruction is the evidence-backed conversion of already recovered,
target-layout-shaped source into maintainable types, names, owners, and
protocols. It is an engineering phase shared by reconstruction repositories,
not a new path into the Truth Kernel and not a repository-wide beautification
pass.

The normative Web contract is
[`gpt-web-semantic-reconstruction-session-v2`](../contracts/gpt-web-semantic-reconstruction-session-v2.json).
It extends the general live-repository
[`gpt-web-reconstruction-session-v4`](../contracts/gpt-web-reconstruction-session-v4.json)
contract, so autonomous Bash, target-attested analysis, local Git checkpoints,
game-local knowledge, replay receipts, and acceptance boundaries remain
unchanged.

For historical-platform reconstruction, the required order is:

```text
target-specific exact baseline
  -> corresponding historical-platform product closure and runtime-owner audit
  -> semantic reconstruction with both feedback lanes
  -> portable platform products
```

For Windows PE games the second stage is the reconstructed Windows i386
compile/link/runtime product. For PC-98 games it is the corresponding 16-bit
product and runtime environment. A known exact residual may remain honestly
`unknown`; this does not permit skipping the native product prerequisite.

## Shared vocabulary

- A **semantic-debt candidate** is a heuristic route to source that may encode
  known meaning as a raw offset, anonymous identifier, absolute view, opaque
  range, or unnamed protocol. It is not evidence that the source is wrong.
- A **semantic batch** is one coherent owner, field, representation, or
  protocol family changed and validated as a reviewable unit.
- A **semantic campaign** is the autonomous outer loop that commits successive
  bounded batches against one user objective without requesting permission
  after every successful batch.
- An **evidence record** separates observed, corroborated, inferred, and unknown
  meaning, with target addresses and limitations.
- A **regression baseline** records the live pre-edit state of every applicable
  exact, product, format, and runtime plane.
- **Affected-oracle closure** means that every check required by the actual
  change surface was rerun. It does not make the English interpretation true.
- A **semantic checkpoint** is a local `gpt-web:` commit containing a coherent
  batch and its evidence record. It is durable review state, not an Oracle
  verdict.
- A **campaign milestone** is a committed source state at which broad native
  gates and Factory receipts are closed once for that state rather than
  redundantly before another planned edit.
- **Semantic completion** is a qualitative game-local exit audit. Candidate
  counts, checked boxes, or an arbitrary number of batches never imply it.

`semantic_evidence` and `semantic_ownership` already exist as Truth Kernel claim
types. They describe bounded assertions, not a whole-project completion bit.
The current Factory has no live semantic-completion driver or acceptance
policy. Exact and product receipts created during a semantic batch may be
accepted for their own narrow claims; that acceptance does not certify a name,
type, protocol interpretation, or semantic milestone.

## One campaign of bounded loops

```mermaid
flowchart LR
    P["Live preflight<br/>HEAD · dirty state · target<br/>current plane baselines"] --> R["Route candidates<br/>Factory heuristic + Bash search<br/>counts are not progress"]
    R --> B["Bound one semantic batch<br/>one owner / field / protocol family<br/>explicit exclusions"]
    B --> E["Build evidence packet<br/>reads · writes · widths · xrefs<br/>observed / corroborated / inferred / unknown"]
    E --> C["Change natural source<br/>real owner · typed layout · enum<br/>retain genuine byte-oriented forms"]
    C --> V1["Affected exact replay<br/>function / object / aggregate<br/>according to change surface"]
    C --> V2["Historical-platform product feedback<br/>cold build · initialized-data owners<br/>bounded native runtime transition"]
    V1 --> D{"All applicable checks<br/>and evidence complete?"}
    V2 --> D
    D -->|"No"| X["Keep or revert experiment<br/>record contradiction or unknown<br/>do not broaden silently"]
    X --> E
    D -->|"Yes"| K["Evidence record + local gpt-web: commit<br/>report planes separately"]
    K --> S{"Campaign stop condition<br/>independently audited?"}
    S -->|"No: continue without asking"| R
    S -->|"Yes / real blocker / context boundary"| H["Close milestone gates<br/>durable handoff + exact next batch"]
```

The two validation branches are coupled feedback but independent truth. A byte-
exact result does not prove an English name. A successful build or runtime path
does not prove target identity. A semantic improvement may not silently spend
an already accepted exact, build, format, or runtime baseline.

This dual-oracle prerequisite is the phase's main false-positive defense. The
target exact oracle catches code-generation, extent, relocation, and configured
byte regressions. The reconstructed historical-platform product/runtime oracle
catches compile/link gaps, initialized-data ownership, storage identity,
lifetime, and exercised behavior that function exactness cannot see. Requiring
a semantic change to preserve both substantially narrows the space of plausible
but wrong refactors. Their agreement still does not prove an English name, so
the evidence record remains mandatory.

The outer campaign loop is the throughput mechanism. A batch remains small
enough to inspect, validate, commit, revert, and bisect, but its successful
checkpoint is not a reason to stop the Web session. The agent refreshes live
state and proceeds to the next family without asking for permission. It stops
only after an independent exit audit supports the supplied campaign condition,
a concrete blocker prevents useful work, a materially different scope decision
is needed, or remaining context cannot safely close another batch. At a context
boundary it first finishes or reverts the active experiment and writes the
evidence and next batch into repository state.

## Select the batch

Start with `factory_report_semantic_debt` when it is available. The tool scans a
repository-relative C/C++ scope in the live worktree and returns paginated
candidates in four deliberately narrow categories:

- `raw-member-access`;
- `absolute-address`;
- `anonymous-identifier`; and
- `opaque-storage`.

The report binds its result to the current HEAD and Git status digest. It also
fixes `routing_only=true`, `completion_metric=false`,
`exactness_credit="none"`, and `semantic_evidence_credit="none"`. A zero count
means only that the selected lexical profile found no matches in that scope.
The report intentionally misses numeric interpreter cases, sibling opcode
tables, resource and sound IDs, flag namespaces, lifetime errors, duplicate
owners, and domain-specific naming debt. Use broad
`factory_repository_run_shell` searches and target analysis to supplement it.

Prefer an early batch with several independent target-local reads or writes, a
small caller/owner surface, existing focused exact units, and no required
behavior change. Do not begin with a repository-wide rename, several unrelated
managers, a large interpreter rewrite, persistent-format redesign, or a name
supported only by an adjacent game.

## Recover meaning accurately

For every selected field or protocol value, inspect the target-local access
offset and width, signedness, read/write sites, bit operations, callers and
callees, strings, relocations, state transitions, lifetime, and canonical
storage owner. Record evidence as:

- **observed** when it is directly present in the canonical target,
  target-bound analysis, exact code shape, or a bounded target/runtime
  observation;
- **corroborated** when independent target-local consumers agree, or an
  adjacent game agrees with target-local evidence;
- **inferred** when the target-local role is bounded but lacks independent
  naming evidence; use a neutral name and state the limitation; or
- **unknown** when only storage, width, alignment, lifetime, extent, or a weaker
  relationship is known.

Adjacent games are workflow and corroboration sources, never substitutes for
the selected target. Decompiler labels and attractive names are hypotheses.
Focused `sizeof` and `offsetof` assertions prove only the declared layout.

Prefer real owners, fields, aggregates, enums, bitfields, and explicit protocol
types. Preserve byte addressing when it is the actual semantics of a serialized
format, instruction stream, tagged representation, or platform ABI buffer. Do
not create duplicate globals for views inside an existing aggregate, hide
unknown meaning behind a union or accessor, or mix a typed recovery with
unrelated control-flow and API redesign.

## Regression scope

| Actual change surface | Exact lane | Product, format, and runtime lane |
| --- | --- | --- |
| Private field/name/expression in one object | Run every affected exact unit. | Compile the smallest affected historical-platform surface; keep broad product closure explicitly pending until a campaign milestone unless the repository requires it immediately. |
| Shared header, class layout, inline body, PCH, or owner | Replay every affected object, then the repository-required cold aggregate exact gate. | Cold compile/link; run a bounded runtime transition when identity, lifetime, initialization, or behavior can change. |
| Serialization, protocol, persistence, callback, rendering, input, or audio | Strictly compare every touched function. | Run focused format/protocol tests, cold compile/link, and the smallest relevant runtime/output check when available. |

When the repository has no accepted unit or no deterministic runtime provider,
say `unknown` or `not applicable` with the reason. Never substitute a nearby
green check. Factory replay requires eligible committed source; repo-native
checks may still guide dirty work, but they are not accepted receipts.

Use a four-level feedback ladder:

1. During an edit, run syntax/layout checks and the smallest affected compile,
   object comparison, or target query.
2. Before a batch checkpoint, close every affected exact unit and native
   compile/link, format, or runtime surface.
3. Run aggregate exact and whole-product gates immediately for shared headers,
   layouts, PCH/inline bodies, ownership, sensitive protocols, or any focused
   failure that exposes cross-object risk.
4. At a campaign milestone and final handoff, close remaining repository-
   required aggregate exact, historical-platform product, and available runtime
   gates once for the current committed source.

Do not cold-replay the entire accepted Factory receipt set after every private
checkpoint when another planned source commit would immediately stale it. Use
repo-native Oracles for the rapid dirty-tree loop and issue current-source
receipts at meaningful committed milestones. A deferred or stale receipt plane
must be reported as non-current; batching receipt work changes cadence, not
truth.

## Record and checkpoint

An accepted game-local batch record should contain:

```text
Owner / field / protocol family and date
Scope: target addresses, functions, source files, object/profile
Observed: target-local facts
Corroborated: independent target-local and labeled adjacent-game evidence
Inference: chosen neutral names/types and confidence
Unknown: retained opaque or unresolved meaning
Layout/ABI: assertions and relationships relied on
Exact oracle: affected replay commands and results
Product/format/runtime: commands, results, or explicit unavailable state
Result: raw forms removed for this family; no project completion percentage
```

Append it to the game repository's semantic reconstruction document after the
checks pass. Update `.reconstruction/game-knowledge.json` only when a concise
fact, recipe, pitfall, decision, or unknown will materially help another game-
local session. Neither location publishes cross-game knowledge.

Create a local English `gpt-web:` commit after one coherent checked batch.
Inspect status, the full diff, and the staged diff; exclude unrelated existing
work. Do not push. Then refresh live state and begin the next batch. At a real
terminal condition, hand off the starting and ending commit/dirty state, all
completed checkpoints, selected and excluded scope, report profile and
limitations, evidence classes, layout facts, changed files, tests by feedback
level, broad gates run or explicitly deferred, every verification plane,
accepted receipts separately from semantic interpretation, retained unknowns,
and the exact next batch.

## Historical derivation from TH08

TH08 established the reusable workflow in commit `5592d853` and then exercised
it across typed runtime owners, protocol families, serialized storage, exact
relocations, and portable builds. Its history exposed several important
corrections that are part of this Factory contract:

- the lexical debt report is a work selector, not a completion denominator;
- one owner/field family per batch keeps evidence and regressions reviewable;
- exact VC7 bytes, portable/runtime behavior, and English meaning answer
  different questions;
- shared headers and owner changes expand replay scope beyond the edited file;
- raw serialized storage can be semantically correct and must not be typed for
  appearances;
- protocol debt remains after structural offset counts reach zero;
- value-equal globals can still be different physical objects with broken
  lifetime or callback state;
- exact source expression shape may require a narrowly scoped compatibility
  bridge, but a bridge cannot invent an owner or meaning; and
- aggregate failures must be classified before broadening a semantic batch.

TH08's later protocol passes also demonstrated that primary interpreter opcodes
can be readable while operand selectors and secondary streams remain raw. A
future game-local exit audit must therefore examine both structural candidates
and router-invisible protocol surfaces.

### Bitter lesson: do not port before native product closure

TH08 discovered this order late. A modern Linux product could compile, link,
and enter gameplay while its port-side startup temporarily populated target-
initialized data that the reconstructed VC7 Windows product did not actually
own. Running the real reconstructed i386 product exposed an empty
`g_EffectTemplates` table and the same owner class around Last Spell counts,
stage-result score data, and dialogue colors. Repairing those definitions in
their semantic translation units preserved all affected exact units while
closing the native product's actual data ownership.

The reusable lesson is not "test one more port." It is to complete and exercise
the corresponding historical-platform product before semantic reconstruction,
then preserve its native product/runtime lane alongside the target exact lane.
Portable products begin after the semantic prerequisite and become additional
consumers; they must never hide or supply missing ownership in the canonical
reconstruction.

## TH095: first Factory consumer

TH095 is the first repository intended to run this workflow from the shared
Factory rather than a game-specific semantic skill. Its historical entry point
is commit `339bb5a`, which declares semantic reconstruction as the next phase.
At the 2026-09-10 preflight, the canonical Japanese v1.02a target passed its
SHA-256/MD5 identity checks, target-attested Ghidra passed all six mapped byte
samples, and the ledgers reported 697 source-present authored functions, 696
exact functions, and 336,486 exact bytes. The production graph has 88 sources
and two profiles; its independently replayable `whole_build_closed` product
claim was established at the earlier immutable playable checkpoint.

These are entry baselines, not semantic evidence and not promises about the
next live worktree. Every Web session must rerun the current preflight. The
2026-09-10 worktree also contained four pre-existing untracked experiment files;
they must be inspected and preserved, not silently committed with a semantic
batch or deleted to make replay eligible.

For TH095, begin with:

```bash
python3 scripts/verify-target.py
python3 scripts/report-reconstruction-status.py --summary
python3 scripts/validate-tracking.py --require-target
python3 scripts/ghidra.py check
```

Use `factory_report_semantic_debt(repository_id="th095",
relative_path="src", category="all", ...)` for the first lexical routing
snapshot, then supplement it with repository search and target-attested Ghidra.
The first source batch should be a small, high-evidence owner or field family,
not the largest ECL interpreter, a persistent-format redesign, or a global
anonymous-field sweep.

TH095's native exact gate is `python3 scripts/replay-exact-units.py`; use one or
more `--source` selections for focused affected objects and the no-argument cold
run when a shared change requires the aggregate gate. Its product gate is
`python3 scripts/build-whole.py`, and target-independent maintenance closes with
`python3 scripts/ci.py` plus `git diff --check`. Run the smallest applicable
runtime or format check for behavior-sensitive batches, but keep the live
Factory runtime plane `unknown` until a deterministic target-bound runtime
provider exists.
