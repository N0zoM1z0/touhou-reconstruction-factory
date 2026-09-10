# Live Repository Work Provider

## Purpose

The live repository work provider gives GPT-web the same useful composition
surface that produced the earlier `gpt-web:` reconstruction history: one real
registered game worktree, broad Bash, repository-native tools, mutable build
state, Wine, and local Git commits. The provider adds durable observation and
stable repository selection; it does not replace the game's scripts with a
pre-enumerated workflow.

The repository ID is the only MCP-side selector. The caller cannot supply a host
path. The operator maps that ID to a canonical Git worktree and any transitional
tool/state mounts in private service configuration.

## Authority model

Repository work is intentionally powerful but has no truth-publication
authority:

| Result | Durable? | Exactness credit? |
| --- | --- | --- |
| Source edit or ignored build output | Yes, in the live worktree | None |
| Shell exit code | In the command record | None |
| Local Git commit | Yes, as a review checkpoint | None |
| Target-attested analysis result | In its analysis envelope | None |
| Factory replay receipt | Yes | Only its declared scope |
| Policy-accepted current receipt | Yes | Accepted scope only |

A command may edit tracked, untracked, and ignored files and may run `git add`
and `git commit`. It runs without a network namespace, so normal remote push is
unavailable. The Factory does not mistake that operational boundary for proof:
only the replay/acceptance path can add a fact to the Truth Kernel.

## Command semantics

`factory_repository_run_shell` accepts:

- `repository_id`: one registered game ID;
- `script`: 1 through 65,536 UTF-8 bytes of Bash;
- `relative_cwd`: an existing directory that resolves inside the worktree;
- `timeout_seconds`: a positive duration within operator policy.

Commands are serialized per repository and take the same Factory repository
lock used by replay, acceptance, analysis, and snapshot operations. This
coordinates all Factory-owned access, while ordinary local terminals and other
programs remain outside that advisory lock. Commands run non-transactionally. Edits and
artifacts survive a nonzero exit or timeout. This is necessary for normal
compiler diagnostics and investigation, but it means a retry must begin with
`factory_get_repository_status` and an inspection of the prior output.

Every command receives an opaque `repository-command:<id>`. Its durable record
contains script digest, timing and terminal state, exit/timeout state, captured
and observed output sizes, output truncation, before/after Git summaries, HEAD
relation, and any newly reachable commits. The initial response includes the
first output page; `factory_get_repository_command_output` resumes either stream
after disconnect. Output beyond the configured capture budget is explicitly
reported as truncated and never presented as complete. Truncation does not stop
the command.

The Git summary includes HEAD, branch, upstream/ahead/behind state, staged,
unstaged, untracked, and conflicted counts, plus a digest of complete porcelain
v2 status. Ignored files are usable even though Git does not enumerate them in
that summary. An advanced HEAD records new commit IDs and subjects; a rewritten
or divergent HEAD is reported without pretending to infer a safe commit list.

## Execution environment

Bubblewrap constructs a networkless process namespace with:

- the selected repository writable at its canonical path and `/workspace`;
- normal system programs and configured shared immutable tool roots read-only;
- explicitly configured game-bound state roots writable;
- an empty temporary home unless a game compatibility profile overrides it;
- a fixed local Git author and disabled credential prompting;
- no Factory evidence store, job database, or other registered repository.

This is a composition boundary, not a source-only sandbox. If the selected game
intentionally keeps a target, compiler, `.tools` bundle, or diagnostic database
inside its registered tree, GPT-web may use it. The evidence boundary remains
the target-attested analysis and accepted-receipt interfaces.

## Tool and state configuration

The preferred target layout separates immutable installation, tracked selector,
and mutable state:

```toml
[repository_work]
enabled = true
root = "state/repository-work"
command_timeout_seconds = 3600
max_command_output_bytes = 8388608
git_author_name = "N0zoM1z0"
git_author_email = "operator@example.invalid"
shared_tool_roots = [
  "/srv/touhou-factory/tools",
  "/srv/touhou-reconstruction-factory/contracts",
  "/srv/touhou-reconstruction-factory/docs",
]

[[repositories]]
id = "th09"
path = "/srv/reconstruction/th09"
adapter_id = "windows-pe-ledgers-v1"
target_identity_ids = ["target:th09-main"]
reference_repository_ids = ["th08", "th095"]
work_environment = { WINEPREFIX = "/srv/touhou-factory/state/th09/wine" }
work_state_roots = ["/srv/touhou-factory/state/th09/wine"]
```

`shared_tool_roots` are Factory-wide read-only installations. A tracked game
profile or wrapper chooses an exact tool/version and records its content
identity. `work_state_roots` are mutable and bound to one repository. Environment
values and host paths are redacted from discovery responses; only names and
counts are public.

`reference_repository_ids` is a per-game allowlist of other registered live
repositories. Their current trees and Git history are mounted read-only at
their canonical paths only inside the selected repository's shell. This makes
adjacent-game source available for composable searches without granting writes
or silently exposing every game to every session. References are hypotheses,
not evidence: prefer committed reference content, record its HEAD and dirty
status, then confirm all accepted facts against the selected game's own target,
analyzer, compiler, and Oracles. A reference under active semantic
reconstruction is explicitly provisional.

Mounting the Factory `contracts/` and `docs/` directories through the same
read-only mechanism lets standalone GPT-web prompts name exact guidance paths.
This is deliberately independent of ChatGPT skill injection: the app may expose
MCP tools while a skill is unavailable or not selected. The prompts still carry
their complete operating rules inline for deployments that have not mounted the
guidance paths.

The TH04/TH08/TH095/TH105 registrations retain legacy layouts so
work can proceed before migration. TH08 maps its historical `~/.wineth08` home,
TH095 maps its historical `~/.wine` prefix, and TH04/TH105 use repo-local
prefixes. These are accurate bridge profiles, not the target format. New games
should use a game-bound state root from the beginning. TH09 is the first clean
instance: its repo is registered directly with the shared Factory MCP and its
IDA provider is Factory-owned rather than copied into the game. Existing games
can be migrated one at a time after historical replay parity is demonstrated.

## Checkpoint workflow

1. Read the game instructions, current Git status, recent history, and relevant
   game-local knowledge.
2. Use target-attested IDA/Ghidra reads and Bash freely to investigate.
3. Make a small natural source change and run the strongest available build or
   comparison checks.
4. Review the complete diff and status. Do not stage unrelated existing work.
5. Commit one coherent English checkpoint with a `gpt-web:` subject.
6. Record what passed, failed, or remains unknown; do not push.
7. Submit a supported replay only when the claim and committed inputs are ready.

The exact GPT-web input contract and stopping rules are in
[`gpt-web-reconstruction-session-v4.json`](../contracts/gpt-web-reconstruction-session-v4.json)
and [`gpt-web-reconstruction.md`](../prompts/gpt-web-reconstruction.md). The
durable operational record is normalized by
[`repository-command.schema.json`](../schemas/v1/repository-command.schema.json).
