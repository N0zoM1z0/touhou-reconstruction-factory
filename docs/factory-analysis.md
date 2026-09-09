# Touhou Reconstruction Factory: Evidence, Architecture, and Roadmap

> Status: architecture working paper with an executable v0 foundation
> Snapshot date: 2026-09-09  
> Primary requirements source: `/tmp/vc_sth.txt`  
> Evidence base: local repositories, their current reports, selected source and documentation, and full commit-subject histories with focused commit inspection

## 1. Executive Conclusion

The proposed project should be a **reconstruction control plane**, not another game repository and not a monorepo containing every reconstruction.

Its durable responsibilities are:

1. define shared evidence, state, artifact, verification, and handoff contracts;
2. provide platform and toolchain profiles rather than pretending every binary format has the same oracle;
3. run cheap diagnostic oracles continuously while reserving acceptance for strict, fail-closed gates;
4. make interrupted GPT Web work resumable through persistent jobs and content-addressed artifacts;
5. turn cross-project lessons into reviewed rules and regression fixtures instead of larger diary documents;
6. keep faithful reconstruction and portable-product development as separate planes with an explicit handoff.

The old PC-98 games and the Windows PE games should share the control-plane model, schemas, lifecycle, and command vocabulary. They should **not** share an undifferentiated executable, linker, relocation, boundary, or ownership oracle. The correct shape is a shared core plus platform and compiler profiles:

```text
shared reconstruction contracts
├── PC-98 / DOS profile
│   ├── MZ executable model
│   ├── OMF objects and libraries
│   ├── Borland C++ / TASM / TLINK behavior
│   └── segment:offset, near/far, DGROUP, and PC-98 runtime adapters
└── Windows PE profile
    ├── PE/COFF image model
    ├── imports, resources, relocations, and image layout
    ├── VC7/VC7.1 non-LTCG ownership profile
    └── VC8 LTCG/chunked physical-ownership profile
```

The most consequential workflow correction is that byte-exact work and whole-program work cannot be a one-way sequence. A whole-build skeleton must exist early and run repeatedly. Function exactness remains an independent acceptance claim; link, owner, layout, data, and ABI failures feed corrections back into source and ledgers. Semantic rewriting still belongs after faithful closure, although semantic evidence may be recorded from the beginning.

### 1.1 What “Factory” Should Mean

The Java factory analogy is useful if it means an **Abstract Factory that creates one coherent family of reconstruction services from a project specification**. It should not mean a command that copies a directory tree.

Conceptually:

```text
ProjectSpec
  + TargetIdentity
  + selected/detected platform capabilities
  + selected/detected toolchain capabilities
  + repository policy
          │
          v
ReconstructionFactory.create(...)
          │
          v
ReconstructionKit
  ├── target attestor
  ├── boundary/origin providers
  ├── compiler and build planner
  ├── exact and whole-image oracles
  ├── workflow/task catalog
  ├── CI gate policy
  ├── artifact store
  ├── handoff/lease service
  └── repository-scoped MCP surface
```

The created objects must be compatible with one another. A PC-98 target cannot accidentally receive a PE layout oracle; a VC8 LTCG project cannot receive a provider that assumes one independently comparable COFF function section per semantic function. This coherent-family guarantee is the real value of the Factory pattern here.

Implementation should favor composition and declared capabilities over a deep inheritance hierarchy. `pc98-mz-omf`, `windows-pe-coff`, `msvc7`, and `msvc8-ltcg` are providers selected by the factory. A game repository supplies data and narrow overrides; it does not fork the shared protocol.

### 1.2 The First Unification Boundary: the Truth Kernel

The first thing to standardize is a small **truth kernel**: identity, vocabulary, claim types, evidence references, and verdict envelopes. Everything else—including bootstrap, workflow, CI, knowledge harvesting, and resumable MCP jobs—depends on it.

The current repositories demonstrate terminology and state drift:

- TH07's `functions.csv` places inventory, origin, source location, workflow status, match percentage, evidence prose, agent owner, and notes in one row.
- TH08 separates `mapping.csv`, a headerless `implemented.csv`, and `matches.csv`, but the same function identity is repeated across them.
- TH095 and TH105 add `function-origins.csv`, yet their origin vocabulary already differs (`authored` versus `authored_game`) and confidence values mix evidence maturity with exact verdicts.
- `claims.csv` in the Windows repositories is a work-reservation table (`address`, agent `owner`, start time, branch), not a truth claim. In three repositories it is currently empty.
- `owner` can mean the agent holding work, the semantic subsystem, the source TU, the emitted object, or the final-image physical owner.
- `matching` is sometimes a workflow state even though source presence, successful compilation, codegen exactness, and ownership are independent claims.

The factory vocabulary should reserve terms unambiguously:

| Term | Reserved meaning |
|---|---|
| `claim` | A typed, evidence-backed assertion about a subject |
| `verdict` | An oracle result: `pass`, `fail`, `incomplete`, or `error` |
| `work_lease` | Temporary agent/session ownership of a work packet |
| `source_owner` | Canonical source declaration/definition owner |
| `object_owner` | Compiler/linker object or LTCG contribution owner |
| `physical_owner` | Final-image extent/chunk owner |
| `semantic_owner` | Runtime or domain subsystem that conceptually owns behavior/state |
| `source_present` | Source representation exists; no exactness implication |
| `codegen_exact` | Declared code extent passes an acceptance oracle |
| `whole_build_closed` | Canonical production graph satisfies its link policy |
| `whole_image_exact` | Complete declared image/layout contract passes |

The minimum truth-kernel graph is:

```text
Project -> Product -> TargetIdentity
                    -> ToolchainIdentity

Subject -> Claim -> OracleResult -> Evidence/ArtifactRef
   │         │
   │         └── scope + coverage + dependencies
   └── function | extent | data | source_unit | object | section | image

WorkPacket -> WorkLease -> Handoff
```

Work coordination is deliberately outside the truth graph. Losing a lease or handoff must not invalidate verified evidence; conversely, holding a lease grants no truth status.

### 1.3 Why This Must Come Before the Other Attractive Work

| Repository evidence | Failure if the Factory starts elsewhere | Truth-kernel requirement |
|---|---|---|
| TH105 reset from 1.06 to 1.06a | A better workflow efficiently accumulates evidence for the wrong target | Every dependent record binds to immutable target identity |
| TH04 has four products and 460 unreviewed authored candidates | A generated dashboard publishes a misleading 99% | Product graph, explicit denominators, and inventory-review claims |
| TH04's 5-byte Ghidra seed became a 398-byte extent | A common function table freezes provisional disassembler ranges | Subject extents and boundary evidence are versioned claims |
| TH095 is 696/697 exact but its whole link remained deeply unresolved | A single workflow state calls the program complete | Orthogonal exact, build, owner, data, and layout claims |
| TH08 accepted the wrong relocated floating literal | A common comparator repeats a false-positive class everywhere | Oracle results declare coverage and dependency attestation |
| TH105 LTCG uses remote physical chunks | A common `address + size` schema cannot represent the target | Extent graphs and separated owner dimensions |
| MCP discards truncated output and has no durable job identity | A persistent runner preserves output but cannot say what claim it proves | Jobs produce truth-kernel oracle envelopes and artifact references |

Starting with MCP would make unreliable execution more reliable without first defining what constitutes a valid result. Starting with bootstrap templates would reproduce today's schema drift. Starting with a universal comparator would overfit either PE/VC7 or PC-98. The truth kernel is the dependency that prevents all three mistakes.

### 1.4 The First Executable Vertical Slice

The first implementation should be read-only and deliberately small:

```text
factory inspect <repository>
    -> detect/adopt project and product identities
    -> invoke a repository-specific read adapter
    -> normalize existing ledgers into truth-kernel claims
    -> validate identities, vocabulary, dependencies, and denominators
    -> emit one deterministic snapshot and diagnostics
```

It should initially support three adversarial examples:

1. TH04 for multi-product PC-98/MZ/OMF boundaries;
2. TH095 for VC7 function-exact versus whole-build separation;
3. TH105 for target invalidation, LTCG, and non-contiguous physical ownership.

TH08 then validates semantic and whole-image claims, while TH07 validates compatibility with the earlier monolithic ledger. This ordering tests the abstraction against the blind spots first rather than only against the cleanest successful path.

The output snapshot should contain no new truth inferred from filenames or percentages. It reports native claims faithfully, marks unmappable fields as `incomplete`, and explains conflicts. When its totals agree with every native report, the same kernel can support `factory create`.

### 1.5 What `factory create` Should Produce

After read-only parity, `factory create project.toml` can safely generate:

- the locked project/product/target/toolchain manifests;
- profile-selected ledger schemas and provider configuration;
- a whole-build skeleton from day one;
- task definitions and bounded work-packet templates;
- named CI tiers and receipt verification;
- scratch/evidence/artifact retention policy;
- a small replacement-style handoff;
- a repository-scoped MCP registration;
- documentation generated from capabilities rather than copied from another game.

The generated repository remains an instance. Regeneration may update managed files, but it must never overwrite game source, hand-authored evidence, or local policy without a three-way migration report.

### 1.6 What Should Not Be Unified First

Do not initially unify:

- PE and MZ byte/layout comparison internals;
- Ghidra and IDA databases or command syntax;
- Borland, VC7, VC7.1, and VC8 compiler flags;
- standalone COFF units and LTCG physical-owner chunks;
- game-specific source layout or subsystem names;
- exact exception mechanisms such as the currently authorized x87 cases;
- runtime launch and portable product adapters.

Unify their provider interfaces, declared capabilities, inputs, outputs, and fail-closed semantics. Reuse implementation only when fixtures prove it has the same meaning under more than one profile.

## 2. Scope and Evidence Method

This review covers these local repositories:

| Repository | Role | Commits at snapshot | Working-tree note |
|---|---|---:|---|
| `th04-reconstruction/th04` | PC-98 multi-artifact reconstruction | 79 | clean |
| `th07` | early Windows exact-reconstruction workflow | 130 | pre-existing untracked `droid.resume.txt` |
| `th08-reconstruction/th08` | mature exact, whole-image, semantic, and portable reconstruction | 685 | clean |
| `th08-reconstruction/th08-web` | browser/WASM product derived from reconstructed source | 1,005 | clean |
| `th095-reconstruction/th095` | VC7.1 exact reconstruction plus active whole-build closure | 326 | branch ahead and pre-existing untracked files |
| `th105-reconstruction/th105` | VC8 LTCG reconstruction and physical-owner analysis | 408 | clean |

`/home/pentester/coding/codex_ida/th08` is a different runtime-agent research repository. It is neither the TH08 reconstruction repository nor `th08-web`, and must be excluded from factory discovery unless selected explicitly.

The review used four evidence levels:

- **Current machine reports** for coverage and state.
- **Executable source and configuration** for what tools actually enforce.
- **Repository documents** for intended contracts and accumulated lessons.
- **Commit archaeology** for ordering, regressions, resets, and fixes that current documentation can hide.

Every recommendation below is either tied to one of those observations or marked as a proposed contract. No game-instance repository was intentionally changed during this review.

## 3. What `/tmp/vc_sth.txt` Is Asking For

The note describes a system problem, not merely a documentation problem.

### 3.1 Throughput requirements

- Bootstrap a new game repository, target attestation, compiler/toolchain, Ghidra or IDA setup, ledgers, skills, CI, and knowledge references from one stable workflow.
- Give GPT Web bounded work packets that fit its context and connection limits.
- Preserve useful results when an MCP connection or Web session disappears.
- Extract reusable knowledge after each reconstruction without requiring the next agent to reread hundreds of commits and thousands of diary lines.

### 3.2 Correctness requirements

- Discover and review authored boundaries independently from reconstructing known functions.
- Prefer natural C/C++ source. Permit assembly only through a narrow, target-evidenced exception contract, such as an otherwise inexpressible x87 sequence.
- Separate authored, compiler-generated, and library-origin bytes.
- Treat compilation, linking, object ownership, global storage, relocations, and image layout as first-class evidence.
- Make semantic reconstruction fail closed: preserve layout, distinguish observed facts from inference, and forbid invented meaning from becoming an oracle premise.
- Keep faithful reconstruction separate from x64, Linux, and WASM product work.

### 3.3 Reliability requirements

- Treat small context, connection loss, and truncated output as ordinary operating conditions.
- Require fresh verification before commits rather than trusting an agent's assertion that CI ran.
- Isolate concurrent repositories, processes, scratch directories, and dirty trees.
- Replace `.analysis/` accumulation with explicit scratch, evidence, fixture, build, and handoff lifecycles.

## 4. Repository Snapshot: Current State Is Multi-Dimensional

### 4.1 Current reconstruction reports

| Game | Current report | Important denominator caveat |
|---|---|---|
| TH04 | MAIN: 270/272 reviewed authored functions exact; 40,638/40,669 reviewed authored bytes exact | Four products contain 732 authored candidates; 460 remain unreviewed. MAIN's 99% is not whole-game completion. |
| TH07 | 223/1,023 authored functions exact; 504/504 classified library functions exact | Function-level COFF equality does not prove original TU ownership or executable layout. |
| TH08 | 1,107/1,107 authored functions source-present; 1,106/1,107 exact | The current non-exact row is `ReplayManager::PlaybackExtendedInputAndFps`; portable/product status is a separate claim. |
| TH095 | 697 authored, 1,183 excluded, 0 origin-review; 697 source-present and 696 exact | Near-complete function matching coexists with unresolved whole-program ownership/link work. |
| TH105 | 1,469 authored, 1,308 excluded, 1,242 still under review; 1,381 source-present and 1,306 exact | 489 match units cover many functions; LTCG physical owners and remote chunks invalidate a simple function-per-object model. |

The factory must never publish a single bare “percent complete.” At minimum it must expose separate dimensions for inventory review, origin classification, source presence, function exactness, owned extent exactness, whole-build closure, whole-image layout, semantic confidence, and portable runtime validation.

### 4.2 Existing artifact growth

| Repository | `.analysis/` files | Approximate size | Tracked files |
|---|---:|---:|---:|
| TH04 | 16,036 | 1.7 GiB | 0 |
| TH07 | 329 | 5.7 MiB | 0 |
| TH08 | 794 | 277 MiB | 0 |
| TH095 | 6,440 | 111 MiB | 0 |
| TH105 | 18,329 | 504 MiB | 0 |

The files are untracked, but “untracked” is not a lifecycle. These directories mix reproducible output, one-off probes, disassembly, logs, and evidence. Their scale confirms that prose asking agents to prune scratch is insufficient; retention must be represented in schemas and enforced by tooling.

### 4.3 Documentation growth

The mature repositories contain valuable knowledge, but some documents have become chronological stores:

- TH08's semantic reconstruction document is about 4,957 lines, its handoff about 2,340 lines, and its knowledge base about 609 lines.
- TH105's knowledge base is about 2,823 lines and its handoff about 1,479 lines.
- TH08's semantic document contains more than sixty completed-batch sections.

TH08 already documents the intended rule—move stable facts into ledgers or knowledge, keep the handoff current, and delete scratch—but the current repository demonstrates that policy text alone does not compact state. The factory needs structural limits, replacement semantics, archival commands, and lints.

## 5. Commit Archaeology and Lessons

### 5.1 TH04: boundary truth is platform- and artifact-specific

TH04 began by building the control plane: target ingestion, MZ/OMF inspection, Borland/TASM probes, Ghidra setup, oracle contracts, ledgers, and handoff. Exact reconstruction followed. Later boundary reviews found authored functions that the earlier seed inventory missed.

Current boundary evidence spans four products:

| Product | Authored candidates | Exact | Unreviewed | Blocked |
|---|---:|---:|---:|---:|
| OP | 94 | 0 | 94 | 0 |
| MAIN | 553 | 270 | 281 | 2 |
| MAINE | 72 | 0 | 72 | 0 |
| ZUN | 13 | 0 | 13 | 0 |

A particularly useful failure case is a five-byte Ghidra boundary for a Gengetsu foreground renderer. Full decoding and TASM evidence established a 398-byte authored extent. Target-derived assembly listings also exposed local procedures omitted by maps or Ghidra.

Factory lesson:

- target identity is gate zero;
- boundary inventory is revisited throughout the project, not completed once at bootstrap;
- per-artifact progress is mandatory;
- disassembler function starts are hypotheses;
- boundary acceptance combines container, decode, relocation, compiler, and cross-reference evidence;
- reviewed-denominator percentages must say exactly what remains outside the denominator.

TH04 also proves why the PC-98 oracle must be a profile. Its correctness model includes 16-bit segment ownership, memory model, near/far calls, DGROUP, MZ relocation entries, OMF record structure, TASM/TLINK behavior, and PC-98 hardware interfaces. Mapping these concepts directly onto PE sections and COFF objects would erase essential evidence.

### 5.2 TH07: a productive function-exact prototype, not whole-program closure

TH07's 130 commits established a fast function-matching workflow with typed diagnostics for stack slots, operand widths, register homes, global references, constants, calls, cleanup, branch topology, and relocation-aware library recovery.

Those typed facts are useful diagnostic sub-oracles: they explain why two outputs differ and route the next edit. The strict byte comparator remains the acceptance oracle. The repository's own workflow correctly warns that a focused COFF match proves function code generation, not original translation-unit ownership or final executable layout.

The current `scripts/progress.py` reports 223/1,023 authored functions exact and all 504 classified library functions exact. Its `build.py --check` validates match-unit graph structure; it is not a complete pre-commit gate for target-dependent cold verification.

Factory lesson:

- retain TH07's typed diagnostic vocabulary;
- never aggregate diagnostic similarity into acceptance;
- distinguish a match unit from a source TU, object owner, physical image owner, and semantic subsystem;
- label CI tiers explicitly so “CI passed” cannot mean only a target-independent graph check.

### 5.3 TH08: whole-image ownership, semantic passes, and a late oracle defect

The important historical sequence is:

1. exact reconstruction infrastructure and authored-function recovery;
2. library reconstruction;
3. whole-image baseline and intensive object/TU/layout repair around 2026-08-20;
4. a playable Linux port around 2026-08-24;
5. browser work and systematic semantic reconstruction beginning around 2026-08-26;
6. post-port exact-oracle reconciliation and a floating-relocation oracle repair on 2026-09-02.

Whole-image work required moving functions and storage among actual owners such as `Ascii`, `Player`, `GameManager`, and animation units. It also required reproducing COMDAT behavior, inline visibility, precompiled-header effects, object order, `/OPT:NOREF`, and `/OPT:ICF`. Exact function bytes did not prove ownership. Object ordering metrics such as drift, inversions, and runs were useful routing signals but never acceptance evidence.

The semantic workflow introduced a strong evidence vocabulary:

- `observed`: directly visible in target behavior or code;
- `corroborated`: supported by independent target evidence;
- `inferred`: plausible and explicitly bounded;
- `unknown`: preserved without invented meaning.

It also preserved aggregate ownership, layout assertions, offsets, and byte-oriented serialized storage. These should become shared contracts.

The portable branch later exposed 88 cold exact failures after owner canonicalization: most were relocation-manifest or extent mismatches, with two true code differences. That episode is evidence that the faithful baseline should be closed and frozen before a portable fork, while still allowing the portable build to act as an independent semantic/runtime oracle afterward.

The most important regression fixture is commits `7148a76b` and `a393f400`:

- Source accepted `GetPower() >= 0.0`, but the target's gameplay threshold was `128.0`.
- The comparator substituted a relocation target but did not attest the data stored at that target.
- Different floating literals could therefore appear exact when the relocation form and pointer identity matched.
- The repair attested relocation destination bytes and audited 1,548 floating relocations, finding 12 stale entries across five previously accepted units.

Factory lesson: relocation equality has at least three independent claims—relocation form, destination identity, and destination contents/semantic literal encoding. Any generic oracle that normalizes relocations without attesting all applicable layers is unsound.

TH08's `scripts/ci.py` is primarily target-independent. It checks Python compilation, literal tests, semantic protocols, ledgers, configuration, documentation, routing, and whitespace. Full cold exact verification remains a separate command required by repository instructions. This is another reason to replace ambiguous CI language with named gate receipts.

### 5.4 TH095: exact functions do not make a linkable program

TH095 refined origin and boundary ledgers by separating candidate inventory, origin classification, source presence, and exact matches.

Its boundary audits found two important blind spots:

- a direct-edge scan missed 49 ten-byte VC7 exception-handler entries; stronger relocation and cleanup audits classified them as compiler-generated;
- switch tables after a `RET` inflated apparent authored extents, requiring separate `authored_size` and `compare_size` concepts.

A later raw scan traversed direct edges, executable address words, uncovered gaps, and prologue-like candidates rather than trusting disassembler function starts. The resulting origin inventory closed at 697 authored and 1,183 excluded candidates with zero remaining review rows.

Commit `cd2072b` added a fail-closed whole-program build audit. At a documented checkpoint all 88 source TUs compiled and 696 of 697 authored functions were exact, yet the link still reported 239 unique unresolved symbols across 258 diagnostics, including 130 data and 109 callable symbols. This is decisive evidence that function matching alone does not reconstruct program ownership or storage.

The subsequent owner repairs use lifecycle-backed shared storage and canonical ABI views. Target-facing aliases are tolerated only under a narrow diff-build boundary; duplicate globals or force-resolved symbols are not accepted as faithful closure.

Factory lesson:

- create the whole-build plan early;
- compile every production TU under exactly one canonical profile;
- fail on object-name collisions and uncovered sources;
- retain `/OPT:NOREF` or the target-backed equivalent while diagnosing dependencies;
- group unresolveds by callable/data/import/target-address/owner class;
- treat successful linking as a milestone, not whole-image equality.

### 5.5 TH105: target identity and LTCG physical ownership

Commit `c10b80a` reset the reconstruction after work had targeted TH105 1.06 instead of the required 1.06a. It removed stale machinery, repinned the official updater payload, regenerated inventory, and reset source/exact/library state. The reset deleted substantial previous work.

Factory lesson: target identity is not a README field. Every evidence record, match, build plan, artifact, and gate receipt must be cryptographically bound to the target identity. A target change invalidates dependent claims automatically.

TH105 adds a second major lesson. VC8 LTCG breaks the convenient equivalence among semantic function, source TU, standalone COFF output, and physical image owner. Its ownership manifests describe remote chunks and internal padding separately. A giant Sakuya or Reimu dispatcher can own code far from its primary range; `start + size` is not an adequate physical-extent model.

Its giant-owner diagnostics preserve opcode, register, branch-width, and owner-offset information. They can distinguish same-sized arms with different `AL`/`EAX` predicates or signedness, but they cannot grant partial exact credit. Generated COMDAT origin scans likewise route work but become evidence only after a pinned, reproducible, unique manifest replay.

Factory lesson:

- physical ownership is an extent graph, not a contiguous interval;
- semantic owner, source owner, emitted object, and final-image physical owner are separate identifiers;
- compiler profiles must declare whether standalone object matching is meaningful;
- diagnostic correspondence and exact acceptance remain separate even for giant functions.

### 5.6 TH08-web: the portable product is a consumer

`th08-web` compiles reconstructed C++ to WebAssembly and adds browser adapters. It is not the “GPT Web” reconstruction environment. Its provenance boundary excludes the original executable and game data from the deployed product; users provide local data files, checked against an allowlist.

Its milestone model—WASM compilation, full link, renderer, persistence, browser support, and deployment—keeps failure domains small. This belongs to a portable-product profile consuming a frozen faithful release, not to the exact-reconstruction acceptance oracle.

## 6. Correct Unified Model

### 6.1 Do not use one linear status column

Each reconstructed entity needs a vector of independent claims:

```text
target identity
boundary review
origin classification
source presence
compile profile
function-codegen exactness
owned-extent exactness
relocation/data exactness
TU/object ownership
whole-build link closure
whole-image layout
semantic evidence maturity
portable build/runtime status
```

Some claims apply to functions, some to extents, source files, objects, sections, artifacts, or the entire product. The schema must reject category errors such as attaching whole-image exactness to a function row.

### 6.2 Use a staged workflow with continuous feedback loops

The recommended control flow is:

```text
attest target and toolchain
          │
          v
seed inventory and origin hypotheses <──────────────┐
          │                                          │
          v                                          │
boundary/extent review ──────── new evidence ────────┤
          │                                          │
          v                                          │
natural-source exact units ───── codegen feedback ───┤
          │                                          │
          ├──── continuous compile/link/owner loop ──┘
          │
          v
faithful whole-program and whole-image closure
          │
          v
bounded semantic passes + exact regression
          │
          v
frozen faithful release
          │
          └──── portable product fork -> platform/runtime validation
```

This answers the workflow question in the source note:

- **Yes, compile/link/layout feedback belongs earlier.** Generate the canonical build graph during bootstrap, compile the first recovered TU immediately, and run partial/full link diagnostics continuously.
- **No, link success does not replace function exactness.** Each oracle answers a different claim.
- **Semantic evidence starts early; semantic rewriting does not.** Names, types, offsets, and confidence can be recorded during exact work. Broad refactoring waits for the faithful baseline and must preserve it.
- **Portable work begins from a frozen faithful handoff.** Portable failures may reveal semantic defects, but fixes first return to and re-close the faithful branch.

### 6.3 Shared core contracts

The platform-independent factory should define these contracts:

| Contract | Purpose |
|---|---|
| `TargetIdentity` | Product, version, hashes, container facts, provenance, canonicality |
| `ToolchainIdentity` | Compiler/linker/assembler hashes, flags, environment digest |
| `BoundaryClaim` | Candidate range or extent graph, discovery method, review state, evidence |
| `OriginClaim` | Authored/compiler/library/generated/unknown with scoped proof |
| `SourceUnit` | Source presence, compile profile, match units, canonical production owner |
| `ExactClaim` | Comparator, normalized fields, raw fields, target, toolchain, result artifacts |
| `OwnershipClaim` | Semantic/source/object/physical owner relationships |
| `SemanticClaim` | Evidence class, layout constraints, scope, contradictions |
| `ArtifactRef` | Content hash, media type, producer, retention class, dependencies |
| `GateReceipt` | Tree hash, target/toolchain/factory versions, gates, outputs, expiry |
| `Handoff` | Active objective, baseline receipt, failure IDs, next bounded action |

### 6.4 Platform and compiler profiles

Profiles implement adapters behind shared interfaces.

`pc98-mz-omf` must own:

- MZ header, load module, overlays if present, and relocation table;
- segment:offset address normalization and segment ownership;
- OMF records, public/local symbols, fixups, and library extraction;
- near/far calling and data models, DGROUP, Borland/TASM/TLINK quirks;
- PC-98-specific static and eventual runtime adapters;
- per-product orchestration for OP, MAIN, MAINE, and ZUN-style artifacts.

`windows-pe-coff` must own:

- PE headers, sections, imports, resources, base relocations, and debug policy;
- COFF symbols, relocations, COMDATs, object order, and image layout;
- MSVC calling, exception, RTTI, library, and linker behavior;
- whole-image comparison and accepted normalization rules.

Compiler subprofiles then refine ownership:

- `msvc7-non-ltcg`: focused COFF codegen is useful, but TU and final-image ownership remain separate claims;
- `msvc8-ltcg`: physical chunks, folding, cross-TU optimization, and remote extents are first-class; standalone object identity may be unavailable or misleading.

## 7. Oracle Architecture

### 7.1 Diagnostic oracles versus acceptance gates

Every oracle declares one of two roles:

- **Diagnostic**: produces structured differences, similarity, hypotheses, routing, or likely causes. It can never advance an exact state by itself.
- **Acceptance**: proves a precisely named claim under pinned inputs and fails closed when coverage or attestation is incomplete.

Examples:

| Oracle | Role | Claim |
|---|---|---|
| stack/register/control-flow diff | diagnostic | likely source-shape mismatch |
| object drift/inversion report | diagnostic | likely owner/order mismatch |
| giant-owner correspondence | diagnostic | likely physical arm/chunk correspondence |
| raw function-byte comparator | acceptance | code bytes equal over an attested extent |
| relocation-aware exact comparator | acceptance | code, relocation form, destination, and required destination data agree |
| cold inventory replay | acceptance | every claimed unit is reproducible from a clean state |
| whole-build audit | acceptance | every canonical source has one profile and unresolved policy is satisfied |
| whole-image comparator | acceptance | declared PE or MZ image claims match under explicit normalizations |
| portable smoke/runtime suite | acceptance | a separate platform behavior contract passes; it does not prove binary fidelity |

### 7.2 Required oracle result envelope

Every invocation should emit a machine-readable record containing:

```yaml
schema_version: 1
oracle_id: windows.vc7.function-exact
oracle_version: <content hash or release>
role: acceptance
claim_type: function_codegen_exact
subject_id: <stable entity id>
target_identity: <TargetIdentity id>
toolchain_identity: <ToolchainIdentity id>
source_tree: <git tree hash>
inputs: [<ArtifactRef>]
coverage:
  expected: <declared domain>
  observed: <measured domain>
result: pass | fail | incomplete | error
normalizations: [<named, versioned rule>]
diagnostics: [<ArtifactRef>]
started_at: <timestamp>
duration_ms: <integer>
```

`incomplete` is not `pass`. Missing bytes, unknown extents, absent relocation destinations, stale manifests, partial output, and unattested targets must fail closed.

### 7.3 CI tiers and commit receipts

The factory should use named tiers rather than one `ci.py` concept:

| Tier | Typical contents | Intended frequency |
|---|---|---|
| `lint` | schemas, graph consistency, syntax, docs, generated-file freshness | every edit |
| `focused` | affected match units and relevant oracle fixtures | every candidate commit |
| `affected` | reverse dependencies, owner group, relocation/data audits | every candidate commit when applicable |
| `cold-exact` | clean replay of all accepted exact claims | milestone and required faithful commits |
| `whole-build` | all canonical production TUs, link/owner/unresolved policy | continuously and at milestones |
| `whole-image` | complete layout/image oracle | faithful release gate |
| `portable-runtime` | platform build and runtime suite | portable plane only; normally Codex-operated |

A commit-capable Web workflow should receive a fresh `GateReceipt`, not raw command prose. The receipt binds the source tree, target, toolchain, factory/oracle versions, tier set, and result artifacts. The commit operation rechecks that the tree and dependencies have not changed. A stale or partial receipt cannot authorize a commit.

## 8. Artifact and Knowledge Architecture

### 8.1 Artifact lifecycle

| Class | Default retention | Promotion rule |
|---|---|---|
| `scratch` | session TTL | deleted unless referenced by an active handoff |
| `job-output` | bounded TTL | promoted when cited by a claim or failure |
| `evidence` | while dependent claim is live | content-addressed and immutable |
| `regression-fixture` | permanent/versioned | minimized reproduction of a framework defect |
| `build-output` | reproducible cache policy | never treated as durable evidence without a hash/reference |
| `handoff` | one live checkpoint plus small archive | replaced, not endlessly appended |
| `knowledge` | maintained | reviewed entry with provenance and scope |

The store should be content-addressed. A metadata index records producer, job, target, source tree, media type, size, retention class, references, and expiry. Garbage collection deletes only unreferenced expired objects and emits an audit report.

The TH08 floating-relocation defect should be the first cross-project regression fixture. Additional fixtures should cover the TH04 false boundary, TH095 exception handlers and post-`RET` switch data, TH105 remote owner chunks, and the TH105 target-version reset.

### 8.2 Knowledge ontology

Long-term knowledge entries should be typed:

- `invariant`: verified across declared profiles or projects;
- `recipe`: executable procedure with prerequisites and outputs;
- `pitfall`: symptom, cause, detector, repair, and regression fixture;
- `scoped_fact`: game, version, compiler, or platform fact;
- `hypothesis`: unverified and forbidden as an acceptance premise;
- `decision`: selected architecture with alternatives and consequences;
- `evidence_index`: stable pointers to claims and artifacts.

Required metadata includes stable ID, scope, confidence, provenance, validators, `supersedes`, `contradicts`, and review date. A fresh agent may harvest candidate lessons from commit history after a project, but it must not auto-promote them to invariants. Promotion requires stated scope and at least one validating fixture or independent project observation.

### 8.3 Handoff is state, not history

A live handoff should contain only:

- repository, branch, and clean/dirty identity;
- active objective and prohibited scope;
- target/toolchain/factory lock IDs;
- last fresh gate receipt;
- exact current blockers by stable ID;
- artifacts needed to resume;
- next bounded command or decision.

Completed narratives belong in commits, structured claims, or a compact archive. The live handoff should have a size limit and replacement semantics.

## 9. MCP for GPT Web: Current Findings

The reviewed copies are vendored under game repositories; no separate top-level MCP repository was found in the searched local tree.

### 9.1 What the newer Ghidra MCP does well

- Bearer-token support, allowed-host configuration, health reporting, and structured request logs.
- Strict bounded schemas for Ghidra operations and paginated function listing.
- Per-call target/project attestation through the configured workflow.
- Serialized Ghidra execution, which avoids concurrent database mutation or contention.
- A Ghidra scratch directory checked both lexically and after `realpath` to remain inside the workspace.
- Read-only MCP annotations for Ghidra, bounded address counts, no patch operation, and explicit provisional-evidence language.
- Headless, niced child processes with process-group timeout handling and SIGTERM-to-SIGKILL escalation.

These are reusable adapter-level protections.

### 9.2 What remains unsafe or non-resumable

The general `run_command` tool is explicitly unrestricted. Its `resolveCommandCwd` accepts absolute paths, `~`, `~/...`, and workspace-relative paths resolved through `path.resolve`. It validates existence but does **not** enforce containment in `WORKSPACE_ROOT`. `..` or an absolute path can therefore cross repository boundaries. An annotation saying “destructive” informs a client but does not enforce isolation.

Both shell and Ghidra calls are synchronous request/response operations:

- the request waits for process completion;
- stdout and stderr are retained only up to a character cap;
- there is no durable job ID, idempotency key, lease, progress cursor, reconnect, or result reclamation;
- the Ghidra path writes to a temporary call directory, reads a bounded prefix, and then deletes the directory in `finally`;
- if output is truncated, the omitted exact output is destroyed;
- the server exposes tools only; it does not currently expose a stable resource/prompt/knowledge surface.

The HTTP handler constructs MCP server instances through a factory, while durable job/session state is absent. Consequently, client connection continuity is not a meaningful recovery boundary.

### 9.3 Required MCP v1 control surface

The normal Web-facing surface should be repository-scoped and task-oriented:

```text
workspace.describe
workspace.status
knowledge.query
source.search / source.read
job.start
job.status
job.cancel
job.output_page
artifact.read_page
artifact.promote
oracle.run
gate.run
gate.get_receipt
handoff.read / handoff.replace
git.commit_with_receipt
```

Each workspace registration binds a stable repository ID to a canonical real path, allowed capabilities, target/profile lock, dirty-tree policy, and artifact namespace. User-supplied paths are resolved beneath that root and checked again after `realpath`. Cross-repository access requires a separately registered read-only dependency, never an arbitrary `cwd`.

Jobs are persisted independently of the HTTP connection, ideally in a small durable database plus content-addressed output storage. A start call accepts an idempotency key and returns immediately. Status and output pagination survive reconnects and service restarts. Output truncation means “read another page,” not “data was discarded.” Cancellation targets the recorded process group and records the terminal state.

Unrestricted Bash may remain an operator-only emergency capability. GPT Web should normally select declared tasks whose commands, inputs, outputs, timeouts, mutation scope, and required follow-up gates are defined by the active profile.

### 9.4 Prompt strategy

The large prompt should shrink. Stable rules belong in server instructions, versioned skills/resources, repository manifests, and task definitions. A Web invocation should need only:

```yaml
workspace: th09
objective: <bounded outcome>
lane: exact | boundary | owner | semantic
budget: <time or work-packet bound>
baseline_receipt: <optional receipt id>
```

The server returns the relevant profile, prohibited actions, current handoff, and exact command surface. This makes rule changes versionable and prevents every session from spending context on an increasingly long prompt.

## 10. Proposed Factory Repository Shape

```text
contracts/
  target-identity.md
  claims.md
  oracle-result.md
  gate-receipt.md
  handoff.md
schemas/
  target-identity.schema.json
  claim.schema.json
  oracle-result.schema.json
  artifact.schema.json
  gate-receipt.schema.json
profiles/
  core/
  platform/pc98-mz-omf/
  platform/windows-pe-coff/
  compiler/borland16/
  compiler/msvc7/
  compiler/msvc8-ltcg/
oracles/
  protocol/
  adapters/
  fixtures/
knowledge/
  invariants/
  recipes/
  pitfalls/
  scoped-facts/
templates/
  instance/
  docs/
  work-packets/
mcp/
  server/
  tasks/
cli/
  bootstrap/
  verify/
  harvest/
docs/
  factory-analysis.md
  architecture.md
  migration.md
```

An instance repository should carry a small `.reconstruction/` control directory:

```text
.reconstruction/
  project.toml
  factory.lock
  targets/
  state/
  handoff.yaml
  artifacts.sqlite        # ignored local index; exportable manifests are tracked
```

Game source, address mappings, target-specific evidence, large artifacts, and build products stay in the instance. The `factory.lock` pins schemas, profiles, tasks, and oracle versions so a later factory update cannot silently reinterpret old exact claims.

## 11. Bootstrap Contract

A factory bootstrap should be transactional:

1. resolve and attest the exact target artifact before importing source claims;
2. detect or require the platform and compiler profile;
3. pin toolchain binaries and record hashes/flags/environment;
4. generate ledgers and schemas, not prefilled truth claims;
5. create the whole-build graph skeleton immediately;
6. provision Ghidra or IDA through a profile adapter and verify database/target identity;
7. initialize artifact storage, retention policy, and a live handoff;
8. install named CI tiers and run smoke fixtures;
9. register a repository-scoped MCP workspace;
10. emit a bootstrap receipt that can be reproduced cold.

Bootstrap must stop before expensive reconstruction if target identity, toolchain identity, or profile selection is ambiguous. TH105 demonstrates the cost of treating those as recoverable later.

## 12. Migration Strategy for Existing Games

Do not refactor every repository into the new model at once.

1. Build read-only importers for current ledgers and reports.
2. Normalize their outputs into the proposed claim vector without changing source repositories.
3. Extract the high-value regression fixtures listed above.
4. Wrap existing oracle commands behind named task definitions and result envelopes.
5. Compare factory reports with native repository reports until they agree.
6. Adopt write-capable receipts and artifact retention only after read-only parity.

TH04 and TH105 should remain deliberate counterexamples during design. A schema that only fits TH08/TH095's PE/VC7 workflow is not the shared core.

## 13. TH09 Validation Plan

TH09 should be the first clean-room consumer of factory v0 rather than another source of ad hoc factory features.

### 13.1 Before reconstruction

- freeze a factory version and its schemas;
- bootstrap TH09 without copying a prior game's stale ledgers or conclusions;
- require target and compiler-profile detection to produce an explicit result rather than assuming a known MSVC version;
- inject the existing regression fixtures into factory self-tests;
- verify that disconnecting and reconnecting to a long-running job preserves status and complete paginated output.

### 13.2 During reconstruction

- use GPT Web only for bounded pre-port work packets;
- run the whole-build skeleton from the first recovered production TUs;
- record boundary discoveries, origin claims, and exact claims on separate axes;
- require fresh focused/affected receipts for routine commits and periodic cold/whole-build receipts;
- harvest candidate knowledge after milestones, but review promotion separately.

### 13.3 Acceptance signals

- no progress number hides unreviewed inventory;
- no accepted exact claim depends on an unattested target, stale manifest, missing extent, or discarded output;
- a Web disconnect loses no completed job result or promoted evidence;
- cross-repository writes are impossible through normal Web capabilities;
- the live handoff remains bounded and sufficient for a fresh session;
- whole-build failures are visible early rather than after near-complete function matching;
- the faithful release is frozen before portable work begins.

## 14. Recommended Implementation Order

### Phase 0: preserve evidence before abstraction

- Copy only minimized regression inputs and expected results from TH04, TH08, TH095, and TH105.
- Record repository/commit provenance for every fixture.
- Write architecture decision records for the shared-core/profile split and multi-axis claims.

### Phase 1: contracts and read-only reporting

- Implement schemas for target identity, claims, artifacts, oracle results, receipts, and handoff.
- Implement importers for existing repository ledgers.
- Produce one unified read-only status report that preserves native denominators.

### Phase 2: oracle runner and artifact store (partially implemented)

- Wrap existing commands without rewriting their internal comparators first.
- Add content-addressed output, explicit `incomplete`, pagination, retention, and fixture replay.
- Implement named CI tiers and locally verifiable receipts.

### Phase 3: resumable MCP

- Add workspace registration, persistent jobs, idempotency, output cursors, cancellation, and artifact promotion.
- Replace normal unrestricted shell access with declared task capabilities.
- Add receipt-bound commit support only after isolation and dirty-tree tests pass.

### Phase 4: bootstrap and TH09 pilot

- Generate a new instance from locked profiles.
- Exercise reconnection and failed-job recovery deliberately.
- Measure where the factory contract is too generic or where game facts leaked into shared code.

### Phase 5: faithful-to-port handoff

- Define the frozen faithful release manifest.
- Generate a separate portable-product workspace/profile.
- Keep portable runtime evidence linked to, but unable to rewrite, faithful exact claims without reopening their gates.

## 15. Decisions Supported by Current Evidence

1. **Use a control-plane repository with game-local instances.** Large targets, source, addresses, and analysis stay local; contracts and fixtures are shared.
2. **Split PC-98 and Windows at the platform-oracle layer.** Share schemas and lifecycle, not binary-format assumptions.
3. **Split Windows compiler behavior further.** VC7 focused objects and VC8 LTCG physical ownership cannot use the same ownership model.
4. **Represent progress as claim vectors.** TH04, TH095, and TH105 each disprove a single percentage.
5. **Start whole-build feedback early.** TH08 and TH095 show that exact functions leave major owner, ABI, data, and layout work.
6. **Freeze faithful output before ports.** TH08's post-port reconciliation shows the cost of crossing the boundary early.
7. **Make oracle defects permanent fixtures.** The floating-relocation bug must never be rediscovered game by game.
8. **Replace diary growth with typed, compactable state.** Existing prose policies have not constrained handoff and `.analysis/` growth.
9. **Make MCP jobs durable and repository-scoped.** The current synchronous unrestricted shell cannot meet reconnect, artifact, or isolation requirements.
10. **Authorize commits with fresh receipts.** Agent intent and generic “CI passed” statements are too ambiguous.

## 16. Open Questions Before Coding Beyond v0

- Which target and toolchain files may be referenced, hashed, or redistributed legally? The artifact store must support local-only objects.
- Should factory locks be consumed as release archives, a package, or a Git dependency? The choice must support offline reproducibility and stable content hashes.
- Which existing exact comparators can emit structured envelopes without changing their accepted semantics?
- What is the smallest durable job backend that safely survives MCP server restart and cleans orphaned process groups?
- How should a multi-artifact game express shared source while keeping per-product target, boundary, and progress claims honest?
- Which portable runtime checks can be deterministic enough to become gates, and which remain operator evidence?
- What explicit approval boundary should exist for knowledge promotion from `scoped_fact` to `invariant`?

These questions do not block Phase 0 or the read-only portion of Phase 1.

## 17. Implemented Foundation Checkpoint (2026-09-09)

The first four requested layers are now executable rather than recommendations:

- the versioned truth kernel and unified vocabulary;
- compatible PC-98 MZ/OMF, Windows PE/COFF, Borland 16-bit, VC7, VC7.1, and
  VC8 LTCG provider interfaces;
- dedicated read-only adapters for TH04, TH08, and the TH095/TH105 ledger
  family;
- manifest-hashed historical regressions plus a scope-aware cross-game
  knowledge catalog.

TH08 required a separate adapter. Its headerless mapping, authored/library
split, and source-name cardinality are materially different from the later
Windows ledgers. Live parity exposed that 1,106 implemented names cover 1,107
authored target addresses because `th08::Float3::Float3` names two constructor
identities. That fact is now preserved as a fixture instead of hidden by a
compatibility shim.

The initial knowledge kernel contains eleven fixtures and ten verified rules
covering target binding, boundary coverage, exact-evidence scope, relocation
destination contents, source/function cardinality, whole-build closure,
toolchain surfaces, concurrent workspace isolation, LTCG comparison context,
and noncontiguous extent exactness. Two questions remain explicitly `unknown`:
a unified cross-platform runtime-equivalence receipt and a general reproduction
recipe for every VC8 linked-LTCG owner/layout decision.

The checkpoint passes 31 local unit tests. Fixture JSON and the knowledge
catalog also validate against their published JSON Schemas. Read-only native
parity compares 36 TH04, 11 TH08, 10 TH095, and 12 TH105 metrics exactly, with
Git working-tree state checked before and after each native report. A separate
provenance command resolves every fixture's full commit, confirms the actual
GitHub origin, and verifies all 29 cited evidence paths as committed blobs.

Imported exact rows still remain claims with zero factory
`OracleResult(pass)` objects. Acceptance is a separate explicit operation: a
factory-controlled driver must cold-replay one claim and issue a
content-addressed receipt. The initial runner now provides a local artifact
store, repository-wide lock, complete stage output, strict target/source/
toolchain/environment bindings, and live freshness verification.

Four independent live replays exercise the first driver family: TH04's
isolated Borland double build, TH08's clean VC7 output graph, TH095's forced
VC7.1 compilation, and TH105's forced standalone VC8 probe. All four selected
claims passed with complete extent coverage and fresh receipt verification.
TH105 is intentionally named and bounded as standalone function codegen; it
does not imply LTCG owner or image closure. Exact receipt IDs, repository
commits, dirty-tree caveats, and reproduction commands are recorded in
[`replay-validation.md`](replay-validation.md).

The next acceptance layer is also executable. A content-addressed registry now
classifies every stored candidate as `invalid`, `rejected`, or `accepted`
through an explicit, hash-bound live policy. Accepted snapshot materialization
drops any imported oracle results and adds only receipt-backed results after
claim, subject, artifact, and freshness revalidation. Receipt-backed knowledge
queries use the same boundary and remain separate from reviewed cross-game
rules backed by historical fixtures.

The final acceptance checkpoint passes 63 unit tests. A fresh four-receipt
store admitted one bounded exact result for each of TH04, TH08, TH095, and
TH105 with zero rejected or invalid candidates; the policy, registry, all
receipts, and all materialized snapshots also passed their JSON Schemas.
Re-evaluating older receipts after a runner change admitted none, and mapping
the isolated TH095 receipt to a different live worktree rejected it as stale.
Exact IDs and limitations are recorded in
[`replay-validation.md`](replay-validation.md).

Durable asynchronous jobs, pagination, retention enforcement, signatures,
named CI tiers, runtime equivalence, and write adapters remain future layers.

## Appendix A: Evidence Anchors

This index is intentionally small. It identifies the sources that support the architectural conclusions without turning this document into a copy of every repository's history.

### A.1 Requirements

- `/tmp/vc_sth.txt`: original factory, workflow, oracle, MCP, artifact, knowledge, and TH09 validation requirements.

### A.2 TH04

Repository root: `/home/pentester/coding/codex_ida/th04-reconstruction/th04`

- `docs/ARCHITECTURE.md`: shared control-plane state and PC-98-specific architecture.
- `docs/ORACLES.md`: layered target, format, layout, compiler, runtime, and metamorphic oracle model.
- `docs/BOUNDARY_REVIEW.md`: authored-boundary methodology and all-artifact review.
- `docs/RE_WORKFLOW.md`: stage and promotion rules.
- `scripts/status.py`: current per-artifact progress and denominator warnings.
- Commit `f402cb3`: initial reconstruction control plane.
- Commit `a34fff9`: private target ingestion and strict binary oracles.
- Commit `c983986`: attested headless Ghidra MZ workflow.
- Commit `7b2e66b`: fail-closed exact promotion and PC-98 oracle hardening.
- Commit `6d339ac`: all-artifact boundary review.

### A.3 TH07

Repository root: `/home/pentester/coding/codex_ida/th07`

- `docs/RE_WORKFLOW.md`: function-unit workflow and limits of focused object evidence.
- `docs/WORKFLOW_EVOLUTION.md`: evolution of the matching approach.
- `docs/PROGRESS.md`: current exact and library coverage.
- `scripts/build.py`: match-unit compilation/comparison and graph checks.
- Commit `3aeace9`: compiler-aware typed reconstruction helper.
- Commit `9cdf4ea`: relocation-aware VC7 library recovery.
- Commit `b9dba32`: typed branch-target diagnostics.
- Commit `41ab7cf`: source-only matching enforcement.

### A.4 TH08

Repository root: `/home/pentester/coding/codex_ida/th08-reconstruction/th08`

- `docs/KNOWLEDGE_BASE.md`: whole-image ownership and reconstruction lessons.
- `docs/SEMANTIC_RECONSTRUCTION.md`: semantic evidence classes and bounded pass history; lines around the “Post-port exact-oracle reconciliation” section document the 88-unit failure set.
- `docs/RE_HANDOFF.md`: current and historical reconstruction state.
- `scripts/analysis/report-reconstruction-status.py`: current source/exact report.
- `scripts/analysis/verify-exact-units.py`: cold exact replay.
- `scripts/ci.py`: target-independent repository checks.
- Commit `c0bbb0d3`: reproducible PE-diff baseline.
- Commit `4233bd1c`: normal link and resource contract.
- Commit `f526cdad`: whole-image rebuild diagnostics.
- Commits `7148a76b` and `a393f400`: auto-collection threshold fix and full floating-relocation attestation.

### A.5 TH095

Repository root: `/home/pentester/coding/codex_ida/th095-reconstruction/th095`

- `docs/BOUNDARY_AUDIT.md`: direct-edge, relocation, exception-handler, cleanup, and extent audits.
- `docs/WHOLE_BUILD_TODO.md`: current whole-build closure state and unresolved taxonomy.
- `docs/ORACLES.md`: target and exactness contract.
- `scripts/report-reconstruction-status.py`: current inventory and exact report.
- `scripts/build-whole.py`: canonical source-plan compilation and fail-closed link reporting.
- Commit `c2197dc`: runtime origin and boundary closure.
- Commit `cd2072b`: fail-closed whole-program build audit.
- Commits `6585748` and `a3412fb`: canonical shared ownership and ABI repairs.
- Commit `b864c31`: remaining whole-build closure report.

### A.6 TH105

Repository root: `/home/pentester/coding/codex_ida/th105-reconstruction/th105`

- `docs/ARCHITECTURE.md`: v1.06a target, VC8 LTCG model, and inventory architecture.
- `docs/RE_WORKFLOW.md`: target invalidation, claim states, and exact workflow.
- `docs/KNOWLEDGE_BASE.md`: LTCG, COMDAT, boundary, and owner lessons.
- `config/function-byte-ownership.toml`: non-contiguous physical extent ownership.
- `scripts/report-reconstruction-status.py`: current inventory and exact report.
- Commit `c10b80a`: target-version reset to v1.06a.
- Commit `2d74511`: common-root ownership and LTCG evidence.
- Commit `8d83c8a`: physical-owner recovery.
- Commit `0b24749`: giant-action LTCG layout blocker.

### A.7 TH08-web

Repository root: `/home/pentester/coding/codex_ida/th08-reconstruction/th08-web`

- `docs/WEB_ARCHITECTURE.md`: C++/WASM/browser adapter architecture.
- `scripts/check-web-provenance.py`: deployment provenance boundary.
- Commit `78b3157`: authored C++ WebAssembly prototype.
- Commit `bb4d83f`: playable WebAssembly port.

### A.8 MCP

Reviewed implementation root: `/home/pentester/coding/codex_ida/th04-reconstruction/th04/.tools/mcp_for_gptweb-ghidra`

- `src/command.ts`: shell process execution, output bounds, timeout handling, and unrestricted cwd resolution.
- `src/server.ts`: tool registration, HTTP/auth/logging, and per-handler server factory.
- `src/ghidra.ts`: serialized attested Ghidra calls, bounded result read, workspace-contained scratch, and unconditional temporary-output deletion.
- `.tools/mcp_for_gptweb*/..._WORKFLOW.md` in TH04, TH08, TH095, and TH105: current game-local prompt/workflow packaging.

### A.9 Review limitations

- Coverage values are a snapshot and will move as active repositories receive commits.
- Imported upstream history makes raw commit counts a scale indicator, not a direct measure of reconstruction labor.
- This review did not launch games or perform new dynamic behavioral tests.
- It inspected all commit subjects in the principal reconstruction ranges and selected high-impact diffs/documents, not every line of every commit.
- Foundation contracts exercised by schemas, fixtures, and live parity are
  implemented. Later runtime, job, artifact, and write-path proposals remain
  design recommendations.
