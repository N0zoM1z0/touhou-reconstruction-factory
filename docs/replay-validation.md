# Controlled replay validation

This document records the first live integration validation of the
factory-controlled replay contract. It is deliberately narrow: four known
exact claims test four materially different repository/toolchain workflows.
It does not claim that any game is complete or that every native oracle is
sound.

## Initial replay snapshot

The validation ran on 2026-09-09 with factory runner implementation digest
`5d3460ede57d28f52d9f3d622ca6312c2f1e3e1ffb1a0ee2a8ea898a2d2d483d`.
All 46 factory unit tests passed before the live runs. Every resulting receipt
then passed both artifact integrity verification and live freshness checking.

| Game | Repository commit | Claim | Coldness | Coverage | Receipt |
|---|---|---|---|---:|---|
| TH04 | `1fa8de07742255053299628213f0674d742a410c` | `claim:unit:th04-main-slowdown-frame-delay:owned-extent-exact` | `isolated-double-build` | 26/26 | `receipt:dc80af36aa22f70bad849d59cfac368b14e70fa5ed4287e723f383805cdf2d03` |
| TH08 | `bd54d865ebbc9f7291b355d152b16cc4b7f5be59` | `claim:th08-main:function:00402000:codegen-exact` | `clean-output-graph` | 296/296 | `receipt:333bf00e46d6aae3d7cfc44c4fad6e3632909cc03980d519eab4da72d95951a6` |
| TH095 | `33d46a0ee48f37060d973125a1a7632a40f8d998` | `claim:th095-main:function:00401090:codegen-exact` | `forced-recompile` | 24/24 | `receipt:b48e035d61459e6ef791f3155d935c6035e1779aee697296e9065437651a444d` |
| TH105 | `20f993b7908d8a207a39cf13da8d7614b9a3b23f` | `claim:th105-main:function:00401000:codegen-exact` | `forced-recompile` | 52/52 | `receipt:ca8a7ec7fe26b7c7f0683af37e305e0105beb706b97f9c41bb48e2cc09d17339` |

All four verdicts were `pass` with empty `acceptance_errors`. The factory
observed 17 toolchain components for TH04, eight for TH08, and six each for
TH095 and TH105. TH04 additionally satisfied its native `verified`
attestation; the Windows drivers conservatively report their directly hashed
surfaces as `observed`.

TH095 was intentionally not cleaned. Its live source binding records a dirty
tree with three non-ignored untracked files, and the same complete state was
observed before and after replay. A dirty tree is therefore not mistaken for a
canonical release, but it can still support an exact claim about the precisely
hashed live state. The other three source bindings were clean.

TH105's pass is restricted to
`windows.msvc8.standalone-function-exact`. The receipt explicitly retains that
it does not prove LTCG physical ownership, linked-owner layout, or whole-image
closure. Promoting it to any of those claims would be an error.

## Evidence retention

The receipt and artifact objects remain in the ignored local
`.factory/final` store. They bind private target and toolchain observations and
are not silently promoted into the public repository. The IDs above record the
exact local execution checkpoint, while the executable tests and driver
contracts are the public regression surface. A future export policy must
classify and redact receipts before publishing them; an ID without its object
store is not independently verifiable evidence.

## Reproduction commands

```bash
PYTHONPATH=src python3 -m reconstruction_factory replay ../th04-reconstruction/th04 \
  --claim claim:unit:th04-main-slowdown-frame-delay:owned-extent-exact \
  --store .factory/final

PYTHONPATH=src python3 -m reconstruction_factory replay ../th08-reconstruction/th08 \
  --claim claim:th08-main:function:00402000:codegen-exact \
  --store .factory/final

PYTHONPATH=src python3 -m reconstruction_factory replay ../th095-reconstruction/th095 \
  --claim claim:th095-main:function:00401090:codegen-exact \
  --store .factory/final

PYTHONPATH=src python3 -m reconstruction_factory replay ../th105-reconstruction/th105 \
  --claim claim:th105-main:function:00401000:codegen-exact \
  --store .factory/final
```

Each receipt can be checked later with `verify-receipt`. Adding
`--repository` intentionally makes an old but intact receipt fail freshness
after any relevant source, claim, target, toolchain, environment, driver, or
runner change.

## Acceptance-registry snapshot

The acceptance layer was validated separately after its implementation was
frozen. The final runner implementation digest was
`9ea230feeb817239ad2aa7a1960b5b287200aea2fd14b9542b3da8100ffa8335`,
and the `strict-live-v1` policy digest was
`2c8e8eacece083a5941fb188cab76d15d9be72397ffe283a1db81413312b4b17`.
All 63 factory unit tests passed before these live runs.

The validation used a new ignored store containing exactly four candidates:

| Game | Repository commit | Source | Claim | Coldness | Coverage | Receipt |
|---|---|---|---|---|---:|---|
| TH04 | `1fa8de07742255053299628213f0674d742a410c` | clean | `claim:unit:th04-main-slowdown-frame-delay:owned-extent-exact` | `isolated-double-build` | 26/26 | `receipt:bcadb41af4d72620bc2913f0fbf2ad770b4d320729970d6d99c0505ccc270031` |
| TH08 | `bd54d865ebbc9f7291b355d152b16cc4b7f5be59` | clean | `claim:th08-main:function:00402000:codegen-exact` | `clean-output-graph` | 296/296 | `receipt:1da3a0c83fa236fac2589c01c14aaf0d7fc9df9b279ec3d21a94a51136169702` |
| TH095 | `0756a075b50c358198af42143cfe2d2882346e8c` | clean isolated worktree | `claim:th095-main:function:00401090:codegen-exact` | `forced-recompile` | 24/24 | `receipt:42a21a174e8918a1057be59969c1486ef9c892de03eff3dab8577de5bf4304f9` |
| TH105 | `20f993b7908d8a207a39cf13da8d7614b9a3b23f` | clean | `claim:th105-main:function:00401000:codegen-exact` | `forced-recompile` | 52/52 | `receipt:63a093f5d729c6c7f0c12fa0d1422dc703f62e03f35a122b84f7540656bfbf94` |

The registry classified all four candidates as `accepted`, with zero rejected
or invalid candidates. Its content identity was
`registry:9f75d06a233c0be72a9dae383d80d30ae02a9c2cb977bfd914d5fec9ae7fb0f3`.
The accepted-knowledge query returned exactly four facts, each with a `pass`
verdict and complete coverage. Per-repository snapshot materialization
returned exactly one accepted result and these fingerprints:

| Game | Accepted snapshot input fingerprint |
|---|---|
| TH04 | `7833f05f267e8b892799eece05dc3c23fa03982f4d9a54cb8581f177f11cfbce` |
| TH08 | `15322833ad84c2b3ca169db0685f979adc20a4cf6b6d6d5c21167c25af6acb95` |
| TH095 | `e63dbd5991ad2d95dc9dc1d2821f86ff2bd8fbe4ec7a9d4a83e3ecaf337216af` |
| TH105 | `a9855b54dc56342e971c99f00e066ebde0da734402dd327ca14d9d19b39de21d` |

The policy document, registry document, all four receipt documents, and all
four materialized snapshots passed their Draft 2020-12 JSON Schemas. The
registry tests also cover changed invalid-candidate bytes, missing and
symlinked artifacts, storage-key mismatch, stale source, changed normalized
claims, dirty-source policy, post-construction artifact and freshness changes,
and an exclusive-replay/shared-query lock conflict.

TH095 was replayed in a detached worktree because its main worktree was moving
during validation. The temporary worktree was deleted after the complete
registry and query checks. Mapping the same current store to the later active
TH095 state produced three accepted entries and one rejected TH095 entry; the
reasons were `source-snapshot-stale`, `invocation-plan-stale`, and
`toolchain-environment-stale`. An older six-receipt store produced zero
accepted entries after the runner changed; all six were rejected as
`runner-implementation-stale`. These are expected fail-closed results, not
attempts to preserve compatibility with obsolete passes.

The second snapshot is retained in the ignored local
`.factory/acceptance-registry-v1` store. Like the initial store, it can contain
private target and toolchain evidence and is not publishable by default. The
TH095 receipt remains integrity-verifiable after worktree removal, but live
freshness requires reconstructing the same source and environment binding.
