# GPT-web reconstruction session prompt

This prompt starts one bounded reconstruction session against any game registered
by the shared Touhou Reconstruction Factory MCP. Change the task values, not the
authority rules. The session contract is
`gpt-web-reconstruction-session-v1`.

## Short prompt with the plugin installed

Select **@Touhou Reconstruction Factory** in ChatGPT, then send:

```text
Run an evidence-first reconstruction session using the bundled
factory-reconstruction workflow.

GAME_ID: th105
OBJECTIVE: <one concrete source-reconstruction objective>
SCOPE_HINT: <optional files, symbols, addresses, or subsystem; use "discover" if unknown>
STOP_CONDITION: <a measurable result for this session>
RESUME_WORKSPACE_ID: none

Communicate with me in Chinese. Write source, documentation, identifiers, and
the proposed commit message in English. Accuracy is more important than
completeness: preserve unknown whenever the available evidence cannot prove a
claim.
```

Use the exact returned workspace capability in `RESUME_WORKSPACE_ID` after a
disconnect. Do not create a replacement workspace merely because a conversation
ended.

## Standalone prompt

Use this complete version when the bundled skill is unavailable or when testing
the workflow independently of automatic skill selection.

```text
Run one evidence-first Touhou source-reconstruction session under contract
gpt-web-reconstruction-session-v1.

Task:
- GAME_ID: th105
- OBJECTIVE: <one concrete source-reconstruction objective>
- SCOPE_HINT: <optional files, symbols, addresses, or subsystem; use "discover" if unknown>
- STOP_CONDITION: <a measurable result for this session>
- RESUME_WORKSPACE_ID: none

Language:
- Communicate with me in Chinese.
- Write source, documentation, identifiers, and the proposed commit message in English.

Authority and safety:
1. Use only the Touhou Reconstruction Factory plugin/MCP as computer,
   repository, analysis, and replay authority. Do not use GitHub or another
   source-management integration. Do not invoke another plugin unless I ask.
2. Start with factory_describe and factory_list_repositories. Select only the
   returned GAME_ID and never invent a host path, target identity, provider,
   operation, claim, or prior success.
3. If RESUME_WORKSPACE_ID is present, call factory_get_workspace and continue
   it. Otherwise create exactly one disposable workspace with a stable unique
   idempotency key. Retain and report its ID, baseline commit, expiry, and
   source_worktree_dirty_observed. The workspace contains committed HEAD only;
   never claim to see, preserve, or overwrite canonical dirty/untracked/ignored
   files.
4. Do not kill, interrupt, or reconfigure unrelated IDA, Ghidra, shell, Codex,
   compiler, or game processes. Do not discard the workspace unless I explicitly
   ask or say that it is no longer needed.
5. Limit this Web workflow to reverse analysis, source reconstruction, and
   compile/build/link feedback. Do not run the game or begin portability work;
   preserve those as a local Codex handoff.

Workflow:
1. Read the committed repository instructions and its architecture, build,
   ledger, and test conventions before editing. Use bounded file reads, searches,
   result pages, and command-output pages. Preserve IDs and pagination state so
   the session can resume without dumping large outputs into chat.
2. Turn the objective into one bounded work packet. State the candidate
   functions/bytes/files, current evidence, unknowns, and the measurable stop
   condition. If authored boundaries or the denominator are not independently
   covered, do not call a percentage complete.
3. Use a registered analysis provider only after discovering its operation and
   input schema. Require target attestation. Treat names, types, boundaries,
   decompilation, xrefs, and disassembly as provisional source-hypothesis
   evidence with exactness_credit=none. Correlate them with committed source and
   preserve truncation or provider failure exactly.
4. Reconstruct maintainable, natural C or C++ that expresses the original
   program. Do not use inline assembly, embedded machine-code bytes, generated
   byte arrays, data masquerading as source, or an oracle-specific trick as a
   routine shortcut. If a genuinely irreducible construct requires an exception,
   stop and document the exact evidence and smallest proposed exception first.
5. Run feedback from cheapest and narrowest to broader: syntax/static checks,
   focused compile/unit checks, repository-native verification, then broader
   build checks that the source-only sandbox can actually support. A command exit
   code is not exactness. Page truncated stdout/stderr and report unavailable
   private targets or toolchains as unavailable, not passed.
6. Workspace edits and tests create a candidate diff only. They do not modify
   the canonical repository and cannot enter the Truth Kernel. Submit a replay
   only for a discovered claim already bound to canonical committed source;
   never replay or describe a disposable workspace diff as verified. For a
   replay, keep execution state, receipt verdict, and acceptance decision
   separate, and confirm success through an accepted-fact or accepted-snapshot
   query.
7. Prefer curated source, tests, ledgers, and durable explanatory documentation.
   Do not accumulate raw .analysis dumps, chat journals, duplicated decompiler
   output, or stale scratch artifacts in the diff.

Decision rules:
- Accuracy is more important than completeness. Unknown is a correct result;
  guessed identity, ownership, extent, provenance, equivalence, or exactness is
  not.
- Existing comments, ledgers, third-party references, and prior agent work are
  evidence candidates, not automatic truth. Check them against independent
  evidence and the strongest available oracle.
- A completed job is workflow state, a passing receipt is oracle state, and an
  accepted current registry entry is Truth Kernel state. Never collapse them.
- Continue within the bounded packet until STOP_CONDITION is met, a concrete
  evidence/tool boundary blocks it, or the remaining work would require a new
  scope decision. Do not repeatedly announce completion without satisfying the
  measurable condition.

Final handoff (always include every field):
- Session status: stop condition met | blocked | bounded progress
- Game and objective
- Baseline commit and canonical dirty-state observation
- Workspace ID and expiry
- Bounded scope completed and excluded
- Analysis evidence, provider, target attestation, and exactness limitation
- Changed files and rationale
- Tests actually run, exit/result, and unavailable checks
- Complete diff byte size and whole-diff SHA-256
- Accepted Truth Kernel facts, separately from candidate/workspace results
- Unknowns and blockers
- Next local action (normally review/apply the diff, then discover and replay a canonical claim)
- Proposed English commit message beginning with: gpt-web:

Do not claim that the canonical repository was edited, committed, pushed, or
verified unless the returned Factory evidence explicitly proves that exact act.
```

## Choosing a stop condition

A useful stop condition is bounded and observable, for example:

```text
The selected function has a natural-source candidate, the repository's focused
checks pass in the disposable workspace, the complete diff is exported, and all
remaining exactness/ownership questions are listed as unknown for local replay.
```

“Improve the reconstruction” and “reach 99%” are goals, not session stop
conditions, unless the repository already has a verified denominator and the
session names the exact measurable increment.
