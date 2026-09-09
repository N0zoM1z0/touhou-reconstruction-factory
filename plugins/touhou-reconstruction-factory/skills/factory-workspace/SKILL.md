---
name: factory-workspace
description: Explore, modify, and test registered Touhou reconstruction source through a disposable Factory workspace. Use when the user asks GPT-web to inspect files, search code, draft or apply a source patch, run composable shell checks, or return a reviewable diff. Do not use workspace results as exact reconstruction evidence or claim they changed the canonical repository.
---

# Factory Workspace

Use the workspace provider as a source-development scratch space, not as an
oracle or deployment channel. It contains only tracked files from the selected
repository's committed `HEAD`. Local dirty changes, untracked files, ignored
targets, private toolchains, analysis databases, credentials, and the operator
home are excluded.

## Work

1. Call `factory_describe` and confirm that `workspace.enabled` is true. Call
   `factory_list_repositories` and select only a returned repository ID.
2. Call `factory_create_workspace` with a stable idempotency key. Retain and
   show the returned capability ID. Report `source_git_commit` and whether
   `source_worktree_dirty_observed` is true; a dirty observation means the
   workspace deliberately omits current local work.
3. Start by reading repository instructions and architecture files. Use
   `factory_workspace_list_files`, `factory_workspace_read_file`, and
   `factory_workspace_search` for bounded discovery.
4. Use `factory_workspace_apply_patch` for a precise text-only unified Git
   diff. Use `factory_workspace_run_shell` when composable Bash, tests, code
   generation, or several Unix tools are clearer. The shell may freely alter
   the disposable tree, but has no network or host authority.
5. Retain each returned command ID. If output was truncated, page both streams
   with `factory_get_workspace_command_output`. Distinguish a command's exit
   code from `workspace_committed`; timeout or an invalid final tree discards
   the complete command filesystem transaction.
6. Call `factory_get_workspace_status` after material changes. Finish by paging
   `factory_get_workspace_diff` until `next_offset` is null and preserve its
   whole-diff SHA-256.
7. Report the workspace ID, baseline commit, tests actually run, command exit
   states, diff SHA-256, and every limitation. The diff is a candidate for
   local review and application; it has not modified the canonical repository.

Use POSIX-relative paths only. Do not attempt symlinks, device files, Git
control-data changes, host-path discovery, or network access. Do not call
`factory_discard_workspace` unless the user asks to discard it or clearly says
the scratch work is no longer needed.

## Evidence boundary

A workspace test can support an engineering recommendation, but it cannot
produce an accepted `OracleResult`. The exact compiler, original target,
ignored toolchain inputs, and native analysis database are intentionally absent.
After a human or local Codex session reviews and applies the exported diff to
the canonical game repository, discover a supported claim and use the separate
factory replay workflow. If no canonical replay proves the requested extent,
report it as `unknown`.
