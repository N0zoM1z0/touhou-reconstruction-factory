# Live Repository Work Provider

> Highest-priority current workflow: [lightweight agent work](agent-autonomy.md).
> Prefer affected exact checks and useful Markdown knowledge. Ordinary notes
> require no full CI, native replay, schema conversion or document-hash refresh.
> Older broad workflow/validation requirements are superseded by that policy.

Use the [shared runtime procedure](shared-runtimes.md) for Ghidra/JDK/Wine.
Game scripts and native Factory providers use the same Factory-owned launcher;
keep Wine prefixes, Java settings/cache and analyzer projects game-bound.
Attach existing locked versions instead of installing a copy in every game.

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
| Exploratory analysis result | In its analysis envelope | None |
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
- `timeout_seconds`: a positive duration within operator policy;
- optional `command_id`: `repository-command:` followed by 32 lowercase hex
  digits, chosen before sending a request that may need recovery.

Commands are serialized per repository and take the same Factory repository
lock used by replay, acceptance, analysis, and snapshot operations. This
serialization starts in an asynchronous per-repository MCP queue: pending shell,
status and semantic-debt requests do not occupy execution threads
while another request owns that worktree. A backlog for one game therefore does
not exhaust the shared thread pool or stall another game's work or discovery.
File locks continue to coordinate separate MCP instances and workers. This
coordinates all Factory-owned access, while ordinary local terminals and other
programs remain outside that advisory lock. Commands run non-transactionally. Edits and
artifacts survive a nonzero exit or timeout. This is necessary for normal
compiler diagnostics and investigation. Inspect prior output and the live
worktree before deliberately executing the work again.

With a caller-chosen `command_id`, retry identical arguments after a lost
response, including a disconnect while queued. The original execution either
runs or returns its retained result; it is never repeated for that ID. The
response sets `reused_existing_command=true` when returning a retained result,
with its original timestamps and Git snapshots. This retrieves an execution,
not a fresh build against subsequent source edits. Use a new ID for new work.
Changing the script, cwd argument, or timeout under an existing ID reports a
conflict. A timed-out command is recovered as timed out, without repeating its
partial writes. An interrupted execution requires output/worktree inspection
and an explicit new ID before executing again. IDs and records are scoped to
one repository. Ordinary calls can continue to omit the ID.

Every command receives an opaque `repository-command:<id>`. Its durable record
contains script digest, timing and terminal state, exit/timeout state, captured
and observed output sizes, output truncation, before/after Git summaries, HEAD
relation, and any newly reachable commits. The initial response includes the
first output page; `factory_get_repository_command_output` resumes either stream
after disconnect. If the response containing the command ID was lost, query
`factory_get_repository_status`: `recent_commands` lists the five most recently
recorded commands with IDs, timing and last recorded states. Set `include_git=false`
to retrieve these records while a writer is active, without waiting for its
worktree lock or requesting a Git snapshot. Output beyond the configured capture budget is explicitly
reported as truncated and never presented as complete. Truncation does not stop
the command. UTF-8 pages may include up to three extra bytes to finish their
last character; follow `next_offset`. Invalid or binary bytes remain base64.
Completed captures are immutable Factory files: reading them does not wait for
a new compiler or other work in that repository. Running captures are also
readable: `command_finished=false`, `command_state=running`, and
`observed_size=null` until final counts are available. Follow `next_offset`;
if it is unchanged, wait briefly before polling again. An incomplete trailing
UTF-8 character stays for the next poll. Once the command finishes, a null
`next_offset` ends that captured stream. An orphaned running record can still
be marked interrupted after its writer releases the lock; its observed total
remains unknown. None of these states establishes successful reconstruction.

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
- no Factory evidence store or job database; other registered repositories are
  mounted read-only for cross-game source reference.

This is a composition boundary, not a source-only sandbox. If the selected game
intentionally keeps a target, compiler, `.tools` bundle, or diagnostic database
inside its registered tree, GPT-web may use it. The evidence boundary remains
explicit target comparison and accepted-receipt interfaces.

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
work_environment = { WINEPREFIX = "/srv/touhou-factory/state/th09/wine" }
work_state_roots = ["/srv/touhou-factory/state/th09/wine"]
```

`shared_tool_roots` are Factory-wide read-only installations. A tracked game
profile or wrapper chooses an exact tool/version and records its content
identity. `work_state_roots` are mutable and bound to one repository. Environment
values and host paths are redacted from discovery responses; only names and
counts are public.

Every other registered repository is automatically mounted read-only at its
canonical path and `/references/<repository_id>`. Discovery returns all current
`reference_repository_ids` and `reference_repository_mounts`; adding a game
requires no pairwise reference lists. Historical lists in private configuration
are ignored. Only the selected repository is writable.

For example, any registered game can read
`/references/th04/src/shared/math/vector.cpp` and inspect TH04's Git history.
References help form hypotheses; confirm target-specific conclusions through
the selected game's own source and focused comparison when needed.

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
TH10 is the corresponding first clean Factory-native Ghidra instance, with a
shared hash-pinned Ghidra/JDK installation and a game-local ignored analysis
project.

## Checkpoint workflow

1. Read the game instructions, current Git status, recent history, and relevant
   game-local knowledge.
2. Use repository-selected IDA/Ghidra reads and Bash freely to investigate.
3. Make a small natural source change and run the strongest available build or
   comparison checks.
4. Review the complete diff and status. Do not stage unrelated existing work.
5. Commit one coherent English checkpoint with a `gpt-web:` subject.
6. Record what passed, failed, or remains unknown; do not push.
7. Submit a supported replay only when the claim and committed inputs are ready.

The exact GPT-web input contract and stopping rules are in
[`gpt-web-reconstruction-session-v5.json`](../contracts/gpt-web-reconstruction-session-v5.json)
and [`gpt-web-reconstruction.md`](../prompts/gpt-web-reconstruction.md). The
durable operational record is normalized by
[`repository-command.schema.json`](../schemas/v1/repository-command.schema.json).

## Operator push helper

From the Factory checkout, publish the current branch of each registered game:

```bash
source ~/clash.sh
proxy_on
./push-all-repos.sh
```

The script inherits exported proxy, Git authentication, and SSH environment
settings. It does not source a proxy configuration or change proxy settings.
HTTPS Git remotes use the caller's proxy environment; SSH remotes use the
caller's SSH configuration. Python 3.11+ and Git are sufficient.

By default it reads the service configuration from this checkout's running
Factory MCP process. Override this with `--config <service.toml>` or
`FACTORY_SERVICE_CONFIG`, including when the service is stopped or multiple
different configurations are running. Registered paths may be absolute or
relative to that TOML file; the repository list is never hardcoded.

The executable root launcher forwards all arguments to
`scripts/push-registered-repos.py` and also works when invoked by its path from
another directory.

Use `./push-all-repos.sh --dry-run` to contact the remotes and
check pushes without changing remote refs. The current branch uses its push
remote, then `remote.pushDefault`, then its upstream remote, falling back to
`origin`. An upstream on that remote keeps its configured destination branch;
otherwise the destination has the local branch name. Only that branch is pushed.
Uncommitted work is preserved. Divergence and other Git errors leave that repo
for manual resolution while the script continues with the rest, lists failed
repository IDs, and exits nonzero. It does not commit, merge, rebase, or force
push. The Factory checkout itself is included only if explicitly registered.
