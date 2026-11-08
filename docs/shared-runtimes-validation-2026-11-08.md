# Shared runtime activation, 2026-11-08

This is a point-in-time infrastructure validation record for Factory 0.9.0.
It is not a current health certificate or reconstruction acceptance receipt.
The operating procedure is [shared runtimes](shared-runtimes.md).

## Installed layout

All fourteen registered worktrees were attached: TH03, TH04, TH05, TH06, TH07,
TH075, TH08, TH09, TH095, TH10, TH105, TH11, TH20 and EFZ. TH08 web/mods were
not added. Their maintained local scripts and Factory's native Ghidra launcher
now use the same Factory runtime entrypoint.

Five physical Ghidra 12.1.3 installations and five JDK 21.0.12.1+1 installations
were compared entry by entry, including bytes, modes and symlink destinations.
Identical copies were consolidated under Factory's ignored shared store, with
old installation paths retained as links. This removed approximately 4.72 GiB
of duplicate payloads. TH09's distinct Ghidra 12.1.4 installation was retained
as another shared distribution. Existing compiler identities were preserved.
Wine was already a shared system installation; Factory now provides its common
entrypoint while retaining separate prefixes and their existing architectures.

Dedicated legacy prefixes were preserved. TH095's global user prefix binding
was replaced with a repository-owned prefix. TH075 also received an explicit
repository-owned selection. Ghidra Java homes, temporary files, settings and
caches were separated per game. TH09 successfully reused both its retained
12.1.3 and 12.1.4 databases after installation relocation; neither was imported
again. Its cache identity now distinguishes tool content without treating the
installation path as a new tool version.

## Observed checks

| Surface | Result |
| --- | --- |
| Local startup with primary MCP and replay worker stopped | All 42 Ghidra, Java and Wine startup/banner checks passed across fourteen worktrees |
| Direct local Ghidra projects | Maintained PC-98 frontend and eight PE frontends passed target checks; both retained TH09 versions exported one function with complete mapped-file verification |
| PC-98 installed-tool identity | TH03/TH04/TH05 Ghidra/JDK full installed-tree and component attestations passed without changing pinned hashes |
| Public transport | Both explicitly resolved global relay addresses completed verified TLS and MCP initialization as version 0.9.0, with proxies and MagicDNS bypassed |
| Connected ChatGPT Factory tool | EFZ shared Wine and Ghidra selection returned exit zero through the connected MCP app |
| Public repository runtime | Fourteen worktrees launched their selected Java/Wine tools and read all thirteen other source references; references and shared installations rejected writes |
| Public native analysis | All seventeen native providers returned bounded function listings; EFZ and TH10 also returned bounded function contexts |
| Public compiler use | Eleven PE repositories compiled ordinary probes through the shared Wine entrypoint, including paths containing spaces |
| Reconstruction-style EFZ probe | Native compilation produced a complete 180-byte, eight-relocation exact comparison; a changed-byte negative control was rejected; no acceptance credit was claimed |
| Recovery | Real Wine timeout, partial output, idempotent command retry, client disconnect and cross-relay recovery passed; subsequent Wine commands remained usable |
| Isolation | Foreign prefix rejection, independent repository caches/prefixes, same-repository serialization, independent repositories, concurrent first ownership and signal/lock recovery passed |
| Provisioning | Re-application retained installation selections, owner tokens and prefixes and used direct links visible in the sandbox |
| Factory release | Ruff, 216 unit/integration tests, bytecode, whitespace, document parsing, CLI imports and isolated 0.9.0 wheel build passed |
| Game tooling | TH04 CI (594 tests) and TH105 CI (1,034 tests) passed; focused PC-98 analysis/path tests passed |

The public probes used `curl --noproxy '*' --resolve` with explicit globally
routable peers, verified the actual peer address and TLS verification result,
and invoked the real MCP tools. Endpoint names, private routes, service
configuration and detailed transcripts remain in ignored operator state.
The tested service retained its existing public endpoint and route.

The upgrade changed only runtime mounts and per-repository Wine environment in
private service configuration. All other provider/replay configuration and the
replay implementation fingerprint stayed unchanged. The primary MCP and replay
worker were started again successfully. Local scripts require neither service.

## Validation limits and preserved work

TH05's optional full tooling run executed 371 tests and retained one failing
ASM totals assertion. The exact same failure was reproduced from an unmodified
archive of its committed HEAD: the test expects an older ledger total. That
unrelated exactness assertion was left unchanged. TH05's installed-tool
attestation, shared-path tests, local Ghidra and public compiler/provider checks
passed.

An optional broad TH03 unit-suite run was interrupted after roughly nine
minutes in the existing guarded-forwarder mutation test. It was not counted as
a passing full CI run. The affected analysis/path tests, full installed-tool
attestation, maintained local Ghidra target check and all four public native
providers passed. No full accepted reconstruction cohort was replayed.

A same-repository analysis request made during an infrastructure compiler shell
received the existing writer-busy response; retry after that writer completed
succeeded. Other repositories continued serving requests. This is repository
state protection, not a transport outage.

The original eighteen tracked TH09 edits, seven tracked TH105 edits, and three
untracked TH095 files were excluded from staging and retained. Tool payloads,
prefixes, projects, targets and private configuration were not committed.
