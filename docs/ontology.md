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
  product, function, extent, data, source unit, object, section, and image.

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

An **oracle result** evaluates one claim. Its role is either:

- `diagnostic`: routes investigation and cannot grant exactness;
- `acceptance`: may advance a claim only under complete declared coverage.

Verdicts are:

- `pass`: the declared claim and coverage passed;
- `fail`: the complete check found a contradiction;
- `incomplete`: required coverage or attestation was unavailable;
- `error`: the oracle could not execute its contract.

An acceptance `pass` requires complete coverage and at least one durable
evidence reference. Missing bytes, unknown extents, stale manifests, absent
relocation destinations, and truncated output are `incomplete`, never `pass`.

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
