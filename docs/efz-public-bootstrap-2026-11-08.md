# EFZ public bootstrap, 2026-11-08

This records one completed deployment checkpoint. Re-query the live interface
before treating repository counts, availability or measurements as current.

## Registered inputs

- Repository `efz` selects the existing
  `Eternal-Fight-Zero-Reconstruction/Eternal-Fight-Zero` worktree.
- The canonical ignored input is `resources/EFZ.exe`, 3,743,744 bytes, SHA-256
  `3a1616d6c76d2eea08a95bb198d853e96cb6b9b3266e277ca1d167426dd66481`.
  Setup verified the file and the existing Ghidra project's complete mapped
  target bytes using the repository's own verifier.
- `windows-pe-inventory-v1` imports 950 provisional function rows. Missing
  release and region fields remain unknown; the native candidate-version text
  is retained as metadata. Native acceptance files are not Factory receipts.
- Provider `efz-ghidra` uses the existing EFZ project, shared Ghidra/JDK
  installations and standalone Factory query helpers. Its project locks,
  native build lock, Wine prefix and output remain EFZ-local.

## Exercised public workflows

An isolated fourteen-game candidate was tested through a temporary,
Factory-wide validation route. The production route retained its earlier
backend throughout staging. Direct probes selected both public relay IPs,
bypassed proxies and MagicDNS, verified TLS and checked the connected peer.

- Discovery and inspection exposed EFZ and its provider. An uppercase-filename
  target-ID mismatch was reproduced and fixed before production activation.
- Repository Python, canonical target, pinned compiler and existing Ghidra
  project verification succeeded through public Bash.
- A copied maintained source file and output path containing spaces compiled
  with EFZ's VC7.1 RTM compiler and Wine prefix. A complete 180-byte comparison
  with eight reviewed relocations had zero differences; a changed-byte
  negative control was rejected. Accepted objects, sources and ledgers were
  preserved; this smoke run created no new Factory acceptance fact.
- Eleven analysis calls covered metadata, decompilation, callers, callees,
  disassembly, references, function listing, strings and combined context.
  Instruction addresses resolved to their containing functions. A large
  decompilation retained all 115,595 bytes / 2,128 lines while returning a
  500-character preview; public Bash recovered and hashed the complete file.
- EFZ read every other registered source tree through read-only references,
  and all thirteen peers read the EFZ mount. TH09's active writer was allowed
  to finish before its reference and native IDA checks; TH10 native Ghidra also
  passed a regression query.
- Timeout retained partial output and writes. Reusing its command ID retrieved
  the timeout without executing again. A deliberate active-client disconnect
  exposed live logs and recovered the original result across relays, with one
  execution. Malformed analysis input did not prevent the next healthy query.

Fifty focused checks passed: six inventory, nineteen analysis, one standalone
provider, ten MCP-server and fourteen repository-work checks. EFZ's focused
whitespace CI and Factory `git diff --check` passed. No whole-game build or
full cold cohort was run.

## Activation

After staging passed, the same production hostname and route were switched to
the tested backend. The validation route was removed and other Funnel mappings
were preserved. Production probes passed EFZ status and combined analysis over
both public relays, EFZ live Bash and target verification, and nonblocking
status for all fourteen repositories. Existing connected Factory tools also
listed EFZ and successfully called its analyzer.

The probes retained 85 completed pinned-public JSON-RPC responses across
staging and production, including expected error cases. The idle prior MCP
backend was retired. The original replay worker, its configuration and replay
implementation fingerprint were retained. EFZ's selected native build/oracle
scripts remain available through Bash; no EFZ Factory replay driver or native
acceptance importer was added. The root push helper discovers fourteen
repositories from the active configuration automatically.

Private routes, service configuration, unit files and raw probe captures remain
in ignored operator state. EFZ's Factory-access instructions were checkpointed
locally; no repository was pushed during this task.
