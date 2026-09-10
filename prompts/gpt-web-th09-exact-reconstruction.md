# GPT-web TH09 exact-reconstruction prompt

Use this after `th09` and `th09-ida` are visible through the public Factory MCP
and a public native-provider smoke test passes. The prompt does not assume that
ChatGPT injected any plugin skill.

```text
Work autonomously on the TH09 exact source-reconstruction phase through the
shared Touhou Reconstruction Factory. Do not assume any skill body was loaded.

Communicate with me in Chinese. Write code, identifiers, documentation, ledger
content, and Git commit messages in English.

Select exactly:
- repository: th09
- analysis provider: th09-ida
- target: target:th09-main
- phase: exact reconstruction, with early faithful Windows i386 build feedback

Read these instructions before editing, using factory_repository_run_shell:
- /home/pentester/coding/codex_ida/th09-reconstruction/th09/AGENTS.md
- /home/pentester/coding/codex_ida/th09-reconstruction/th09/docs/RE_HANDOFF.md
- /home/pentester/coding/codex_ida/th09-reconstruction/th09/docs/RE_WORKFLOW.md
- /home/pentester/coding/codex_ida/th09-reconstruction/th09/docs/ORACLES.md
- /home/pentester/coding/codex_ida/touhou-reconstruction-factory/contracts/gpt-web-reconstruction-session-v4.json
- /home/pentester/coding/codex_ida/touhou-reconstruction-factory/contracts/worktree-recovery-and-analysis-artifacts-v1.json
- /home/pentester/coding/codex_ida/touhou-reconstruction-factory/docs/new-game-bootstrap.md
- /home/pentester/coding/codex_ida/touhou-reconstruction-factory/docs/worktree-recovery-and-analysis-artifacts.md

The TH09 repository runner also mounts these adjacent-game repositories
read-only as hypothesis sources:
- /home/pentester/coding/codex_ida/th08-reconstruction/th08
- /home/pentester/coding/codex_ida/th095-reconstruction/th095

If a Factory path is not mounted, report that once and continue under the
complete rules below. Missing skill injection or one missing guidance path is
not itself a reason to stop.

Ground rules:
1. Accuracy dominates completeness. Unknown is valid. Never guess authorship,
   function extent, ABI, type, object owner, toolchain flag, equality, or
   completion.
2. Exercise broad engineering autonomy. Compose repository Bash, Python, Git,
   the shared VC7.1/Wine toolchain when available, and discovered atomic IDA
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

Mandatory recovery gate:
1. Call factory_describe, factory_list_repositories, and
   factory_get_repository_status(th09).
2. Regardless of whether a disconnect is known, inspect branch, HEAD, recent
   commits, porcelain-v2 status, staged and unstaged diffs, all relevant
   untracked files, ignored analysis/build state, and the handoff.
3. Classify each dirty path as recoverable interrupted work, unrelated
   pre-existing work, reproducible generated output, or unknown. Finish and
   checkpoint recoverable work first. Preserve and exclude unrelated or unknown
   work. Never reset, overwrite, delete, or stage it merely to obtain a clean
   tree.
4. Run the repository target, IDA, ledger, status, and public-CI preflights named
   in AGENTS.md. Stop on a target mismatch. A failed or timed-out command may
   leave files; always inspect status afterward and page durable output instead
   of guessing.

Native IDA use:
1. Discover `th09-ida` operations instead of inventing tool names or schemas.
   Require `attestation.status=passed`, target `target:th09-main`, and
   `provider_transport=factory-native-stdio` on every useful result.
2. Decompilation, disassembly, xrefs, bytes, names, types, and boundaries are
   provisional hypotheses with `exactness_credit=none`.
3. When discovery advertises `database_metadata_writable=true`, use the atomic
   comment/name/prototype/type/stack operations where they improve the shared
   IDA database. Read back important edits. Mirror durable conclusions into
   source, ledgers, or concise game-local knowledge. Never request target-byte
   patching.
4. If attestation fails, do not substitute another game's provider or proceed
   from remembered output. Report the mismatch as unavailable and stop
   target-dependent work.

Autonomous exact loop:
1. Select one evidence-connected bounded packet: a small caller/callee cohort,
   one subsystem seam, or one candidate plus its necessary data/ABI context.
   State addresses, current ledger state, known evidence, unknowns, and a
   measurable stop condition.
2. Reconcile entry/exit, tails, padding, tables, xrefs, relocations, and physical
   ownership before treating the IDA candidate as an authored function extent.
3. Classify origin independently from implementation and exactness. Keep
   uncertain candidates `unknown/review`.
4. Recover ABI, layout, constants, globals, side effects, error paths, and
   compiler-sensitive source shape. Add source presence without claiming a
   match.
5. Establish only compiler/profile facts demonstrated by focused probes. The
   target identifies VC7.1 build 3077, but flags, translation-unit partition,
   libraries, resources, and link order begin unknown.
6. Run the cheapest focused compile/diff feedback first, then the affected
   translation unit and available whole-build diagnostic at useful milestones.
   Compare complete owned extents and relocations. Distinguish source mismatch,
   compiler-profile mismatch, boundary error, owner error, and library code.
7. Add canonical match/exact ledger rows only after a repeatable zero-difference
   target-bound check. Never promote an IDA observation or plausible C source.
8. Review status and complete diffs, run focused validation, update the handoff
   and durable game-local knowledge when warranted, then create one coherent
   English `gpt-web:` checkpoint. Continue with another connected bounded packet
   while the session has reliable context and useful feedback; do not stop after
   orientation or one trivial edit.

Adjacent-game hypothesis discipline:
- Search focused TH08 or TH095 source, history, scripts, and game-local notes
  when a TH09 target observation suggests a related engine subsystem. These
  repositories may accelerate naming, source-shape, ownership, ABI, and compiler
  hypotheses; they do not prove any TH09 fact.
- TH095 is still undergoing semantic reconstruction. Treat its names, owners,
  layouts, abstractions, and uncommitted state as provisional even within TH095.
- Prefer committed adjacent source. Record its repository, observed HEAD, and
  dirty status when it materially shapes a hypothesis; treat any consulted
  uncommitted content as volatile. Validate the proposal through TH09 target bytes,
  IDA/xrefs, ABI evidence, compiler output, and the relevant TH09 Oracle. Never
  transfer addresses, extents, data ownership, exactness, or completion claims.
- If adjacent source conflicts with TH09 evidence, TH09 wins. If TH09 cannot
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
- Reuse one `.analysis/gpt-web/<campaign-id>/` directory with a manifest for
  multi-command work. Prefer bounded provider queries and temporary directories.
- Review at 256 MiB per campaign and record disposition for files over 64 MiB.
  Delete only reproducible current-session scratch with known ownership and no
  references; never bulk-delete legacy/unknown analysis state, IDBs, toolchains,
  targets, Wine prefixes, or another process's output.

At each checkpoint and final handoff report:
- starting/ending HEAD, branch, and dirty-state counts;
- recovered dirty paths and preserved unknown/unrelated paths;
- exact bounded scope, addresses, source/ledger files, and IDA metadata edits;
- commands actually run and their results, including unavailable checks;
- separate states for source presence, exactness, whole-build closure, runtime,
  and accepted Factory facts;
- checkpoint hashes/subjects, with confirmation that nothing was pushed;
- `.analysis/` starting/ending size and retained/removed artifacts;
- remaining unknowns, blockers, and the next evidence-connected packet.

Continue until several coherent bounded packets are checkpointed, a concrete
evidence/tool boundary blocks progress, or context reliability requires a clean
handoff. Do not claim completion, exactness, acceptance, or push without direct
evidence for that exact state.
```
