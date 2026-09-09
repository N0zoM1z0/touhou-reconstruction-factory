# Disposable Workspace Provider

## Decision

The factory exposes a small set of repository primitives and an arbitrary Bash
tool inside a fixed isolation boundary. It does not expose host Bash and does
not attempt to predict every useful source operation as a separate MCP tool.

This is the composability/authority split:

| Surface | Caller can do | Caller cannot do |
| --- | --- | --- |
| Repository primitives | List, read, search, patch, inspect status, and page a diff | Name a host path or traverse a symlink |
| Workspace Bash | Compose installed Unix tools and change a disposable source tree | Reach the network, host home, canonical worktree, ignored files, evidence store, or job database |
| Replay jobs | Run registered factory drivers against the canonical repository | Select an arbitrary command or redefine success |
| Acceptance registry | Query receipt-backed facts | Promote a workspace result or caller assertion |

The workspace layer is deliberately useful without becoming a second truth
path. A command exit code or passing unit test is engineering evidence for a
candidate patch. It is not an `OracleResult`, receipt, or accepted fact.

## Snapshot contract

`factory_create_workspace` accepts a registered repository ID and an
idempotency key. Under the repository's shared factory lock, it records the Git
commit and tree at `HEAD`, observes whether the source worktree is dirty, and
extracts `git archive <recorded-commit>` into private service state.

The recorded commit is resolved first, its complete tree is preflighted for
file type and size, and that immutable commit ID—not a later moving `HEAD`—is
passed to `git archive`. The extracted file count must equal the preflighted
tree, while extracted bytes are remeasured after committed attributes such as
line-ending rules are materialized. This prevents a concurrent ref update,
export-ignore rule, symlink, or Git link from silently changing the advertised
snapshot.

Only committed, tracked content enters the snapshot. In particular:

- tracked local modifications are replaced by their `HEAD` versions;
- staged modifications that are not committed are excluded;
- untracked and ignored files are excluded;
- tracked symlinks, Git links, special files, oversized files, excessive file
  counts, and excessive total bytes fail workspace creation;
- the synthetic Git baseline contains only the extracted public source and is
  not the canonical repository's `.git` directory.

The response makes the omission visible through `source_mode =
"committed-head"` and `source_worktree_dirty_observed`. The Boolean dirty
observation does not disclose, copy, or characterize the omitted files.

Workspace IDs are random 128-bit capabilities. There is intentionally no
global workspace-list tool on the unauthenticated deployment. A caller must
retain its ID. Each capability has a configured expiry; expiry removes the
source and command payloads and leaves only a tombstone. `max_active` bounds
concurrent retained workspaces.

## Transactional Bash

`factory_workspace_run_shell` starts Bubblewrap with new user, mount, PID,
IPC, UTS, cgroup, and network namespaces. It mounts system programs, creates
empty `/etc` and temporary-home directories plus a minimal `/dev`, exposes the
current disposable source and
synthetic Git metadata read-only, and copies source into a size-bounded tmpfs.
The caller's script runs in that tmpfs with:

- no host `/home` and an empty temporary `HOME`;
- no network interface inherited from the host;
- no canonical repository, ignored target, private compiler bundle, analysis
  database, factory configuration, receipt store, or job database;
- no Linux capabilities, no interactive profile, and no Git credential
  prompting;
- process address-space, CPU-time, output, file-size, wall-clock, and workspace
  capacity bounds.

After the script exits, the service archives the tmpfs and extracts it into a
new host-side candidate using its own parser. Only regular files and
directories with safe POSIX-relative paths are accepted. The complete tree is
validated against configured limits and then atomically replaces the previous
disposable tree. A timeout, incomplete archive, symlink, hard link, special
file, or limit violation discards the entire filesystem transaction.

A nonzero script exit does not by itself discard a valid final tree. This
preserves normal shell semantics: a diagnostic command may fail after writing
useful source. The response therefore reports `exit_code` and
`workspace_committed` separately.

Command records and bounded stdout/stderr survive a client reconnect. The
workspace response returns recent command IDs, and output pages report both
captured and observed byte counts. Output beyond the configured bound is
discarded explicitly with `output_truncated = true`; it is never represented as
complete.

## Patch and handoff

`factory_workspace_apply_patch` accepts only a bounded text unified Git diff.
It rejects absolute or escaping paths, Git control data, binary patches,
symlink/Git-link modes, and ambiguous rename/copy metadata. Application occurs
against a copy, followed by the same tree validation and replacement rule.

`factory_get_workspace_diff` constructs a reproducible Git binary diff against
the immutable synthetic baseline. It returns bounded byte pages and the SHA-256
of the complete diff. That diff is the handoff object:

1. GPT-web explores, edits, and tests in the disposable workspace.
2. GPT-web returns the complete diff, its SHA-256, commands, and limitations.
3. A local Codex session or human reviews and applies the diff to the canonical
   game repository under that repository's own instructions.
4. Factory replay discovers a supported canonical claim and produces a bound
   receipt.
5. Only the acceptance registry may admit the result.

There is no remote “apply to canonical repository” tool. On a public endpoint
without caller authentication, such a tool would grant every Internet caller
the same write authority as the operator. A random workspace capability does
not authenticate the person who created it.

## Deliberate limits and residual risk

Bubblewrap is OS-process isolation, not a virtual machine or a proof against a
kernel vulnerability. The public no-auth profile should contain only
non-sensitive registered source and should be disabled when it is not needed.
Even with filesystem, process, time, and capacity limits, an unauthenticated
caller can consume the bounded workspace slots or compute budget. Authentication
is the real remedy for caller-specific availability and write authority.

Arbitrary Bash and private binary-analysis authority cannot safely share one
sandbox. If an original executable, IDA database, Ghidra project, or exact
compiler is mounted where arbitrary Bash can read it, Bash can copy it into
model-visible output. The separate
[`attested analysis provider`](analysis-provider.md) therefore exposes
target-bound, factory-allowlisted read queries and no native database writes.
Unsupported analysis remains `unknown`; it is not filled by mounting private
state into the source shell.

The persisted operational record shapes are normalized in
[`disposable-workspace.schema.json`](../schemas/v1/disposable-workspace.schema.json)
and [`workspace-command.schema.json`](../schemas/v1/workspace-command.schema.json).
They record resumable state; they are not Truth Kernel evidence schemas.
