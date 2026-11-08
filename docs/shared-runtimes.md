# Shared runtimes

Factory owns one installed copy of each required Ghidra/JDK version and one
Wine entrypoint. Both native Factory providers and game-local scripts use the
same launcher. No running MCP service or network connection is required for
local use. Sharing tools does not share projects, Wine prefixes, compiler
profiles, targets, evidence, or reconstructed source.

## Use from a game repository

The maintained Ghidra and compiler scripts forward to the shared runtime.
Their existing arguments, target checks, project locks and build profiles stay
in the game repository. The direct entrypoint is also available:

```bash
./scripts/shared_runtime.py --describe ghidra
./scripts/shared_runtime.py ghidra -- /path/to/project Project -process game.exe -readOnly -noanalysis
./scripts/shared_runtime.py --ghidra ghidra_VERSION_PUBLIC --describe ghidra
./scripts/shared_runtime.py java -- -version
./scripts/shared_runtime.py --describe wine
./scripts/shared_runtime.py wine -- cmd /c ver
./scripts/shared_runtime.py winepath -- -w "$PWD/build/probe.obj"
./scripts/shared_runtime.py --prefix .analysis/probe-prefix wine -- cmd /c ver
```

Supply the normal Ghidra headless arguments, including the game's script and
project selection. Prefer existing repository scripts for everyday analysis;
the raw command does not replace their project lock or target attestation.
An explicit Wine prefix can be inside the selected repository, or its exact
operator-configured legacy prefix. Another game's prefix is rejected. Ambient
`WINEPREFIX` does not change the direct launcher's default. The compatibility
commands in `.tools/factory-bin` validate an explicit `WINEPREFIX`; maintained
shell scripts select their own repository's prefix before using them.

## Layout and isolation

| Location | Purpose |
| --- | --- |
| Factory `.factory/shared-tools/<distribution>` | One physical installation per locked Ghidra/JDK version |
| Factory `.factory/shared-tools/wine/bin` | Selectors for the shared system Wine components |
| Factory `runtime/run.py` | Common local and MCP launcher |
| Game `scripts/shared_runtime.py` | Tracked forwarding script; no service dependency |
| Game `.tools/factory-runtime.py` | Ignored link to the local Factory launcher |
| Game `.tools/shared-runtimes.json` | Ignored installation names, prefix, architecture and ownership token |
| Game `.tools/ghidra`, `.tools/jdk` | Compatibility selectors to the shared installations |
| Game `.analysis/factory-runtime/ghidra` | Separate Java home, temporary files, settings and caches |
| Game configured Wine prefix | Persistent game/toolchain-specific Windows state |

Ghidra/Java launch headlessly on one allowed CPU with lowered priority and a
768 MiB default headless heap; an explicit repository heap setting is retained.
Each game keeps its existing project and project lock. Existing tool versions
are retained: different locked versions may coexist in the shared store. Tool
hashes are not refreshed merely because an installation moved.

Wine launches serialize within each repository. The lock descriptor stays in
the short-lived launcher and is not inherited by persistent wineserver
processes. Different repositories may run independently. Prefix checks also
apply to `wineserver`; its control commands bypass the launch queue so `./scripts/shared_runtime.py wineserver -- -k` can recover a stuck process.
Ownership markers reject accidental reassignment to another game. Existing
dedicated prefixes are reused, including explicitly configured legacy external paths;
the global user prefix is not a default. Wine's inherited `TMPDIR`,
`WINELOADER` and `WINESERVER` overrides are cleared. Existing repository Xvfb
wrappers remain responsible for display-sensitive historical compilers.

Factory repository shells prepend the selected game's `.tools/factory-bin` to
`PATH`, mount shared runtime source/installations read-only, and mount only the
selected game's external prefix for writing. Other registered source worktrees
remain readable for cross-game reference. Do not mount another game's mutable
prefix or project for writing. Historical verifier recipes that explicitly
name system Wine still use that same system binary and retain their own
recorded prefix/profile; they do not justify a second installation.

## Provision and relocate

Inspect real Git/ignored state and stop active jobs before moving tool payloads.
Install or extract required, hash-verified versions once under the ignored
Factory shared store. For existing worktrees the provisioner can adopt their
installed payloads without downloads:

```bash
python3 scripts/provision-shared-runtimes.py --config /private/service.toml
python3 scripts/provision-shared-runtimes.py --config /private/service.toml \
  --prefix game=/private/game-owned-prefix --apply
```

The configuration argument can also come from `FACTORY_SERVICE_CONFIG`, or be
discovered from this checkout's running MCP process. The first invocation plans
only. All duplicate package entries are compared by path, content, mode and
symlink destination before consolidation. Distinct content is preserved for
review. One complete physical copy and its ignored migration manifest are
retained; retired duplicate paths become compatible links. No target, project,
prefix, compiler payload or analysis evidence is deleted.

The provisioner attaches every registered worktree, copies the small tracked
forwarder, and writes ignored local selectors. Re-running it preserves owner
tokens and configured prefixes. Re-run after moving the Factory checkout to
refresh links; this binding is a local installation locator, not a frozen
provider implementation hash. Review only the affected tracked game files.

For a new game, select its locked versions and dedicated prefix before
attaching. Do not download a Ghidra/JDK copy into every game or use the operator's
global Wine prefix. Add Factory `runtime` and `.factory/shared-tools` to private
`repository_work.shared_tool_roots`; set each registration's `WINEPREFIX` and
`WINEARCH`, and register an external prefix in that game's `work_state_roots`
only when necessary. Keep real paths, endpoint bindings and ownership tokens
out of public examples and commits. Restart the MCP after reviewed configuration
changes. Ordinary source reads and analysis calls do not run a full preflight.
