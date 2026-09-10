# Worktree recovery and analysis artifact lifecycle

## Why this is a required gate

GPT-web cannot reliably know whether the preceding conversation disconnected,
timed out, or left a half-completed command. Repository commands deliberately
persist their filesystem effects on nonzero exit, timeout, transport loss, and
conversation loss. Therefore a dirty worktree is not an inconvenience to route
around. It is possible recovery state and must be reviewed before a new batch
begins.

This policy is machine-readable in
[`worktree-recovery-and-analysis-artifacts-v1.json`](../contracts/worktree-recovery-and-analysis-artifacts-v1.json).
It applies even when ChatGPT does not load a bundled skill.

## Mandatory recovery review

Run the gate at every session start or resume, after an interrupted or timed-out
command, and whenever status changes unexpectedly. First record branch, HEAD,
upstream, and porcelain-v2 status. If the worktree is dirty, inspect the complete
staged and unstaged diffs, relevant untracked files, the latest durable handoff,
recent relevant commits, and any tests or manifests that explain the partial
work. Do this before selecting or editing a new batch.

Classify every relevant path:

| Classification | Required action |
|---|---|
| `recoverable-current-work` | Adopt it as the first batch. Understand and finish or narrow it, validate it, and checkpoint it before unrelated work. |
| `unrelated-preexisting-work` | Preserve it, exclude it from staging, and avoid tests or edits that rewrite it. |
| `generated-ephemeral-output` | Remove it only when producer, reproducibility, references, and inactive ownership are established. |
| `unknown-origin-or-intent` | Do not delete, reset, overwrite, or stage it. Avoid overlap or report a concrete blocker. |

Staged does not mean complete. Modification time does not prove provenance. A
`RESUME_COMMIT` is orientation, never authority to reset newer filesystem state.
Never use clean/reset/stash/delete or an indiscriminate commit as a substitute
for this review.

Record the paths, classifications, evidence, actions, retained unknowns, and
post-review status in the batch record or final handoff. If new concurrent
changes appear later, stop that batch at a coherent boundary and run the gate
again.

## `.analysis/` is a workspace, not a knowledge base

`.analysis/` is ignored, non-authoritative working storage. Old decompiler
exports, worktrees, logs, build trees, and runtime probes can be both large and
misleading. An artifact is only a lead until its source HEAD, target, analysis
database, tool version, and relevant command inputs are current or reproduced.
Neither keeping nor deleting it changes Truth Kernel status.

Use these classes:

- `session-scratch`: current campaign experiments, normally removed after their
  compact conclusions are retained;
- `reproducible-cache`: input-keyed outputs that may be regenerated;
- `durable-analysis-evidence`: an exceptional raw artifact with a tracked
  reference and a documented reason compact evidence is insufficient;
- `shared-provider-state`: reusable IDA/Ghidra databases, toolchains, and Wine
  prefixes managed by the operator, preferably outside `.analysis/`; and
- `legacy-unknown`: pre-existing or unmanifested content that is neither trusted
  nor automatically removed.

For a one-command experiment, use an OS temporary directory and clean it in the
same command. For a multi-command campaign, reuse one
`.analysis/gpt-web/<campaign-id>/` directory. Create `manifest.json` before the
first large output with the campaign/game identity, timestamps, starting and
current HEAD, state, and an artifact list. Each artifact records its path,
class, producer, real input binding, observed size, tracked references, and
cleanup disposition.

The default soft campaign budget is 256 MiB; 64 MiB is the large-artifact
threshold. These are review triggers, not destructive quotas. Crossing either
requires a reason and an explicit cleanup disposition. Prefer bounded analysis
queries over whole-program text exports, reuse the registered IDA/Ghidra
project, use configured Wine/provider state instead of copying a prefix, reuse
one worktree, and page command output instead of saving unbounded dumps.

At every checkpoint, measure growth since preflight. Move only compact durable
conclusions into tracked semantic evidence or game-local knowledge. Delete only
explicit current-session scratch paths whose ownership is established, whose
producer is no longer active, which are reproducible or no longer needed, and
which have no tracked or active reference. Retain only the smallest current
failure reproducer needed by the next batch.

Never bulk-delete `.analysis/`, delete by age alone, or remove unmanifested
legacy content, provider databases, toolchains, or Wine prefixes. An agent that
cannot prove an artifact's classification records it as `legacy-unknown` and
leaves it untouched for later operator review.

## Observed legacy footprint

A read-only inventory on 2026-09-10 found the following existing roots. No file
was removed or changed:

| Game | `.analysis/` size | Dominant observed content |
|---|---:|---|
| TH04 | 2.2 GiB | 1.3 GiB Wine/toolchain state and 784 MiB exact-unit replay trees |
| TH08 | 278 MiB | many repeated approximately 5 MiB semantic analysis directories |
| TH095 | 1.4 GiB | a 1.3 GiB legacy GDB/Wine-prefix experiment |
| TH105 | 511 MiB | repeated worktrees, disassembly exports, and GPT-web analysis trees |

These observations motivate the lifecycle but do not classify any individual
legacy directory as safe to delete. Migration should first identify active
provider state, tracked references, and reproducibility. New sessions must not
compound the legacy footprint while that audit remains pending.
