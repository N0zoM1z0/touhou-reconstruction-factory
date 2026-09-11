# GPT-web reconstruction session prompt

This prompt starts one autonomous, evidence-first reconstruction session in a
game repository registered by the shared Touhou Reconstruction Factory MCP. The
session contract is `gpt-web-reconstruction-session-v4`.

The mandatory companion contract is
`worktree-recovery-and-analysis-artifacts-v1`. Automatic skill loading is an
optional convenience; this prompt is designed to work without it.

## Ready-to-run prompt

Select **@Touhou Reconstruction Factory**, then paste the complete prompt below.
Do not shorten it to a skill name: the Web client may expose the MCP app without
injecting the skill body.

The repository and its Git history are the durable resume state. `RESUME_COMMIT`
is orientation for the agent, not authority to reset current work.

## Complete standalone prompt

```text
Run one autonomous evidence-first Touhou source-reconstruction session under
contract gpt-web-reconstruction-session-v4 plus mandatory companion contract
worktree-recovery-and-analysis-artifacts-v1. Do not assume any bundled skill was
loaded.

Factory guidance paths on this host:
- /home/pentester/coding/codex_ida/touhou-reconstruction-factory/contracts/gpt-web-reconstruction-session-v4.json
- /home/pentester/coding/codex_ida/touhou-reconstruction-factory/contracts/worktree-recovery-and-analysis-artifacts-v1.json
- /home/pentester/coding/codex_ida/touhou-reconstruction-factory/docs/worktree-recovery-and-analysis-artifacts.md

Before editing, try to read those paths with factory_repository_run_shell. If
the operator has not mounted them into the repository-work sandbox, report that
fact once and continue under this complete inline prompt; do not invent omitted
rules and do not stop merely because automatic skill loading is unavailable.

Task:
- GAME_ID: th105
- OBJECTIVE: <one concrete source-reconstruction objective>
- SCOPE_HINT: <files, symbols, addresses, or subsystem; use "discover" if unknown>
- STOP_CONDITION: <a measurable result for this session>
- RESUME_COMMIT: <prior gpt-web checkpoint hash, or "current">

Language:
- Communicate with me in Chinese.
- Write source, documentation, identifiers, and Git commit messages in English.

Operating model:
1. The Factory is a capability and evidence framework, not a rigid workflow
   engine. Exercise engineering judgment. Use broad composable repository Bash
   for unanticipated work, and combine atomic Factory tools when their schemas,
   identity binding, analysis, replay, or paging make the work more accurate or
   efficient.
2. The Agent may inspect and change the real registered game worktree, including
   current dirty/untracked files and ignored repo-local tools; run repository
   scripts, Wine, compilers, object comparison, IDA/Ghidra queries, and useful
   local experiments; and create local Git commits. Network and Git push are
   unavailable.
3. Attempt authority is deliberately broad. Truth admission is deliberately
   narrow. Analysis guides hypotheses, build results give feedback, and Git
   commits give checkpoints. Only accepted replay receipts enter the Truth
   Kernel.
4. Accuracy dominates completeness. `unknown` is a correct outcome. Never guess
   an identity, owner, extent, provenance, equivalence, or exactness result.

Start:
1. Call factory_describe and factory_list_repositories. Select exactly GAME_ID.
2. Call factory_get_repository_status. Record the actual branch, HEAD, upstream,
   staged/unstaged/untracked counts, and dirty state. If RESUME_COMMIT names an
   earlier checkpoint, inspect history and changes since it; do not reset or
   discard newer work merely to match the prompt.
3. Treat any non-clean state as a mandatory recovery gate, regardless of whether
   a disconnect is known. Before selecting or editing a new packet, inspect
   porcelain-v2 status, complete staged and unstaged diffs, every relevant
   untracked path, the latest handoff, recent relevant history, and available
   tests or manifests. Classify each path as recoverable current work, unrelated
   pre-existing work, generated ephemeral output, or unknown origin/intent.
   Finish and checkpoint recoverable work first; preserve and exclude unrelated
   work; never delete, reset, overwrite, or stage unknown work. If overlap cannot
   be isolated, report a concrete blocker. Staged does not mean complete and
   mtime does not prove provenance.
4. Use factory_repository_run_shell to read the repository's current AGENTS.md
   or equivalent instructions, architecture, build/oracle scripts, ledgers, and
   relevant recent commits. Existing local changes are part of the live context:
   understand and preserve them, and distinguish them from changes made now.
5. Turn the objective into one bounded work packet. State the candidate
   functions/addresses/extents/files, evidence already available, unknowns, and
   measurable stop condition. Do not invent a completion percentage without an
   independently established boundary and denominator.

Investigate and reconstruct:
1. Discover the registered IDA or Ghidra provider and its operation schema before
   calling it. Require target attestation. Names, types, decompilation, xrefs,
   disassembly, and boundaries remain provisional source-hypothesis evidence
   with exactness_credit=none.
   If a native provider advertises database_metadata_writable=true, use its
   discovered atomic comment/name/prototype/type/stack operations when they
   improve shared analysis state, then read back important edits. Such edits
   remain provisional and never change source or exactness. Target-byte patching
   is outside the Factory provider.
2. Correlate analysis with current source, project history, and the strongest
   available repository-native evidence. Existing comments, ledgers, and prior
   agent work are candidates, not automatic truth.
3. Write maintainable natural C or C++. Do not routinely substitute inline
   assembly, embedded machine-code bytes, generated byte arrays, data disguised
   as source, or oracle-specific tricks. If the evidence demonstrates a genuinely
   irreducible exception, explain the exact scope and smallest exception first.
4. Use factory_repository_run_shell freely to compose rg, Git, scripts, Python,
   Wine, repo-local toolchains, object diff, and build/oracle diagnostics. The
   command runs in the real worktree. Nonzero exit and timeout do not roll back
   files; always inspect status and diff after an interrupted or surprising run.
   Keep searches bounded: prefer git grep/history for tracked content; for live
   untracked source use rg --hidden while excluding .git, .analysis, build, and
   .tools. Never begin with a symlink-following repository-root traversal: a
   Wine dosdevices/z: link can escape into the host filesystem. Search a named
   ignored evidence path only when it is intentionally in scope.
5. Run feedback from cheapest/focused to strongest/broader: syntax/static checks,
   affected exact function/extent checks, production translation-unit compile,
   and cold whole-product build at bounded milestones. Owner, ABI, layout,
   shared-header, link-input, or build-graph changes require both affected exact
   replay and product closure; neither result grants the other. If command output
   is truncated, page it with factory_get_repository_command_output instead of
   guessing the omitted result.

Analysis artifact lifecycle:
1. Treat `.analysis/` as ignored, non-authoritative working storage, never as a
   knowledge base or current evidence by itself. At preflight, inventory its
   total and top-level size without hashing every large file. Old outputs are
   leads until their source HEAD, target, database, tool, and command inputs are
   checked or reproduced.
2. Use command-local temporary directories with cleanup for one-shot outputs.
   For multi-command work, reuse one `.analysis/gpt-web/<campaign-id>/` scratch
   root and create `manifest.json` before the first large output. Record campaign,
   game, starting/current HEAD, state, and each artifact's path, class, producer,
   input binding, size, references, and disposition. Do not create a fresh whole-
   program export, copied Wine prefix, copied IDA/Ghidra project, or worktree for
   every probe.
3. Use 256 MiB per campaign as a soft review budget and 64 MiB as a large-
   artifact threshold. Crossing either requires a reason and cleanup disposition,
   not automatic deletion. Prefer bounded analysis queries, registered provider
   state, one reused worktree, and paged output.
4. Before each checkpoint, measure growth and retain compact conclusions in
   tracked evidence. Delete only explicit current-session scratch paths whose
   ownership, inactive producer, reproducibility/non-need, and lack of references
   are established. Never bulk-delete `.analysis/`, delete by age alone, or touch
   legacy-unknown/shared provider databases, toolchains, or Wine prefixes.

Checkpoint:
1. Create local Git commits after coherent reviewable units; checkpoints are a
   normal part of the work, not merely a final handoff.
2. Before each commit, inspect git status, the complete working diff, and the
   staged diff. Stage only intended files and run the available focused checks.
3. Use a concise English subject beginning with `gpt-web:`. Preserve useful
   incremental history for review, rollback, bisect, and later continuation.
4. Do not push. Do not rewrite or erase pre-existing work unless the user
   explicitly makes that the task. A clean worktree and a commit hash prove only
   checkpoint state, not reconstruction exactness.

Knowledge and verification:
1. If a result will materially help a later session, update and commit only the
   game-local `.reconstruction/game-knowledge.json` input. Keep schema_version=1,
   document_type=game-knowledge-input, authority=game-local,
   factory_publication=none, and exactly one matching game scope per entry. Use
   only observed, reproduced, unknown, or superseded; `reproduced` requires a
   passed validation actually run. Record limitations and do not write a chat
   journal.
2. Never edit Factory catalogs, fixtures, schemas, prompts, or skills to promote
   a game observation. Cross-game extraction is a later local-Codex review of
   completed game history.
3. Submit a replay only for a discovered claim bound to the committed source
   state being checked. Keep job completion, receipt verdict, registry decision,
   and accepted-fact query distinct. If dirty source or unsupported scope makes
   replay ineligible, report that boundary accurately.
4. Report function/extent exactness, production closure, runtime storage
   identity, and runtime scenario validation as independent planes. A successful
   build or playable/manual report is not a runtime receipt. When the Factory has
   no runtime provider, report the corresponding live plane as `unknown`.

Continue until STOP_CONDITION is met, a concrete evidence/tool boundary blocks
the packet, or a materially different scope decision is required.

Final handoff:
- Session status: stop condition met | blocked | bounded progress
- Game and objective
- Starting and ending commit
- Starting and ending staged/unstaged/untracked state
- Dirty-work recovery classifications, actions, and retained unknowns
- Starting and ending `.analysis/` bytes, current scratch/manifest state, and
  every retained large artifact or removed current-session artifact
- Bounded scope completed and excluded
- Analysis provider, target attestation, evidence, and exactness limitations
- Changed files and rationale
- Created `gpt-web:` checkpoint hashes and subjects
- Game-local knowledge changes, or why none were durable enough
- Tests/commands actually run, exits/results, and unavailable checks
- Independent status for exactness, production closure, runtime storage, and
  runtime scenario planes
- Accepted Truth Kernel facts, separately from analysis/build/commit candidates
- Unknowns and blockers
- Next useful action

Do not claim that source was committed, replayed, verified, accepted, or pushed
unless returned Factory/Git evidence proves that exact state. Never equate those
states with one another.
```

## Choosing a stop condition

A useful stop condition is bounded and observable, for example:

```text
The selected function cohort has maintainable source candidates; focused
repository-native compile/object checks have been run; coherent changes are in
one or more local `gpt-web:` checkpoint commits; replay-accepted extents and all
remaining unknown ownership/exactness questions are reported separately.
```

“Improve the reconstruction” and “reach 99%” are goals, not stop conditions,
unless the repository already has a verified denominator and the task names an
exact measurable increment.
