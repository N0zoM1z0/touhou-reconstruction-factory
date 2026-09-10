# TH095 semantic reconstruction start

Use this reference only for repository ID `th095`. Live repository state and
the canonical TH095 documents override every dated observation below.

## Entry point

Commit `339bb5a` declares semantic reconstruction as TH095's next phase after
function reconstruction, production closure, owner repair, and Windows i386
runtime testing. Read at least:

- `AGENTS.md`;
- `docs/RE_HANDOFF.md`;
- `docs/ARCHITECTURE.md`;
- `docs/RE_WORKFLOW.md`;
- `docs/SEMANTIC_RECONSTRUCTION.md`;
- `docs/OWNER_AUDIT.md` and `docs/RUNTIME_ISSUES.md` when ownership/lifetime is
  in scope; and
- the complete relevant source, ledgers, and match-unit definitions.

Run the live preflight:

```bash
python3 scripts/verify-target.py
python3 scripts/report-reconstruction-status.py --summary
python3 scripts/validate-tracking.py --require-target
python3 scripts/ghidra.py check
```

The 2026-09-10 orientation baseline was 697 source-present authored functions,
696 exact functions, 336,486 exact bytes, 88 production source files, and two
production profiles. Target-attested Ghidra passed the executable identity and
six mapped byte samples. These values are not semantic evidence and must be
replaced by live command output in the session handoff.

This ordering is a prerequisite, not incidental history. The exact replay lane
and reconstructed Windows i386 product/runtime lane are the two independent
semantic regression oracles. Preserve both throughout the phase. Windows
x86-64, Linux, and Web products begin only after semantic readiness and cannot
stand in for the i386 owner/runtime baseline.

The same dated worktree contained four pre-existing untracked experiment files.
Because Web cannot know whether a prior conversation disconnected, any current
dirty/untracked state requires the full recovery review before a new semantic
batch. Inspect its complete diffs/content, handoff/history, tests, and manifests;
classify every path and adopt recoverable partial work as the first batch. Do
not stage it with a semantic batch unless its purpose and inclusion are
independently established.
If it prevents Factory replay eligibility, use repo-native checks and report the
receipt plane as unavailable for that worktree; never delete work merely to make
a receipt green.

## Campaign routing

On a fresh semantic history, begin with:

```text
factory_report_semantic_debt(
  repository_id="th095",
  relative_path="src",
  category="all",
  limit=100,
  offset=0
)
```

Follow `next_offset` only as needed to compare promising files. Supplement the
lexical report with `rg`, mappings, match-unit definitions, target-attested
Ghidra xrefs/decompilation/disassembly, and relevant TH08 source/history.

When one or more semantic batches are already committed, first read the latest
entry and its named next batch. Continue from it when current TH095 evidence
still supports the choice; do not repeat a completed family merely because this
reference describes the original entry point. Choose another small
high-evidence canonical-owner or field family after each checkpoint. Avoid the
largest ECL interpreter, a persistent score/replay/archive redesign, or an
anonymous-field sweep until prior bounding makes that scope coherent. TH08 is
workflow and corroboration only; require TH095-local evidence for every
accepted interpretation.

## Native regression commands

Use one or more manifest source selections for the smallest affected exact
scope:

```bash
python3 scripts/replay-exact-units.py --source <manifest-source>
```

Run the no-argument cold aggregate replay after shared layout, header, PCH,
inline, owner, or other cross-object changes:

```bash
python3 scripts/replay-exact-units.py
```

The production gate is:

```bash
python3 scripts/build-whole.py
```

Close target-independent repository maintenance with:

```bash
python3 scripts/ci.py
git diff --check
```

Run the smallest applicable format or runtime check when the batch changes
serialization, ownership, lifetime, initialization, callbacks, persistence,
rendering, input, or audio. Manual/runtime evidence remains engineering feedback
until a deterministic target-bound Factory runtime provider exists.

Append a completed entry to `docs/SEMANTIC_RECONSTRUCTION.md` only after the
batch's applicable checks pass, then create one focused local English
`gpt-web:` checkpoint. Refresh the live state and immediately start the next
named batch unless a campaign terminal condition is real. Report exactness,
product closure, runtime storage, and runtime scenario planes independently.

Use repository-native checks for the rapid inner loop. Do not cold-replay the
entire accepted Factory receipt set after every private checkpoint when another
planned source commit would immediately stale it. Close current-source Factory
receipts at a meaningful campaign milestone; shared owner/layout/header changes
still require their broad cold exact and product gates immediately.
