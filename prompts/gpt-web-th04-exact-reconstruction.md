# GPT-web TH04 PC-98 exact-reconstruction prompt

Use this prompt to continue the mature TH04 MAIN exact-reconstruction campaign
through the shared Factory MCP. It is complete enough to paste into GPT-web even
when no bundled skill body is injected.

```text
Continue TH04 authored-function discovery and natural-source byte-exact
reconstruction through the shared Touhou Reconstruction Factory. Work seriously,
move quickly through the cheapest correct feedback loop, and use broad engineering
judgment. Do not assume any skill body was loaded.

Communicate with me in Chinese. Write source, identifiers, documentation,
evidence, ledgers, and Git commit messages in English.

Select exactly:
- repository: th04
- analysis provider: th04-ghidra
- current target: target:th04-main
- current artifact: th04-main / MAIN.EXE
- private target: /home/pentester/coding/codex_ida/th04-reconstruction/th04/.analysis/targets/th04/main.exe
- phase: PC-98 16-bit authored-boundary review plus natural-source exact reconstruction

The private executable is ignored operator input. Never commit, patch, replace,
relocate, or publish it. Its current canonicality is only
`candidate-local-attested`: the hash identifies the tested local Japanese copy,
not an independently proved pristine release.

Before editing, read these paths with factory_repository_run_shell:
- /home/pentester/coding/codex_ida/th04-reconstruction/th04/AGENTS.md
- /home/pentester/coding/codex_ida/th04-reconstruction/th04/docs/RE_HANDOFF.md
- /home/pentester/coding/codex_ida/th04-reconstruction/th04/docs/RE_WORKFLOW.md
- /home/pentester/coding/codex_ida/th04-reconstruction/th04/docs/ORACLES.md
- /home/pentester/coding/codex_ida/th04-reconstruction/th04/docs/BOUNDARY_REVIEW.md
- /home/pentester/coding/codex_ida/th04-reconstruction/th04/docs/TOOLCHAIN.md
- /home/pentester/coding/codex_ida/th04-reconstruction/th04/docs/GHIDRA.md
- /home/pentester/coding/codex_ida/th04-reconstruction/th04/docs/PROGRESS.md
- /home/pentester/coding/codex_ida/touhou-reconstruction-factory/contracts/gpt-web-reconstruction-session-v5.json
- /home/pentester/coding/codex_ida/touhou-reconstruction-factory/contracts/worktree-recovery-and-analysis-artifacts-v1.json
- /home/pentester/coding/codex_ida/touhou-reconstruction-factory/docs/verification-planes.md
- /home/pentester/coding/codex_ida/touhou-reconstruction-factory/docs/agent-autonomy.md
- /home/pentester/coding/codex_ida/touhou-reconstruction-factory/docs/worktree-recovery-and-analysis-artifacts.md

If a Factory path is not mounted, report that once and continue under this
complete prompt plus the TH04 repository documents. Missing skill injection is
not a reason to stop.

The campaign has two equally important tracks:
1. Expand and correct the authored-function universe. Do not trust Ghidra,
   historical TASM PROC starts, ReC98, existing ledgers, or old prose as a
   complete boundary inventory. Reconcile gaps, shared tails, jump tables,
   post-return data, far entries, alignment, relocation ownership, compiler or
   library code, original-style assembly, and target-authored code that no tool
   recognized.
2. Recover maintainable natural C/C++ for reviewed authored extents and prove
   exactness through the complete configured TH04 Oracle set. Source presence,
   compilation, a plausible decompilation, normalized instructions, or an exact
   neighboring function is not exactness.

Campaign pressure target: drive both reviewed authored-function exactness and
reviewed authored-byte exactness toward at least 99.5%, while continuously
auditing and expanding the authored boundary denominator. This is intentionally
an ambitious moving target, not an automatic stop rule and not a claim about
99.5% of MAIN.EXE or the whole game. Reaching it on today's reviewed ledger does
not authorize GPT-web to declare completion; the operator will decide when a
later independent audit is sufficient.

Accuracy dominates completeness. Unknown and incomplete are honest outcomes.
Never force an extent, origin, owner, near/far distance, memory model, type,
toolchain flag, source shape, or exact verdict merely to increase a count.

Worktree recovery is mandatory at every conversation start, even when nobody
reported a disconnect:
1. Call factory_describe, factory_list_repositories, and
   factory_get_repository_status(th04). Record branch, HEAD, upstream relation,
   staged/unstaged/untracked state, and recent relevant commits.
2. Inspect porcelain-v2 status, complete staged and unstaged diffs, relevant
   untracked files, ignored current analysis/build state, and the latest handoff.
3. Classify non-clean paths as recoverable interrupted work, unrelated existing
   work, reproducible ephemeral output, or unknown. Understand and finish the
   recoverable work first. Preserve and exclude unrelated or unknown work. Never
   reset, overwrite, delete, or stage it just to make the tree clean.
4. Run `python3 scripts/preflight.py`, `python3 scripts/status.py`, and
   `python3 scripts/boundary_review/validate_function_boundary_ledger.py`.
   Always inspect status again after an interrupted, failed, or timed-out command.

Attest analysis before using it:
1. Call factory_list_analysis_operations(th04-ghidra), read the returned schemas,
   then call factory_analysis_call(th04-ghidra, get_metadata, {}). Require passed
   attestation for repository th04 and target target:th04-main.
2. Use only discovered argument schemas. Keep address evidence qualified by the
   artifact plus segment identity and segment:offset. A linear image or emulator
   address alone is incomplete without its load-segment interpretation.
3. Ghidra names, decompilation, disassembly, xrefs, function boundaries, and
   types are provisional target observations with zero exactness credit. Use
   atomic analysis operations where useful, but compose broad repository Bash,
   raw decoding, maps, ledgers, and scripts for questions the tool list did not
   predict.
4. The repository-native read-only cross-check is
   `python3 scripts/ghidra.py th04-main check`. It must agree on the target MZ
   file, header/load mapping, entry CS:IP, relocation sequence, load-module
   digest, and sampled bytes. Passing it attests the database identity, not its
   inferred semantics or boundaries.

Respect the historical platform. This is 16-bit DOS MZ/OMF code for PC-98, not
PE/COFF and not flat 32-bit x86. Preserve Turbo C++ 4.0J/TCC 4.02, TASM32 5.0,
TLINK 6.10, memory model, near/far functions and pointers, calling convention,
segment/group ownership, DGROUP assumptions, enum and integer widths, packing,
x87 behavior, translation-unit order, linker order, MZ relocations, and PC-98
hardware behavior until bounded evidence proves otherwise. `ZUN.COM` is itself
an MZ file despite its extension.

Do not use inline assembly, target-derived byte arrays, `#pragma codestring`,
fake returns, inert padding, ABI lies, target patching, or copied target bytes to
manufacture equality. Genuine original-style or irreducible assembly is a
separate evidence-backed classification, not a shortcut for likely authored C++.

Use the live handoff and machine ledgers rather than frozen counts in this prompt.
At the current handoff, `sub_11DE6` in MAIN_012_TEXT is a useful first hypothesis:
a target-reviewed but not reconstructed or accepted FAR extent at
0x21DE6..0x21E11. Verify all of that against current ledgers, target bytes,
TASM/map evidence, and Ghidra before using it. Test whether natural Turbo C++
can reproduce its nine-threshold LOOP scan, `shot_level` store, callback
selection, same-segment `NOP; PUSH CS; CALL near` sequence, and RETF. The handoff
is orientation, never acceptance.

After that compact frontier, do not spend the conversation collecting only easy
small-function wins. Deliberately take on structurally meaningful work: a larger
caller/callee cohort, central owner/dispatcher, provisional or missing boundary,
shared tail or jump-table extent, relocation/data-owner seam, difficult ABI
shape, or a previously blocked near-match with a genuinely new hypothesis. A
hard result may be exact, source-present/non-exact, a corrected boundary/origin,
or a durable unknown. All are better than a forced false promotion.

ReC98 at
`/home/pentester/coding/codex_ida/th04-reconstruction/th04/_reference/ReC98`
is a valuable hypothesis, build scaffold, and cross-game source-shape reference.
It is not authoritative. Most remaining authored candidates extend beyond its
reconstruction. Validate every borrowed name, boundary, owner, ABI, and source
form against TH04-local evidence; never inherit its exactness or progress claim.

For each packet:
1. Bound artifact, segment, offset/extent, origin question, owner, callers,
   callees, tables/tails, relocations, ABI, existing evidence, and unknowns.
2. Write the smallest maintainable natural-source candidate in the correct
   `src/main/` semantic subsystem. Do not revive retired `exact/`, `partial/`, or
   `modules/` layouts and do not bulk-copy ReC98.
3. Run cheap compiler/source probes first. Diagnose mismatches as source shape,
   compiler/profile, boundary, relocation/layout, owner, or library/original ASM
   rather than blindly editing C++.
4. For exact promotion, run the focused cold replay, for example
   `python3 scripts/replay_th04_main_exact_units.py --unit <unit-id> --run-id <unique-id>`.
   It performs two isolated serial cold builds. Never run writable Borland/Wine
   reconstruction builds concurrently against shared outputs.
5. Before promotion, run the repository-required aggregate cold replay with no
   `--unit` selection and close target identity, format, boundary, toolchain,
   OMF, map/layout, ordered relocation, raw-byte, determinism, and ledger gates.
   Amortize expensive aggregate work over a coherent packet when repository rules
   allow, but never omit a required promotion gate.
6. Inspect the complete diff and status, update ledgers/evidence and the current
   handoff, run focused validation plus `python3 scripts/ci.py` and
   `git diff --check`, then create an English local `gpt-web:` checkpoint.
   Never push to any remote. A commit is review/resume state, not exactness
   evidence.

The pinned ReC98 overlay build is an exactness Oracle for maintained owned
extents, not a standalone TH04 product build. Keep production closure separate:
many TH04 translation units, localized headers, source/data owners, and the full
TH04-owned link graph remain incomplete. Do not claim whole-product compile/link
closure, runtime storage identity, or runtime scenario validation from exact
unit replay.

Treat `.analysis/` as bounded ignored workspace, not knowledge. Inventory total
and top-level size at entry and exit without recursively hashing old trees. Reuse
one current-session scratch location, bounded provider queries, the existing
Ghidra project, target, toolchain, Wine prefix, and current cold baseline. Do not
copy whole databases, prefixes, worktrees, targets, or whole-program exports per
probe. Delete only explicit current-session reproducible scratch with established
ownership, inactive producers, and no references. Never bulk-delete legacy or
unknown analysis state.

Work with urgency, but do not try to finish the entire TH04 exact campaign in
one browser conversation. Decide how much fits from actual difficulty, serial
cold-build latency, browser responsiveness, and remaining reliable context. One
hard packet may be enough; several tightly connected smaller packets may fit.
Before another packet would make the conversation slow or fragile, finish or
revert the active experiment, run applicable checks, commit coherent progress,
and update `docs/RE_HANDOFF.md` with exact continuation evidence. Do not wait for
a disconnect. A new conversation will audit live Git and continue. This handoff
does not mean the exact phase or project is complete.

At handoff report starting/ending HEAD and dirty state; recovered/pre-existing
paths; artifacts, segments, offsets, and boundaries reviewed; source and ledger
changes; target/Ghidra/toolchain attestation; focused and aggregate Oracle
results actually run; independent exactness, standalone production-closure,
runtime-storage, runtime-scenario, and Factory-acceptance states; checkpoint
hashes; `.analysis/` growth/disposition; retained unknowns and negative evidence;
and the first concrete evidence-connected candidate for the next conversation.
Do not claim source, exactness, build closure, acceptance, completion, or push
without direct evidence for that exact state.
```
