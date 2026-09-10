# Oracle receipts

An oracle receipt is the factory's durable statement about one replay of one
claim. Native project output is evidence inside the receipt; it is not itself a
factory verdict.

The envelope is intentionally shared by PC-98 MZ/OMF and Windows PE/COFF
projects. The comparator, toolchain surface, address space, relocation policy,
and cold-build mechanism remain provider- or driver-specific.

## Required bindings

Every receipt binds all of the following values:

- the complete normalized `Claim` and `Subject`, including every declared
  extent, by canonical SHA-256;
- the declared target identity and the size and SHA-256 of the target bytes
  actually observed immediately around the replay;
- the declared `ToolchainIdentity`, the environment variables that can select
  execution surfaces, and conservative hashes of the toolchain surfaces
  observed by the driver;
- the Git commit and tree plus a content digest of every tracked or
  non-ignored untracked file in the instance repository scope, both before and
  after execution;
- the driver version, defined by the exact checked-in native scripts and
  manifests that implement its build and comparison contract;
- the complete factory Python implementation before and after the replay, so
  changes to normalization, execution, receipt, or adapter semantics cannot be
  hidden behind a static runner version;
- every shell-free invocation stage, its declared input digest, exit status,
  duration, and complete stdout and stderr artifacts;
- structured native comparison evidence, explicit coverage, normalizations,
  and the final truth-kernel `OracleResult`.

The receipt ID is the SHA-256 of the canonical envelope with an empty
`receipt_id`. Any edit invalidates the ID. Evidence artifacts use their own
content addresses and may be deduplicated by a receipt store.

## Fail-closed verdicts

The result vocabulary remains exact:

- `pass`: the acceptance contract ran with complete declared coverage and all
  receipt invariants hold;
- `fail`: the oracle fully evaluated the claim and disproved it;
- `incomplete`: the available replay did not cover or attest enough to decide;
- `error`: the oracle contract could not execute reliably, including timeout,
  malformed output, source mutation during replay, or identity drift.

A zero process exit code is never sufficient for `pass`. In particular, an
incremental comparison, a target hash copied only from a manifest, a compiler
binary without its relevant headers and execution surface, or a report whose
address and size do not match the claim remains incomplete or erroneous.

Dirty source trees are not automatically rejected. Reconstruction work often
needs verification before commit. Instead, the runner hashes the exact live
source state and rejects any receipt whose state changes during execution. A
later consumer can therefore test freshness against the same source digest.

## Coldness vocabulary

`coldness` states how stale candidate output is excluded:

- `isolated-double-build`: two separately materialized builds agree;
- `clean-output-graph`: the native generated-output graph is cleaned before
  the selected target is rebuilt;
- `forced-recompile`: the compiler is unconditionally invoked and overwrites
  the selected candidate object;
- `incremental`: an existing artifact may have satisfied the request;
- `unknown`: the driver cannot prove how the candidate was produced.

Only the first three values can support an acceptance pass. They are not
claimed to be interchangeable: the precise mechanism remains visible in the
receipt.

## Native repository policy

Drivers are narrow translators, not compatibility promises. A project with a
weak native workflow is allowed to produce only `incomplete` receipts until
its build or comparator is strengthened. The factory must not parse arbitrary
ledger command strings, execute user-provided shell fragments, infer extent
coverage from names, or reinterpret a native diagnostic as acceptance.

The normative machine shape is
[`schemas/v1/oracle-receipt.schema.json`](../schemas/v1/oracle-receipt.schema.json).

## Controlled drivers

The first drivers deliberately expose different native mechanisms behind one
receipt contract. They do not pretend that the mechanisms prove the same
platform facts.

| Driver | Accepted claim scope | Coldness proof | Native evidence and limit |
|---|---|---|---|
| TH04 Borland 16-bit | one declared MAIN owned extent | two isolated materializations | Both builds must agree on raw bytes, map ownership, relocations, and valid OMF objects. The native toolchain attestation must bind the same target and all required Borland surfaces. |
| TH08 VC7 | one declared function extent | clean generated-output graph followed by a selected rebuild | The strict JSON function comparator must bind unit, address, size, byte count, and relocations. This proves neither source/object ownership nor whole-image equality. |
| TH095 VC7.1 | one declared function extent | unconditional selected-unit compiler invocation | The strict COFF report must bind unit, address, size, matched bytes, and relocations. It does not promote whole-build closure. |
| TH095 VC7.1 whole build | one extent-free product | cold rebuild of the complete declared production output graph | All 88 declared production translation units must compile as i386 COFF under their canonical profiles, the clean link must have zero unresolved symbols and no `/FORCE*` flag, and the output must be a report-bound PE32 i386 Windows GUI image. This proves neither function exactness, whole-image equality, nor runtime behavior. |
| TH105 VC8 | one declared standalone function extent | unconditional non-LTCG probe compilation | Build provenance and the manifest-derived comparison contract must agree. The oracle ID explicitly says `standalone-function-exact`; it does not prove LTCG physical ownership, linked-owner layout, or whole-image closure. |

Driver selection is factory code. Ledger command strings are evidence for an
adapter, but are never executed. Every argument vector is rebuilt from typed
claim fields and checked native manifests. Driver identity hashes the factory
driver implementation and every native script or manifest that defines the
selected build/comparison contract.

The receipt envelope accepts driver-declared non-byte `Coverage` for product
and future runtime claims. A driver cannot reuse a byte count from a different
subject to manufacture completeness. The current strict policy allows the
TH095 product driver but deliberately allows no runtime claim or runtime driver.

## Running and verifying a replay

```bash
PYTHONPATH=src python3 -m reconstruction_factory replay /path/to/game \
  --claim claim:project-main:function:00401000:codegen-exact \
  --store .factory

PYTHONPATH=src python3 -m reconstruction_factory verify-receipt \
  .factory/receipts/<sha256>.json \
  --store .factory \
  --repository /path/to/game
```

The first command takes a lock in the repository's Git administrative area,
then performs inspection, planning, observation, execution, and receipt
sealing under that lock. Locks therefore remain exclusive even when two
factory processes select different artifact stores.

Verification without `--repository` checks the receipt content ID, semantic
invariants, and every referenced artifact object. Live verification also
reconstructs the current normalized claim and invocation plan and checks the
full Git snapshot, target, toolchain surfaces, environment selector values,
driver version, and factory runner implementation.

Content addressing is integrity, not authorship. A hostile writer capable of
replacing an entire store can manufacture a different internally consistent
store. Signed receipts and remote transparency are separate future contracts;
the current store is suitable for a trusted local or CI execution boundary.

A valid receipt is not automatically accepted truth. Promotion into snapshots
and receipt-backed queries is governed by the separate
[`verified receipt acceptance registry`](acceptance-registry.md).
