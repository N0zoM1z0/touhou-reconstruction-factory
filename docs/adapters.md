# Existing-Repository Read Adapters

## Contract

Adapters translate existing repository ledgers into truth-kernel snapshots.
They are read-only and deterministic over their declared input files.

The governing rule is accuracy before completeness:

- native evidence is preserved with its native scope;
- unknown fields remain unknown;
- vocabulary mappings must be explicit and lossless;
- address coverage mismatches, duplicate identities, target mismatches, and
  invalid extent graphs fail closed;
- an imported exact ledger row becomes an imported `codegen_exact` claim, but
  not a factory acceptance result;
- a factory `OracleResult(pass)` requires a separate cold replay through a
  versioned factory oracle envelope.

## Implemented adapters

### Inventory-only control-plane imports

The CLI and MCP inspection/analysis interfaces use `inspection_adapters.py`.
It adds the following conservative imports before falling back to the existing
replay adapter registry:

- `th05-pc98-manifest-v1` reads `config/targets.toml` and
  `config/toolchain.toml`. It exposes TH05's MAIN, OP, MAINE and COM ZUN targets
  with their declared provenance, without inventing function or acceptance
  ledgers. TH05 calibration artifacts inside other games do not select it.
- `windows-pe-inventory-v1` reads `config/target.toml`,
  `config/functions.csv` and `config/tools.lock.toml` for TH06, TH07, TH11 and
  TH20. It exposes complete native function rows as provisional boundaries.
  Native `matching` labels, acceptance files, origins and source presence are
  not interpreted as Factory claims by this initial import.

These adapters produce no Oracle results or exactness credit. Their limited
scope is explicit in diagnostics. TH20 retains its operator-selected Steamless
target hash and native version/provenance fields; registration does not select
a different executable. The `pe-inventory-only` toolchain descriptor grants no
compile or replay capability. TH075 uses the existing Windows ledger adapter.
Inventory additions do not enter the replay execution registry or change its
implementation fingerprint. New replay drivers require separate review of
each game's native source and acceptance contract.

### `th03-pc98-v1`

TH03 uses the shared multi-product PC-98 adapter contract with
`config/th03_function_boundaries.csv` and
`config/th03_main_authored_functions.csv`. Its products are OP, MAIN, MAINL
and ZUN. Only `game = "th03"` targets contribute to progress; optional
cross-game calibration artifacts are excluded. Empty ledgers import zero
source/ownership/exact claims rather than inheriting TH04 progress. Target
version remains unknown when the manifest does not establish it.

Native analysis uses the command backend with independent MZ/header/load,
relocation and entry checks. TH03 exact-unit replay has no registered driver
until its own source and extent contract are implemented.

### `th04-pc98-v1`

Inputs:

- `config/targets.toml`
- `config/toolchain.toml`
- `config/th04_function_boundaries.csv`
- `config/th04_main_authored_functions.csv`
- `config/units.csv`

The adapter imports four TH04 products and excludes TH01 oracle-smoke targets
from TH04 project progress. It preserves hash-attested targets, segmented
addresses, zero-size provisional boundary observations, boundary/origin claims,
and exact-unit claims. It does not rehash private target content, so an explicit
diagnostic distinguishes imported native attestation from a fresh factory
attestation.

The target manifest does not record an explicit TH04 version, so the adapter
emits `version = unknown` and a diagnostic instead of guessing.

### `windows-pe-ledgers-v1`

Inputs:

- `config/target.toml`
- `config/tools.lock.toml`
- `config/functions.csv`
- `config/function-origins.csv`
- `config/reccmp-functions.csv`
- `config/implemented.csv`
- `config/matches.csv`
- `config/match-units.toml`
- optional `config/function-byte-ownership.toml`
- optional TH095 `scripts/build-whole.py`

The adapter covers the related TH09, TH095, and TH10 Windows ledger forms plus
the TH105 VC8 LTCG form. It separates provisional boundary extents, origin,
source presence, exact codegen, and physical ownership into independent claims.
The TH105 ownership manifest is target-bound and validated for main size,
exclusions, ordered non-overlapping remote chunks, candidate-start intrusion,
byte totals, and remote-exact evidence.

When TH095 has the maintained whole-build script, the adapter also emits one
extent-free product subject and one `whole_build_closed` candidate. Its source
and profile counts are derived from the canonical match-unit table. The claim
has `evidence_class=unknown` and `state=replay-required`; the adapter never runs
the script or manufactures a product pass. The controlled product driver and
acceptance registry perform that independent operation.

The Windows target identity is marked `manifest-declared`, not `hash-attested`,
because the read adapter deliberately does not access or hash the private
executable.

TH09's 2026-09-10 bootstrap validated the clean zero-state contract. It
contained 2,159 provisional nonzero IDA candidates, all with unknown origin and
review state, while mappings, implemented rows, match rows, and exact units were
empty. TH10's 2026-09-12 Ghidra bootstrap similarly began with 1,195
provisional `unknown/review` candidates and empty source and exact ledgers.
Those numbers describe bootstrap checkpoints, not either repository's current
progress. In both cases the adapter imported boundary and unknown-origin claims
but produced no Oracle result and no exactness credit. Private executable
rehashing belongs to the separately configured Factory-native analysis provider
and controlled replay drivers, not this public repository reader.

`vc8_runtime` is normalized to the generic `library` origin while the native
value is retained in claim data. Unrecognized origin values produce error
diagnostics rather than guessed classifications.

### `th08-vc7-ledgers-v1`

Inputs:

- `config/target.toml`
- the headerless `config/mapping.csv`
- `config/reccmp-functions.csv`
- `config/implemented.csv`
- authored `matches.csv` and `match-units.toml`
- library `library-matches.csv`, `library-match-units.toml`, and
  `library-provenance.toml`

TH08 has a distinct, older Windows ledger shape and is intentionally not
coerced into the TH095/TH105 adapter. Its inventory separates `function`
(authored) and `library` rows. Authored and library exactness remain separate
metrics and claims, and neither is converted into a factory oracle result.

`implemented.csv` is a set of source-level names, not function identities. One
name may cover more than one target address, so source-present function counts
are computed over target-address rows. At the validated checkpoint, 1,106
unique implemented names cover 1,107 authored target functions. Treating the
set size as the function count would be a silent undercount.

## Native parity validation

`validate-live` runs each repository's read-only native status command and
compares it against adapter metrics. It snapshots `git status` before and after
and rejects a report if validation changed the working tree.

```bash
PYTHONPATH=src python3 -m reconstruction_factory validate-live \
  /path/to/th04 \
  /path/to/th08 \
  /path/to/th09 \
  /path/to/th095 \
  /path/to/th10 \
  /path/to/th105
```

At the historical 2026-09-09 development snapshot, validation compared 36 TH04
metrics, 11 TH08 metrics, 10 TH095 metrics, and 12 TH105 metrics with exact
parity. That record predates TH09 and TH10 registration. The current deployed
procedure validates all six adapters; see [`validation.md`](validation.md) and
query current repository state rather than carrying these counts forward.

## Snapshot inspection

```bash
PYTHONPATH=src python3 -m reconstruction_factory inspect /path/to/repo --summary
```

The summary includes the selected provider family, input fingerprint, metrics,
diagnostics, and entity counts. Omit `--summary` for the complete normalized
snapshot.

## Deliberate current limits

- Adapters do not execute compilers, disassemblers, exact comparators, or
  whole-build commands. They may import a typed replay candidate for a
  separately controlled driver.
- A TH07 adapter is not yet implemented.
- Existing evidence prose and IDs are imported but are not automatically
  promoted into the factory artifact store.
- Whole-build closure remains unattested unless a structured accepted receipt
  exists; function exactness never fills that gap. Runtime storage and scenario
  validation remain separate and currently have no live Factory driver.
