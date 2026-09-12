# GPT-web TH10 exact-reconstruction prompt

Use this after `th10` and `th10-ghidra` are visible through the public Factory MCP
and a public native-provider smoke test passes. The prompt does not assume that
ChatGPT injected any plugin skill.

```text
Work autonomously on the TH10 exact source-reconstruction phase through the
shared Touhou Reconstruction Factory. Do not assume any skill body was loaded.

Communicate with me in Chinese. Write code, identifiers, documentation, ledger
content, and Git commit messages in English.

Select exactly:
- repository: th10
- analysis provider: th10-ghidra
- target: target:th10-main
- private game file: /home/pentester/coding/codex_ida/th10-reconstruction/th10/resources/th10.exe
- phase: exact reconstruction, with early faithful Windows i386 build feedback

The private game file above is an operator-supplied, ignored WSL-local input.
Never commit, replace, modify, or relocate it. Do not search `/mnt`, request a
Windows game-directory mount, or set `TH10_TARGET_PATH` during normal Factory
work; the repository tools already default to this path.

Read these instructions before editing, using factory_repository_run_shell:
- /home/pentester/coding/codex_ida/th10-reconstruction/th10/AGENTS.md
- /home/pentester/coding/codex_ida/th10-reconstruction/th10/docs/RE_HANDOFF.md
- /home/pentester/coding/codex_ida/th10-reconstruction/th10/docs/RE_WORKFLOW.md
- /home/pentester/coding/codex_ida/th10-reconstruction/th10/docs/ORACLES.md
- /home/pentester/coding/codex_ida/touhou-reconstruction-factory/contracts/gpt-web-reconstruction-session-v5.json
- /home/pentester/coding/codex_ida/touhou-reconstruction-factory/contracts/worktree-recovery-and-analysis-artifacts-v1.json
- /home/pentester/coding/codex_ida/touhou-reconstruction-factory/docs/ontology.md
- /home/pentester/coding/codex_ida/touhou-reconstruction-factory/docs/verification-planes.md
- /home/pentester/coding/codex_ida/touhou-reconstruction-factory/docs/agent-autonomy.md
- /home/pentester/coding/codex_ida/touhou-reconstruction-factory/docs/new-game-bootstrap.md
- /home/pentester/coding/codex_ida/touhou-reconstruction-factory/docs/worktree-recovery-and-analysis-artifacts.md

The TH10 repository runner also mounts these adjacent-game repositories
read-only as hypothesis sources:
- /home/pentester/coding/codex_ida/th08-reconstruction/th08
- /home/pentester/coding/codex_ida/th09-reconstruction/th09
- /home/pentester/coding/codex_ida/th095-reconstruction/th095

If a Factory path is not mounted, report that once and continue under the
complete rules below. Missing skill injection or one missing guidance path is
not itself a reason to stop.

Ground rules:
1. Accuracy dominates completeness. Unknown is valid. Never guess authorship,
   function extent, ABI, type, object owner, toolchain flag, equality, or
   completion.
2. Exercise broad engineering autonomy. Compose repository Bash, Python, Git,
   the shared VC7.1/Wine toolchain when available, and discovered atomic Ghidra
   operations. The Factory improves feedback and identity binding; it is not a
   substitute for judgment.
3. Attempt, commit, build, analysis, exactness, whole-product closure, runtime
   validation, and Truth Kernel acceptance are different states. Report them
   separately.
4. Use natural maintainable C/C++. Do not embed target bytes, fake returns, add
   inert padding, patch the target, or use oracle-specific tricks. A genuinely
   irreducible assembly exception requires explicit target evidence and the
   smallest possible scope.
5. Work in the real registered repository and create coherent local
   `gpt-web:` commits. Never push.
6. Do not optimize for function count or easy exact wins. Function size,
   relocation count, control-flow complexity, or an earlier mismatch is not a
   reason to leave structurally important target code until the end.

Campaign pressure target: drive both reviewed authored-function exactness and
reviewed authored-byte exactness toward at least 99.5%, while continuously
challenging and expanding the authored boundary denominator. This is a moving
work objective, not an automatic stop condition and not a whole-executable or
whole-game exactness claim. Even if the current ledger crosses it, GPT-web does
not declare the phase complete; the operator will decide after later audit.

Mandatory recovery gate:
1. Call factory_describe, factory_list_repositories, and
   factory_get_repository_status(th10).
2. Regardless of whether a disconnect is known, inspect branch, HEAD, recent
   commits, porcelain-v2 status, staged and unstaged diffs, all relevant
   untracked files, ignored analysis/build state, and the handoff.
3. Classify each dirty path as recoverable interrupted work, unrelated
   pre-existing work, reproducible generated output, or unknown. Finish and
   checkpoint recoverable work first. Preserve and exclude unrelated or unknown
   work. Never reset, overwrite, delete, or stage it merely to obtain a clean
   tree.
4. Through `factory_repository_run_shell`, run the target, ledger, status, and
   public-CI preflights named in AGENTS.md. Perform the mandatory Ghidra
   preflight through `factory_list_analysis_operations(th10-ghidra)` followed
   by `factory_analysis_call(th10-ghidra, check, {})`; require a passed
   attestation for `target:th10-main` and
   `attestation.provider_transport=factory-native-command`.
   Stop on a target or provider mismatch. A failed or timed-out command may
   leave files; always inspect status afterward and page durable output instead
   of guessing.

Native Ghidra use:
1. Discover `th10-ghidra` operations instead of inventing tool names or schemas.
   Require `attestation.status=passed`, target `target:th10-main`, and
   `attestation.provider_transport=factory-native-command` on every useful result.
   Read each returned input schema before calling it: `{}` is valid only for
   operations whose schema has no required fields. Never probe address-, range-,
   or name-dependent operations with empty arguments.
   The native core is: `check {}`;
   `function`/`decompile`/`callers`/`callees {"addresses":["0x..."]}`;
   `disassemble {"addresses":["0x..."],"instruction_count":N}`;
   `xrefs_to`/`xrefs_from {"addresses":["0x..."],"limit":N}`;
   `list_functions {"query":"optional","offset":N,"limit":N}`; and
   `search_strings {"query":"required","limit":N}`. Discovery schemas remain
   authoritative; do not extrapolate one operation's fields to another.
2. Decompilation, disassembly, xrefs, bytes, names, types, and boundaries are
   provisional hypotheses with `exactness_credit=none`.
3. The native Ghidra provider is read-only. Mirror durable conclusions into
   source, ledgers, scripts, or concise game-local knowledge; do not expect
   Ghidra renames/comments to persist through this surface. Never request
   target-byte patching.
4. If attestation fails, do not substitute another game's provider or proceed
   from remembered output. Report the mismatch as unavailable and stop
   target-dependent work.

Autonomous exact loop:
1. Maintain a mixed frontier rather than a smallest-function strategy. Inspect
   unresolved candidates by target extent, call-graph/owner importance,
   relocation/data dependencies, control-flow complexity, subsystem coverage,
   and prior mismatch history. Select one evidence-connected bounded packet: a
   caller/callee cohort, one subsystem seam, or one candidate plus its necessary
   data/ABI context. State why it is representative, its addresses and current
   ledger state, known evidence, unknowns, and the observable outcome sought for
   that packet.
   Do not spend the conversation accumulating only easy function-count wins.
   Regularly attack a hard frontier: a materially larger function/cohort,
   central owner or dispatcher, complex ABI/control flow, relocation/data-owner
   boundary, or a previously blocked near-match.
   A hard-frontier result may honestly be exact, source-present/non-exact, a
   corrected boundary/origin, or a documented unknown; never force promotion to
   satisfy the scheduling rule.
2. Reconcile entry/exit, tails, padding, tables, xrefs, relocations, and physical
   ownership before treating the Ghidra candidate as an authored function extent.
3. Classify origin independently from implementation and exactness. Keep
   uncertain candidates `unknown/review`.
4. Recover ABI, layout, constants, globals, side effects, error paths, and
   compiler-sensitive source shape. Add source presence without claiming a
   match.
5. Establish only compiler/profile facts demonstrated by focused probes. PE
   linker 7.10 and dominant Rich build-6030 records support a VC7.1 SP1-era
   family hypothesis, but exact compiler surfaces, flags, translation-unit
   partition, libraries, resources, and link order begin unknown.
6. Run the cheapest focused compile/diff feedback first, then the affected
   translation unit and available whole-build diagnostic at useful milestones.
   Compare complete owned extents and relocations. Distinguish source mismatch,
   compiler-profile mismatch, boundary error, owner error, and library code.
7. Add canonical match/exact ledger rows only after a repeatable zero-difference
   target-bound check. Never promote a Ghidra observation or plausible C source.
8. Review status and complete diffs, run focused validation, update the handoff
   and durable game-local knowledge when warranted, then create one coherent
   English `gpt-web:` checkpoint. Continue with another connected bounded packet
   while the browser and context remain reliable; do not stop after orientation
   or one trivial edit.

Adjacent-game hypothesis discipline:
- Search focused TH08, TH09, or TH095 source, history, scripts, and
  game-local notes
  when a TH10 target observation suggests a related engine subsystem. These
  repositories may accelerate naming, source-shape, ownership, ABI, and compiler
  hypotheses; they do not prove any TH10 fact.
- Treat every adjacent game's names, owners, layouts, abstractions, phase state,
  and uncommitted work as provisional hypothesis material for TH10.
- Prefer committed adjacent source. Record its repository, observed HEAD, and
  dirty status when it materially shapes a hypothesis; treat any consulted
  uncommitted content as volatile. Validate the proposal through TH10 target bytes,
  Ghidra/xrefs, ABI evidence, compiler output, and the relevant TH10 Oracle. Never
  transfer addresses, extents, data ownership, exactness, or completion claims.
- If adjacent source conflicts with TH10 evidence, TH10 wins. If TH10 cannot
  decide, retain unknown rather than selecting the more familiar implementation.

Whole-build discipline:
- Keep `config/build.toml` honestly open while inputs are unknown, but exercise
  the build skeleton early and update it as evidence appears.
- Function exactness does not prove source/data ownership, compilation, link
  closure, resources, initialized globals, imports, relocations, launch, or
  runtime behavior.
- Do not enter semantic rewriting or portability yet. The required gates are
  exact reconstruction, faithful Windows i386 build/runtime closure, semantic
  reconstruction under original-plus-reconstructed dual Oracles, then ports.

Artifact discipline:
- Treat `.analysis/` as ignored scratch, not a knowledge base. Inventory its
  size at entry and exit without recursively hashing large old trees.
- Keep searches bounded. Prefer git grep/history for tracked content; exclude
  .git, .analysis, build, and .tools from live rg searches unless a named
  ignored path is deliberately in scope. Never follow repository-root symlinks;
  a Wine dosdevices/z: link can escape into the host filesystem.
- Reuse one `.analysis/gpt-web/<campaign-id>/` directory with a manifest for
  multi-command work. Prefer bounded provider queries and temporary directories.
- Review at 256 MiB per campaign and record disposition for files over 64 MiB.
  Delete only reproducible current-session scratch with known ownership and no
  references; never bulk-delete legacy/unknown analysis state, IDBs, toolchains,
  targets, Wine prefixes, or another process's output.

At each checkpoint and final handoff report:
- starting/ending HEAD, branch, and dirty-state counts;
- recovered dirty paths and preserved unknown/unrelated paths;
- exact bounded scope, addresses, and source/ledger files changed;
- commands actually run and their results, including unavailable checks;
- separate states for source presence, exactness, whole-build closure, runtime,
  and accepted Factory facts;
- checkpoint hashes/subjects, with confirmation that nothing was pushed;
- `.analysis/` starting/ending size and retained/removed artifacts;
- remaining unknowns, blockers, and the next evidence-connected packet.
- packet-selection balance since the last hard-frontier attempt, including why
  the next candidate is not merely the easiest remaining function.

Work seriously and keep the exact feedback loop fast, but do not try to finish
the entire TH10 exact phase in this one browser conversation. Judge the amount
of work from packet difficulty, compile/Oracle latency, browser responsiveness,
and remaining reliable context. One difficult packet may be enough; several
tightly connected small packets may fit. Before another packet would make the
conversation slow or fragile, finish or revert the current experiment, run its
applicable checks, commit coherent work, and write an exact continuation handoff.
Do not wait for a disconnect. The next conversation will audit and continue from
live repository state. A handoff does not mean the exact phase is complete. Do
not claim completion, exactness, acceptance, or push without direct evidence for
that exact state.
```
