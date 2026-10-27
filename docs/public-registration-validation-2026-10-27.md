# Recorded public registration validation, 2026-10-27

This is a dated deployment observation, not a continuing availability promise
or an exactness claim. Private bindings, addresses, command transcripts and
full reports remain in ignored operator state. The checked implementation
checkpoint is `14b32be`; the later documentation checkpoint adds this record
and two compiler-family regression cases.

The existing public Factory route now discovers these thirteen main repository
IDs: `th03`, `th04`, `th05`, `th06`, `th07`, `th075`, `th08`, `th09`, `th095`,
`th10`, `th105`, `th11`, and `th20`. The six added IDs are TH05, TH06, TH07,
TH075, TH11 and TH20. TH08 web/mods checkouts were explicitly excluded by the
operator. No additional public game endpoint was created.

## Reproduced failures and repairs

The initial public audit passed status, imports and basic Python calls for the
seven existing games. Five analyzer checks failed:

- all four TH03 providers rejected their stale implementation binding;
- TH09's stdio bridge still depended on a stopped GUI RPC server.

The TH03 code review identified removal of already-retired download-archive
checks in `scripts/lib/analysis.py`. Installed-tree, tool execution and target
database checks remained in place. The reviewed private implementation hashes
were refreshed; all four databases passed fresh MZ attestation and queries.
TH09 moved to the maintained headless IDAlib helper with a separate private
input and database. Its staged input matched the canonical repository target.

The added games have differing native contracts. TH075 uses the existing
Windows ledger adapter. TH05 imports only its target/toolchain manifests;
TH06, TH07, TH11 and TH20 import provisional PE inventories. These limited
imports explicitly grant no native acceptance, exactness or source-presence
claims. Their headless analysis providers independently attest target bytes
and query the correct game-bound databases. The repository-provider wrapper
translates existing PE success markers without changing their fields, and
performs MZ attestation and queries in the same read-only process.

The first expanded public matrix also exposed unavailable TH105 and TH20
repository Python interpreters inside the shell sandbox. Their virtual
environments linked to external runtime installations. The compatible private
configuration now mounts the required uv runtime and Conda `bin`/`lib`
directories read-only. Both repositories' own interpreter selectors then
passed, including their pinned dependency checks.

An additional native target-verifier smoke found that TH20's ignored
`resources/th20.exe` was a symlink outside the checkout. The shell sandbox
correctly could not follow it. It was atomically replaced by a repository-local
regular file with the same manifest size and SHA-256. The original symlink
record was retained privately and the supplied source was untouched. TH20's
selected Steamless identity was preserved. The target verifier and complete
TH20 public shell/analysis checks passed afterward.

## Public transport and call evidence

`scripts/validate-public-mcp.py` obtained two global IPv4 relay addresses from
external DNS-over-HTTPS. It bypassed every HTTP proxy for MCP requests, pinned
each destination with `curl --resolve`, retained hostname/SNI and normal TLS
verification, and required the actual peer IP to match the selected relay.
Neither initialization nor any game call used MagicDNS or a tailnet address.

Both public addresses passed TLS, MCP initialization, discovery of all 33 tools
and discovery of the exact thirteen-repository inventory. The full public
matrix completed 103 requests with 68 passing checks and zero failed checks:

- status and adapter inspection for all thirteen repositories;
- each repository's harmless Python shell, unchanged before/after HEAD and
  status digest, and retrieval of the persisted command output;
- discovery and a real function-list query for all sixteen analysis providers,
  preserving target identity, successful attestation and zero exactness credit.

All six added repositories additionally passed their target-verifier smoke
through the public repository shell. TH20's seven public calls were
repeated after target localization. Complete command/error output, the initial
failures and successful reruns remain available in private reports. These
observations verify public MCP calls, not a refreshed ChatGPT connector cache
or a particular browser conversation.

## Activation and scope

The candidate was validated separately before switching only the upstream of
the existing public route. All 33 tool definitions matched the original
inventory. Other Funnel mappings, the original MCP processes and the original
replay worker remained unchanged and running. The expanded service is enabled
for subsequent user-service startup. Config-only Python mount repairs were
hot-reloaded without restarting it.

Inventory-only imports live outside the replay adapter registry. Every file in
the replay runner's implementation fingerprint remained byte-identical to the
prior checkpoint. The public server explicitly retains the original worker's
configuration binding and six-game replay registration. New repository shell
and analysis availability does not establish new replay-driver support; no
whole-game build or exact campaign was run for registration.

Repository source state was preserved, including TH095's three existing dirty
entries and the existing unpushed TH20 commits. Private configuration, targets,
databases and reports were not staged. The portable release validation passed
187 tests, Ruff, bytecode compilation, document parsing, CLI help and isolated
wheel packaging. Changes were committed locally without pushing.
