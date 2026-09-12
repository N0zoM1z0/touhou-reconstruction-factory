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

The MCP surface returns `detail="summary"` by default. It contains the same
content-addressed registry ID and complete partition counts while omitting the
potentially large entry array. Request `detail="full"` only when candidate-level
rejection diagnostics are needed. Summary mode changes response size, not the
classification work or registry identity.

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

## Fast fail-closed evaluation

The live evaluator orders checks by decisive cost. Receipt document and
artifact integrity remain mandatory. During freshness evaluation, a stale
runner implementation digest is terminal for acceptance, so registry and query
paths return that exact rejection without parsing repository adapters or
rehashing targets and toolchains that cannot restore the receipt. Current-runner
receipts continue through every source, claim, target, toolchain, environment,
driver, invocation, and coverage check.

The runner digest covers an explicit replay-execution import closure: adapter
normalization, artifact storage, ontology and receipt semantics, replay drivers,
identity observation, and the runner itself. MCP presentation, workspace,
knowledge, and other control-plane modules are deliberately outside that
closure because they cannot change native replay output or receipt semantics.
The file list is code-reviewed and regression-tested. This avoids cold-replaying
every game merely because a Web tool description or unrelated service surface
changed, while changes to any evidence-producing dependency still invalidate
receipts.

Repository adapter TOML and replay manifests are parsed through process-local
caches keyed by their exact bytes. No mtime, file size, TTL, or pathname-only
shortcut participates. Later bytes are reparsed; live observations and
acceptance decisions are never retained across requests.

## Explicit policy

[`policies/strict-live-v1.json`](../policies/strict-live-v1.json) is the first
published policy. It allows the five current exact drivers plus the TH095
product-closure driver and requires:

- a live repository binding for every accepted target;
- complete coverage and an empty acceptance-error set;
- one of the three accepted coldness mechanisms;
- at least observed toolchain surfaces, with verified native attestation for
  TH04 and the TH095 whole-product driver;
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

`runtime_storage_identity` and `runtime_scenario_validated` are defined in the
truth vocabulary but are not allowed by this policy. Runtime prose, a playable
label, or a successful product build therefore cannot enter the registry as a
runtime pass. A future bounded runtime provider requires its own driver and
oracle allowlist entries.

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

The MCP query uses `detail="summary"` by default and returns receipt, claim,
subject, target, toolchain, source snapshot, Oracle, verdict, and coverage
identity without verbose claim metadata, diagnostics, and evidence arrays.
Use `detail="full"` when those complete bindings are needed. Both projections
perform the same artifact and freshness checks before projecting the result.

The service builds the registry and projects facts atomically under the same
repository lock set. It therefore consumes the integrity and freshness pass
that just admitted those receipts instead of releasing the locks and repeating
the same observations inside one MCP call. An `AcceptanceRegistry` object used
later still rechecks artifacts and freshness before returning facts; the reuse
applies only to the point-in-time build-and-query operation.

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
