# Platform and Toolchain Provider Contracts

## Abstract Factory boundary

`ReconstructionFactory.create(ProjectSpec)` selects one platform provider and
one toolchain provider, validates every target, verifies bidirectional
compatibility, and returns one coherent `ReconstructionKit`.

Providers describe structural semantics and required oracle contracts. Their
presence does not imply that all binary oracles are implemented. This
distinction prevents a descriptor from becoming a false completion claim.

## Built-in provider families

| Platform | Compatible toolchains | Important structural capabilities |
|---|---|---|
| `pc98-mz-omf` | `borland16` | MZ/COM, OMF, segmented addressing, relocations/fixups, multi-product |
| `windows-pe-coff` | `msvc7`, `msvc71`, `msvc8-ltcg` | PE, COFF, linear VA, COMDAT, imports/resources |

| Toolchain | Ownership/codegen model |
|---|---|
| `borland16` | memory model, near/far semantics, OMF/TLINK layout |
| `msvc7` | focused standalone COFF is useful; final ownership remains separate |
| `msvc71` | normal standalone COFF and LTCG may coexist in one target; the declared artifact owner selects a normal-COFF or linked-image Oracle, while final product ownership remains separate |
| `msvc8-ltcg` | semantic and physical owners may diverge; remote chunks are first-class |

## Compatibility rules

Compatibility is bidirectional. Both providers must name the other as allowed.
Every target must pass both validators, and every capability required by the
project specification must be present in the combined family.

Examples of rejected construction:

- MZ/OMF plus an MSVC toolchain;
- PE/COFF plus the Borland 16-bit toolchain;
- a PE target passed to the PC-98 provider;
- a VC8 LTCG kit required to support standalone-COFF matching;
- an alleged LTCG target with explicitly zero LTCG evidence.

## Extension rule

New games select providers; they do not modify provider semantics. A new
provider ID is required when an implementation changes the meaning of address,
extent, codegen, ownership, relocation, or whole-image evidence. Reusing an ID
requires the old regression fixtures to retain exactly the same verdicts.

## Installed payload boundary

A provider family describes semantics; a tracked toolchain manifest identifies
one candidate payload; a game-local executable verifier demonstrates that the
payload actually works in that repository's environment. None substitutes for
the others. Shared immutable compiler and Wine installations are infrastructure,
while the selector, Wine prefix, build graph, profile hypotheses, generated
objects, and receipts remain game-bound.

TH10 demonstrates why `msvc71` cannot mean “standalone COFF everywhere.” Its
Rich records contain normal C, normal C++, and LTCG C++ inputs from the same
build-6030 generation. TH10 claims carry their manifest-declared
`artifact_kind`: the normal-COFF driver requires `coff` and rejects `/GL`, while
the linked-PE driver requires `linked-pe`, `/GL`, `/ltcg`, and a complete
target-bound PE/map/PDB contribution replay. Archive-member COFF remains a
separate unsupported route until its immutable rematerialization has an honest
coldness vocabulary. The canonical VC7.1 SP1 payload and provisioning contract are pinned in
[`config/toolchains/msvc710-sp1.toml`](../config/toolchains/msvc710-sp1.toml).
