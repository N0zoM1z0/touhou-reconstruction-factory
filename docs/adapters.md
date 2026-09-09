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
- a factory `OracleResult(pass)` requires a future cold replay through a
  versioned factory oracle envelope.

## Implemented adapters

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

The adapter currently covers the TH095 VC7.1 and TH105 VC8 LTCG ledger forms.
It separates provisional boundary extents, origin, source presence, exact
codegen, and physical ownership into independent claims. The TH105 ownership
manifest is target-bound and validated for main size, exclusions, ordered
non-overlapping remote chunks, candidate-start intrusion, byte totals, and
remote-exact evidence.

The Windows target identity is marked `manifest-declared`, not `hash-attested`,
because the read adapter deliberately does not access or hash the private
executable.

`vc8_runtime` is normalized to the generic `library` origin while the native
value is retained in claim data. Unrecognized origin values produce error
diagnostics rather than guessed classifications.

## Native parity validation

`validate-live` runs each repository's read-only native status command and
compares it against adapter metrics. It snapshots `git status` before and after
and rejects a report if validation changed the working tree.

```bash
PYTHONPATH=src python3 -m reconstruction_factory validate-live \
  /path/to/th04 \
  /path/to/th095 \
  /path/to/th105
```

At the 2026-09-09 development snapshot, validation compared 36 TH04 metrics,
10 TH095 metrics, and 12 TH105 metrics with exact parity.

## Snapshot inspection

```bash
PYTHONPATH=src python3 -m reconstruction_factory inspect /path/to/repo --summary
```

The summary includes the selected provider family, input fingerprint, metrics,
diagnostics, and entity counts. Omit `--summary` for the complete normalized
snapshot.

## Deliberate v0 limits

- Adapters do not execute compilers, disassemblers, exact comparators, or
  whole-build commands.
- TH07 and TH08 adapters are not yet implemented.
- Existing evidence prose and IDs are imported but are not automatically
  promoted into the factory artifact store.
- Whole-build closure remains unattested unless a structured receipt exists;
  function exactness never fills that gap.
