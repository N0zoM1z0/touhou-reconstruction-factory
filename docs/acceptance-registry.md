# Verified receipt acceptance registry

The acceptance registry is the only bridge from stored replay evidence into an
accepted truth view. Repository adapters still emit claims and diagnostics but
no acceptance results. A receipt file merely appearing in an artifact store
also grants no truth.

## Decision pipeline

Every candidate is classified explicitly:

1. `invalid`: the receipt document, content address, semantic envelope,
   storage key, or referenced artifact objects cannot be verified;
2. `rejected`: the receipt is internally valid but fails the selected policy
   or its live repository binding is missing or stale;
3. `accepted`: the receipt is a complete acceptance `pass`, satisfies every
   policy allowlist and evidence threshold, and is fresh for its explicitly
   bound live repository.

Candidates are never silently omitted. Even invalid documents receive an
entry with a content hash and size when their bytes can be read. The registry
ID hashes the policy identity, policy digest, complete decision list, candidate
content identities, and counts.

All supplied repositories are held under shared factory locks for the complete
registry evaluation. Replays take the corresponding exclusive lock. This
prevents two factory operations from observing a half-completed native replay,
although non-factory programs that ignore the lock remain outside this
coordination boundary.

An accepted-knowledge query acquires shared locks for all selected repositories
before revalidating any fact, so a factory replay cannot produce a mixed-time
multi-repository answer. Artifact objects must be regular files opened without
following symlinks; matching bytes reached through an alias are not accepted as
immutable store evidence.

## Explicit policy

[`policies/strict-live-v1.json`](../policies/strict-live-v1.json) is the first
published policy. It allows only the four current controlled drivers and their
exact claim types and requires:

- a live repository binding for every accepted target;
- complete coverage and an empty acceptance-error set;
- one of the three accepted coldness mechanisms;
- at least observed toolchain surfaces, with verified native attestation for
  TH04;
- the exact adapter, oracle, and driver allowlists in the policy.

The policy allows a dirty source tree because receipts hash the complete live
tracked and non-ignored state before and after replay. That means the claim is
accurate for that exact state; it does not make the state a canonical or
reproducible release. A release policy may set `allow_dirty_source` to `false`
without changing receipt semantics.

Unknown toolchain attestation, incremental replay, and policies that disable
freshness, complete coverage, or empty acceptance errors are structurally
incapable of acceptance. Adding a future driver requires an explicit policy
change and therefore changes the policy SHA-256.

## Accepted snapshots

`inspect-accepted` performs a new live check and materializes a
`RepositorySnapshot` whose `oracle_results` and `artifacts` are replaced with
registry-accepted values. It never preserves an imported or caller-supplied
result alongside them. Claim and subject hashes are checked again during
materialization.

The materialized snapshot input fingerprint binds:

- the adapter input fingerprint;
- the complete acceptance-policy digest;
- the accepted receipt IDs relevant to that snapshot.

Unrelated invalid or rejected candidates remain visible in the registry report
but do not perturb the accepted snapshot fingerprint.

## Accepted knowledge queries

`accepted-knowledge` exposes receipt-backed facts, optionally filtered by
target identity, claim type, or oracle ID. Before returning a fact, it checks
the referenced artifacts and live freshness again. A registry object is not a
permanent authorization: changing source, target, toolchain, environment,
driver, runner, or evidence after registry construction makes the query fail.

This command is intentionally separate from `knowledge`. The latter is the
reviewed cross-game catalog backed by historical regression fixtures. A live
exact receipt is evidence for its scoped claim, not automatic proof of a
cross-game invariant. Promotion from receipt-backed facts into the shared
catalog remains a reviewed operation.

## Commands

```bash
PYTHONPATH=src python3 -m reconstruction_factory acceptance-registry \
  --store .factory/final \
  --policy policies/strict-live-v1.json \
  --repository target:th08-main=/path/to/th08

PYTHONPATH=src python3 -m reconstruction_factory inspect-accepted /path/to/th08 \
  --store .factory/final \
  --policy policies/strict-live-v1.json \
  --summary

PYTHONPATH=src python3 -m reconstruction_factory accepted-knowledge \
  --store .factory/final \
  --policy policies/strict-live-v1.json \
  --repository target:th08-main=/path/to/th08 \
  --claim-type codegen_exact
```

The normative policy and registry shapes are
[`acceptance-policy.schema.json`](../schemas/v1/acceptance-policy.schema.json)
and
[`acceptance-registry.schema.json`](../schemas/v1/acceptance-registry.schema.json).

Content addressing still proves integrity rather than authorship. Registry
acceptance assumes a trusted local or CI execution/store boundary until a
separate signing or transparency contract is implemented.
