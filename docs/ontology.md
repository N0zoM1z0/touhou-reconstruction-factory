# Reconstruction Truth Kernel and Vocabulary

## Purpose

The truth kernel is the smallest platform-independent contract shared by every
reconstruction instance. It makes target binding, subject scope, evidence,
coverage, and oracle verdicts explicit. It does not prescribe PE, MZ, COFF,
OMF, compiler, disassembler, or runtime implementations.

The kernel follows two equivalent rules: a convenient workflow state must never
imply a stronger truth claim than its evidence proves, and incomplete knowledge
is preferable to incorrect knowledge. `unknown` and `incomplete` are valid,
actionable outputs rather than failures to be hidden.

## Identity hierarchy

```text
Project -> Product -> TargetIdentity
                    -> ToolchainIdentity

Subject -> Claim -> OracleResult -> ArtifactRef
```

- A **project** is one reconstruction repository or coordinated source effort.
- A **product** is one independently attestable output, such as TH04 OP, MAIN,
  MAINE, or ZUN. A project may contain multiple products.
- A **target identity** binds a product to version, region, format, size,
  cryptographic hashes, provenance, and canonicality.
- A **toolchain identity** binds compiler-family assertions to a deterministic
  fingerprint over the attested surfaces used by the project.
- A **subject** is the entity about which a claim is made. Subject kinds are
  product, runtime scenario, function, extent, data, source unit, object,
  section, and image. A product or runtime scenario may be extent-free because
  its provider declares a non-byte coverage domain.

Addresses are never globally meaningful. Every subject is target-qualified,
and every extent names its address space. Non-contiguous physical ownership is
represented by multiple extents with explicit roles.

A provisional function candidate may have no accepted extent. Such a subject
is representable, but it cannot receive a passing exact claim. This is required
for TH04 map-public observations whose current body size is zero.

## Claims and verdicts

A **claim** is a typed assertion. Examples include `boundary_extent`, `source_present`,
`codegen_exact`, `physical_ownership`, and `whole_build_closed`. Claims bind to
one subject and one target identity. Toolchain-dependent claims also bind to a
toolchain identity.

`semantic_evidence` records one bounded interpretation with its evidence class
and limitations. `semantic_ownership` records one target-qualified conceptual
owner relationship. Neither is a project-level "semantics complete" bit, and
neither follows from a readable identifier, layout assertion, exact function,
successful build, or runtime observation alone.

The primary verification planes are deliberately independent:

- `codegen_exact` and `owned_extent_exact` cover declared function or extent
  bytes;
- `whole_build_closed` covers the complete declared production graph and a
  clean link for an extent-free product subject;
- `runtime_storage_identity` covers a bounded physical-storage, alias,
  publication, or lifetime relationship observed at runtime;
- `runtime_scenario_validated` covers one artifact-, asset-, environment-,
  input-, and observable-bound scenario.

No claim in this list implies another. In particular, exact functions may
coexist with unresolved product linkage, and a closed product may coexist with
a deliberately non-exact function or unknown runtime behavior. The operational
feedback loop and the TH095 positive/negative example are specified in
[`verification-planes.md`](verification-planes.md).

An **oracle result** evaluates one claim. Its role is either:

- `diagnostic`: routes investigation and cannot grant exactness;
- `acceptance`: may advance a claim only under complete declared coverage.

Verdicts are:

- `pass`: the declared claim and coverage passed;
- `fail`: the complete check found a contradiction;
- `incomplete`: required coverage or attestation was unavailable;
- `error`: the oracle could not execute its contract.

An acceptance `pass` requires complete coverage and at least one durable
evidence reference. Coverage is claim-specific: exact claims commonly count
bytes, product closure counts production translation units, and a future
runtime provider must count its declared scenario observables. Missing bytes,
unknown extents, stale manifests, absent relocation destinations, truncated
output, or an unavailable runtime provider are `incomplete` or `unknown`, never
`pass`.

The `OracleResult` is the truth-kernel verdict, not the execution transcript.
When it originates from replay, it is carried by a content-addressed
[`OracleReceipt`](oracle-receipts.md) that additionally binds the full claim,
subject extents, observed target and toolchain surfaces, exact live source
snapshot, invocation stages, and retained output.

## Engineering phases and semantic batches

Engineering phases coordinate work; they are not truth verdicts and never
promote claims implicitly:

- **authored reconstruction** recovers maintainable source candidates for
  target behavior;
- **production closure** recovers the complete compile/link graph, ABI, data,
  and owners needed to build a declared product;
- **semantic reconstruction** replaces target-layout-shaped source with
  evidence-backed types, names, representations, protocols, and canonical
  owners while preserving applicable exact and product/runtime baselines; and
- **port implementation** adapts semantic source to another platform product
  without turning that product's behavior into target exactness.

The historical-platform order is deliberate:

```text
target-specific exact baseline
  -> corresponding historical-platform product closure and runtime-owner feedback
  -> semantic reconstruction under both feedback lanes
  -> portable platform products
```

For Windows PE projects, the middle prerequisite is the reconstructed Windows
i386 product. For PC-98 projects, it is the corresponding 16-bit product and
runtime environment. Whole-project exactness need not be falsely declared when
a bounded residual remains unknown, but the exact baseline must be explicit and
the historical production graph must compile/link before semantic work begins.
A modern Windows, Linux, or Web port cannot substitute for that product gate.
Finishing exact functions or a clean link alone still does not imply semantic
completion.

A **semantic-debt candidate** is a heuristic work route, not a claim. A
**semantic batch** is one coherent owner, field, representation, or protocol
family plus its evidence record and affected-oracle closure. A **semantic
checkpoint** is the batch's durable review commit; it is not an OracleResult.
**Semantic completion** is a qualitative game-local exit audit and has no
canonical aggregate claim or live Factory provider in schema version 1. The
normative batch contract and non-implications are in
[`semantic-reconstruction.md`](semantic-reconstruction.md).

## Evidence maturity

- `observed`: directly present in an attested artifact or deterministic output;
- `corroborated`: supported by independent evidence sources;
- `inferred`: bounded interpretation that must not be used as an exact premise;
- `unknown`: deliberately unresolved.

Evidence maturity is not an oracle verdict. An observed origin does not imply
exact source, and an exact function does not prove object ownership.

## Origin vocabulary

The canonical origin values are:

- `authored_game`
- `compiler_generated`
- `library`
- `third_party`
- `import_thunk`
- `original_assembly`
- `data`
- `padding`
- `unknown`

Adapters may map native values into this vocabulary only through documented,
lossless mappings. Unmapped values produce diagnostics.

## Ownership vocabulary

- `source_owner`: canonical source declaration or definition owner;
- `object_owner`: compiler object or LTCG contribution owner;
- `physical_owner`: final-image extent or chunk owner;
- `semantic_owner`: runtime/domain subsystem that conceptually owns behavior.

These relationships are independent. The unqualified field name `owner` is
forbidden in new truth-kernel schemas.

## Work coordination

A **work lease** records a temporary holder, branch, work packet, and subjects.
It replaces the overloaded term “claim” used by older `claims.csv` files.

Work leases and handoffs are not part of the truth chain. Losing a lease does
not invalidate evidence, and holding a lease proves nothing about a subject.

## Normative serialization

The Python dataclasses in `reconstruction_factory.ontology` enforce graph and
fail-closed invariants. `schemas/v1/truth-snapshot.schema.json` is the
language-neutral interchange contract. Both use schema version 1.
