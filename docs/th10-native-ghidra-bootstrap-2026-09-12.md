# TH10 Factory-native Ghidra bootstrap

> **Historical measured record.** This document preserves the 2026-09-12 TH10
> bootstrap and Factory 0.7.0 activation evidence. Its counts, hashes, provider
> observations, and service state remain valid only for their named artifacts
> and checkpoint; query current repository and service state before reuse.

## Result

TH10 is the first new reconstruction whose Ghidra path is owned end to end by
the Factory contract. It uses the same shared Web-facing MCP as every other
game. No `mcp_for_gptweb` checkout, game-specific HTTP bridge, public endpoint,
or game-specific connector is present.

The public repository is `N0zoM1z0/th10`; its local registered path is
`th10-reconstruction/th10`. Private paths and endpoint material remain only in
operator configuration.

## Target identity

The selected file is the original Japanese TH10 v1.00a executable, not either
localized executable found beside it:

| Observation | Value |
| --- | --- |
| Size | `487936` |
| SHA-256 | `2f14760b6fbbf57549541583283badb9a19a4222b90f0a146d5aa17f01dc9040` |
| MD5 | `7dc488d82c81dd4aee4ba098b8804d83` |
| Format | PE32 i386, relocations stripped |
| Image base | `0x00400000` |
| Entry point | `0x004537DC` |
| Image size | `0x0009C000` |
| PE timestamp | `2007-08-02T20:21:36Z` |
| PE linker | `7.10` |

The version classification is pinned to thcrap's version database at commit
`f08b582ce57bce800955dd371fc9a68dbad5b324`. The Rich stream contains 232
build-6030 records across product IDs 15, 90, 95, 96, and 100. Product IDs 95,
96, and 100 specifically record 131 normal C, 15 normal C++, and 52 LTCG C++
inputs. That establishes a mixed VC7.1 SP1-generation build rather than a
uniform standalone-COFF model. Per-unit flags and ownership, translation-unit
partition, libraries, the production resource graph, and link order remain
unknown.

## Compiler feedback-loop completion

The same-day follow-up pins the operator-supplied
`archaic-msvc/msvc710_sp1` checkout at commit
`cf62606064633dd8441aa2feffe34792099cc366`. The Factory manifest locks the
compiler, both language frontends, optimizer, linker, PDB backend, resource
compiler, and resource converter individually. The selected compiler and linker
report build 6030, independently corroborating the target's observed
generation. The upstream checkout declares no license, so neither Factory nor
TH10 redistributes it.

The payload is immutable and shared; TH10 owns its ignored selector, win32 Wine
prefix, wrappers, build outputs, and evidence. The repo-local verifier always
uses Xvfb and exercises normal C COFF, normal C++ COFF, C++ `/GL` LTCG,
resource compilation, and a linked PE32 i386 image. This establishes a usable
headless feedback loop, not a target codegen or product-closure result.

The target's mixed inputs forced an explicit Oracle boundary. TH10's first
controlled replay driver accepts only a manifest unit that explicitly declares
`artifact_kind = "coff"` and has no `/GL` flag. LTCG candidates stay unknown
until a linked-image extent Oracle can bind their physical ownership. This is a
bootstrap invariant for future games: identify, pin, provision, and execute the
historical compiler path before advertising an exact campaign as ready, while
refusing to convert a successful smoke into target truth.

## Tool and project ownership

Ghidra 12.1.3 and Temurin JDK 21.0.12.1+1 are hash-pinned in private
Factory-managed storage. Existing identical TH095 payload files were hard-linked
into that store to avoid another full installation copy. TH10's ignored
`.tools/ghidra` and `.tools/jdk` paths are selectors, not private payloads to
commit. Its mutable database is isolated at ignored `ghidra-project/TH10`.

The first target-attested headless import completed in 65 seconds and exported
1,195 provisional candidates. Every candidate started `unknown/review`; source,
implemented, match, and accepted-result counts all remained zero. Ghidra's
boundaries and auto-names received no authored or exactness credit.

## Native provider contract

Factory 0.7.0 adds `attested-ghidra-command-v1`. Private registration selects:

- repository `th10`;
- target `target:th10-main`;
- provider `th10-ghidra`;
- the repo-local fixed-grammar `scripts/ghidra.py` wrapper; and
- the ignored canonical `resources/th10.exe`.

Discovery executes a real read-only `check` before returning ten bounded
operation schemas. Each analysis call performs its target/project attestation
and requested query in the same headless process. The Factory independently
reads the private PE and compares SHA-256, MD5, file size, image base, image
size, entry point, and six distributed mapped `.text` samples against the
marker emitted by Ghidra. Mismatch, missing marker, timeout, or missing query
output fails closed.

The private registration also binds the aggregate SHA-256 of the target/tool
manifests, Python wrapper and validators, and all Ghidra Java scripts. This
prevents mutable repository provider code from silently self-certifying after a
Web edit. Such edits remain allowed, but native analysis becomes unavailable
until an operator reviews the new implementation and deliberately updates the
private binding.

The operation set is check, decompile, function metadata, disassembly, callers,
callees, xrefs-to, xrefs-from, paged function listing, and bounded string
search. It is read-only; durable conclusions belong in source, ledgers, scripts,
or game-local knowledge. Responses report
`authority=provisional-semantic-analysis`, `exactness_credit=none`, and
`output_completeness=factory-bounded-native-ghidra`.

## Measured validation

The isolated live configuration loaded six repositories and six providers. The
generic Windows adapter resolved exactly `target:th10-main` with the expected
hash and size. Native discovery plus a real `function` query at `0x004537DC`
completed in 9.8 seconds on this host. Both returned `status=passed`, transport
`factory-native-command`, implementation binding
`62c66f14aa31c4ed6ed51a57276c2b14ad2b2f7110402a2ad750319228a58f9a`,
and six mapped-byte samples; the function result was
`entry`, signature `int entry(void)`, body `0x004537DC..0x004539B0`, and 426
body addresses. The response exposed no private command, target, tool, project,
or endpoint path.

The repo-local wrapper was also exercised directly for check, function,
12-instruction disassembly, paged listing, bounded string search, and entry
decompilation. Unit regressions cover native configuration redaction, exact
operation fields, and rejection of a Ghidra marker that differs from the
independent PE observation. The portable Factory 0.7.0 release gate passed all
155 tests with no skips, Ruff, bytecode compilation, Git whitespace, 42 JSON,
two TOML, two evaluation XML documents, all three CLI constructions, and an
isolated wheel build. Public MCP activation remains a separate measured gate.

Factory 0.7.0 was then activated behind the unchanged private Funnel route. The
MCP and worker entered active state together with zero restart count. Public
read-only validation passed the unchanged 33-tool inventory and all six
repositories. TH10 normalized to 2,390 imported claims while retaining zero
accepted Oracle results and zero historical fixtures. All 125 service-wide
receipt candidates from the prior runner epoch were accurately rejected rather
than silently retained as current acceptance.

The public analysis suite target-attested legacy TH04/TH095 Ghidra, native TH10
Ghidra, and the currently active TH105 IDA database; TH08 and TH09 IDA were
accurately unavailable because neither was the active Windows database. TH10
passed discovery, `check`, and bounded `list_functions`. A separate public
`function(0x004537DC)` call returned the measured entry metadata above with the
same six samples and implementation binding, provisional authority, and zero
exactness credit.

Finally, a public TH10 repository-shell probe ran target verification, quick
Ghidra/JDK attestation, 1,195-row tracking validation, generated-progress check,
the complete public CI script, and committed-HEAD reads from TH08, TH09, and
TH095. It exited zero without changing HEAD or worktree status and created no
commit. The public TH10 GitHub workflow also passed at commit `2c0a6ab`.

## Campaign handoff

The standalone prompt is
`prompts/gpt-web-th10-exact-reconstruction.md`. It assumes no injected skill,
forces dirty-state recovery, requires native Ghidra attestation, exposes all three
adjacent repositories only as hypothesis material, pressures both reviewed
authored functions and bytes toward a moving 99.5% goal, schedules hard
frontiers as well as small packets, and ends a browser conversation at a
reliable checkpoint without claiming phase closure.
