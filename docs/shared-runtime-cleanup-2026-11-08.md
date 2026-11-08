# Shared runtime cleanup, 2026-11-08

This follow-up records installation cleanup after the
[0.9.0 shared runtime activation](shared-runtimes-validation-2026-11-08.md).
It is a point-in-time observation, not a continuing health certificate.
See [shared runtimes](shared-runtimes.md) for current operating instructions.

The live fourteen-repository registration was inspected before cleanup. The
Ghidra 12.1.3/12.1.4 and JDK copies consolidated during the preceding activation
were already links into Factory. No remaining Ghidra/JDK download archives or
standalone Wine distribution were found in the inspected game tool roots.
Directories named `wine`, `wine-msvc*` and `wineprefix-*` contained game-owned
prefix state and were preserved. The `msvc-wine` checkout is compiler helper
source, and legacy analysis-helper checkouts remain available where used.

One physical installation remained: TH105's legacy Ghidra 12.1, including its
additional bridge wheel. It had no active process users or embedded game
project/prefix state. The complete installation was moved into Factory's
ignored shared store and the old path replaced with a direct compatibility
link. All 6,694 manifest entries were checked before and after the move,
including file hashes, modes and symlink destinations. The directory inode and
all customized payloads were retained. The old path and an explicit installed
version selection through `scripts/shared_runtime.py` both start successfully.

Approximately 880 MiB of allocated installation storage moved out of the game
worktree. This was a relocation of a distinct legacy version, so it did not
reclaim additional global disk space. The preceding 4.72 GiB deduplication is
recorded in the activation report and is not counted again here. After cleanup,
no physical Ghidra/JDK/Wine installations remained in the inspected game tool
roots; their shared selectors resolve into Factory.

| Check | Before cleanup | After cleanup |
| --- | --- | --- |
| Local Ghidra/Java/Wine startup | 42 checks across 14 worktrees passed | 42 checks across 14 worktrees passed |
| Public repository Wine/Java and shared mounts | All 14 worktrees passed | All 14 worktrees passed |
| Public native analysis | All 17 registered providers passed | All 17 registered providers passed |
| Public discovery and TLS | Both explicitly resolved global relay peers passed | Both explicitly resolved global relay peers passed |
| TH105 native VC8 compilation | Passed with a source/output path containing spaces | Passed with a source/output path containing spaces |
| EFZ native compilation and complete extent comparison | 180 bytes and 8 relocations matched; changed-byte negative control rejected | Same comparison and negative control passed |

Public probes bypassed proxies and MagicDNS with explicit global peer addresses
and verified the actual TLS peer. Shared installations rejected writes in
repository shells, and all thirteen other registered source references stayed
readable from each game. Local launchers were exercised directly without
using MCP. After cleanup, the connected ChatGPT Factory tool also started the
retained legacy Ghidra and Wine successfully. The legacy TH105 version is retained for compatibility; default
runtime selections and native provider bindings were not changed.

Original target and shared executable/component hashes, tracked diffs,
untracked file contents, prefix/project identities and runtime configuration
were checked against the pre-cleanup snapshot. Private service configuration
was unchanged and the service required no restart. Targets, game projects,
Wine prefixes, compiler installations and reconstruction evidence were retained.
Detailed manifests and command results remain in ignored operator state.
