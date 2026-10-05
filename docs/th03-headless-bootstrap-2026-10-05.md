# Recorded TH03 headless bootstrap and hot deployment, 2026-10-05

This is a dated validation record, not a live service inventory or a game
completion claim. Query the current Factory before relying on availability.

## Repository and tools

TH03 adopts the shared PC-98 adapter contract as `th03-pc98-v1`. The four
Japanese targets are OP, MAIN, MAINL and ZUN; optional cross-game controls
are excluded from progress. Maintained source and exact-unit ledgers start
empty. Target provenance remains `candidate-local-attested` and release
version remains unknown.

TC4J/TASM/TLINK required surfaces and Ghidra/JDK identities are inherited
from the pinned TH04 candidate. TH03 has its own physical installations,
Wine prefix and four analyzer projects. Compiler probes and all analyzer
invocations are headless. The native command provider independently checks
MZ disk structure and compares a same-process, nonce-bound full database
attestation before returning read-only query output.

The staged registration adds repository `th03` and providers `th03-ghidra`,
`th03-op-ghidra`, `th03-mainl-ghidra`, `th03-zun-ghidra`. Each exposes the
same ten bounded Ghidra operations. No game-specific HTTP bridge was added.
Exact TH03 replay is unavailable until a dedicated extent/source driver exists.

## Observed checks

- TH03 portable tests: 58 passed. Its private CI also passed required tool
  probes, all four live database checks and adversarial database mutations.
- Factory release validation: 164 tests passed, Ruff and whitespace checks
  passed, tracked documents parsed and an isolated wheel built successfully.
- Native adapter parity: 30 comparable metrics agreed. Unknown function
  denominators outside the MAIN ledger were retained as unknown.
- All four native providers passed real function-list queries through the
  staged loopback MCP. Their observations retained zero exactness credit.
- The unchanged public Factory URL returned seven repositories and the same
  33 tools with byte-identical tool metadata. A public TH03 native query and
  existing-project status query passed after the proxy switch.
- A public TH03 repository-shell command compiled, assembled, linked and
  executed the Borland probes, returned exit 0 without timeout and preserved
  game HEAD and visible source state.

## Deployment boundary

A new shared Factory instance was started on an unused loopback port and
validated before changing only the existing Tailscale route's upstream.
The earlier MCP process and replay worker retained their original PIDs and
were neither restarted nor drained. Their private configuration was unchanged.
The new service was enabled for future boots. Operator paths, bindings, port,
route backup and detailed validation results remain under ignored private
state and user-service configuration.

No existing-game compiler, source, target or analyzer database was changed.
Existing repositories remained discoverable; unavailable IDA databases were
not opened or switched as part of this deployment.

## Explicit residual

The TH03-local pinned ReC98 cold build reproduced all 20 known EXE/COM hashes
and their comparison vectors; all 416 OMF objects were structurally valid.
The imported calibration gate still failed the dependency-normalized object
set identities for all five games. Its cause remains unresolved and the
imported expected hashes were preserved. This observation does not establish
object reproducibility, reconstructed product closure or any exact unit.
