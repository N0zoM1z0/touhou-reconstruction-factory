# TH04 exact reconstruction

Paste this standalone prompt with the shared Factory app selected.

```text
Contract: gpt-web-reconstruction-session-v6
GAME_ID: th04
OBJECTIVE: Continue natural-source exact reconstruction.
Provider: th04-ghidra; target: target:th04-main.
Repository: /home/pentester/coding/codex_ida/th04-reconstruction/th04
Target: .analysis/targets/th04/main.exe
Platform: PC-98 16-bit MZ/OMF; preserve segments, far calls/returns and RETF.

Communicate in Chinese; write source, notes and commits in English.
Prioritize exact reconstruction and reusable knowledge with minimal overhead.
These current user requirements override older broad CI, repeated preflight,
document-hash, source-pin and reporting instructions.

Read the selected repository's AGENTS.md and short current handoff. Search only
knowledge relevant to the task. The common guide is
/home/pentester/coding/codex_ida/touhou-reconstruction-factory/docs/agent-autonomy.md
and shared tools are documented in that Factory's docs/shared-runtimes.md.
If a guidance path is unavailable, continue using these complete inline rules.

Use broad repository Bash, existing local tools and bounded IDA/Ghidra queries.
Preserve dirty, untracked and useful ignored work. Analyze, edit natural source,
compile and compare the complete affected scope including relocations, record
useful learning and checkpoint coherent work. Recheck known affected consumers
when changing shared inputs. No fixed packet count or extra workflow machinery.

Ordinary Markdown, knowledge and handoff edits need diff review only. Do not
run a compiler, analyzer, full CI or cold replay for those edits. Do not bind
exact freshness to prose, Git metadata or manual handoff source-SHA tables.
Documents genuinely consumed by a build remain executable inputs. Tool changes
need meaningful affected tests; broad suites require an explicit request or a
stated impact that cannot be narrowed. A passing quick CI check is not exactness.

Do not add tests for prompt wording, prose hashes, progress totals or ordinary
source spelling. Do not add frameworks, schemas, registries, state machines,
generalized validators or reporting processes for a local task. Use the
smallest existing command or focused fix that addresses an observed need.

Write documentation and knowledge in fluent, natural English. State the finding,
evidence and next action directly. Remove filler, circular restatements,
repeated conclusions and unnecessary jargon. Avoid defensive-claim boilerplate;
state a genuine uncertainty or scope limit once when it affects a decision.

Plain Markdown knowledge is sufficient: finding, applicable scope, evidence,
useful failed attempts and open questions. No mandatory JSON conversion or
promotion. Read other registered games through read-only references when useful;
verify scope before transferring a lesson. Keep counts in canonical ledgers,
and handoff focused on current work, blockers, evidence and next action.

Preserve target/toolchain identity, readable natural source, full owned extents,
strict byte comparison and relocation checks. Analysis, knowledge, builds and
Git alone confer no exact credit. Preserve historical receipts without hash
refreshes. Reuse Factory tools while keeping prefixes, projects and caches
separate. Discover operations before calling an analyzer. Retain recoverable
output for interrupted commands. Make coherent local commits; do not push from
Web. Do not claim wider reconstruction completion from bounded success.
```
