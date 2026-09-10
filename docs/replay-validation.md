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

## Durable job and MCP checkpoint

The durable service was validated again after its Python implementation was
frozen, using runner implementation digest
`3a90629a2731d7a6fa2420a58276ca348fccc1e0ff73d9386fa33d0080be337b`
and private service configuration digest
`06aa468a7bc9d5824221c6ced557d69cc5c76d941556c8f094c9546b900ea2ba`.
The private configuration used policy digest
`2c8e8eacece083a5941fb188cab76d15d9be72397ffe283a1db81413312b4b17`.
All four requests were submitted before a separate FIFO worker process was
started. A repeated TH08 submission with the same idempotency key returned its
original completed job and did not create a fifth job.

| Game | Job | Queue-time source | Receipt | Completion decision |
|---|---|---|---|---|
| TH04 | `job:da19c9ca156e48bf8900c3da0a018712` | commit `1fa8de07742255053299628213f0674d742a410c`, clean | `receipt:8c40bcd84e2911d07e8abcb3fdcbcc113f9389c0b3abeedb8be7939dae2b7331` | pass, accepted |
| TH08 | `job:fb7b77b163a744ffb2ea37e0ca569385` | commit `bd54d865ebbc9f7291b355d152b16cc4b7f5be59`, clean | `receipt:2c5ad0e61c467a3aef7862911a95d46a2cf24b39dffcb3bb9fd6d4fd067b46ff` | pass, accepted |
| TH095 | `job:0c264449e513429f8dcc0ded475d40d8` | commit `a298606a3e4452a5f7b79da88cd3f365ff459734`, dirty with three tracked modifications and two untracked files | `receipt:004351fa2646361ebb07ad62b7ecac16bd9a36839added6f55ba5493b1b19494` | pass, accepted |
| TH105 | `job:a3266052d50f4162876c64922ddc3e3a` | commit `20f993b7908d8a207a39cf13da8d7614b9a3b23f`, clean | `receipt:aa22fdee5e5e2eef2f0d0c82adb1f96c1c69e2bc39eab63daab279ea2a7f3e8d` | pass, accepted |

At fourth-job completion and again after a separate live rebuild, the registry
contained exactly four accepted candidates and no rejected or invalid
candidates, with identity
`registry:b327c0d5e00d3b46bee3332f4e51dfd1ee4f31d72d027ee7b89705e8f70b302f`.
The accepted-fact query returned exactly those four bounded results. TH04's
isolated double build remained leased and heartbeat-visible for about two
minutes; the shorter Windows jobs then completed from the same queue.

The TH095 acceptance is intentionally narrow. The queue-time source digest
bound its three tracked modifications and two untracked files, and the worker
observed exactly that state before and after replay. It proves the selected
24-byte claim for that live snapshot, not repository cleanliness, completion,
or any other function. An earlier checkpoint correctly rejected an older
TH095 receipt after the active worktree changed; freshness is recomputed and a
historical job outcome is never treated as permanently current.

The private TOML document, four replay specifications, four public job records,
four receipts, the registry, and four materialized snapshots were validated
offline against all nine published Draft 2020-12 schemas. The complete suite
contained 87 tests: 83 core tests plus four MCP tests. All 87 passed with MCP
SDK 2.2.0; the dependency-free core run also passed all 83 applicable tests and
skipped only those four optional MCP tests.

The real stateless Streamable HTTP endpoint accepted the ChatGPT-style
`server/discover` exchange for protocol `2026-07-28` and listed exactly 15
structured-output tools. None exposed a `command`, `cwd`, or filesystem `path`
argument. A missing bearer token returned HTTP 401, and an authenticated
request with a non-allowlisted Host returned HTTP 421. A 64-byte TH04 artifact
page returned exactly 64 bytes plus `next_offset`; the retained artifact was
still hashed in full before any bytes were returned.

Running an accepted-fact query from a different Python virtual environment can
correctly reject receipts because the resolved runtime/toolchain surface differs
from the worker environment. Production workers and the MCP process must use
the same factory installation and relevant environment.

## TH095 product-closure checkpoint: 2026-09-10

The first product-scoped replay used an isolated clean clone at immutable TH095
commit `3442dcf29d9e0b5bef384a49bd0c9ad32a711826`. The private canonical target
was copied into the ignored `resources/` path, while the pinned VC7.1 package
was reused read-only through `TH095_MSVC71_ROOT`. The concurrently active TH095
worktree and its four untracked files were not changed.

The adapter imported one extent-free `product` subject and
`claim:th095-main:product:whole-build-closed` with
`evidence_class=unknown`, plus zero imported Oracle results. Factory driver
`th095-vc71-whole-build-v1` then ran the native `scripts/build-whole.py` from a
clean output graph. It observed:

- clean source commit `3442dcf...`, 278 bound source files, and identical
  before/after source digest
  `55d0641ee0055843917a98b069e4a9b48f3612452c970d9398624bc7068fc6e3`;
- canonical target SHA-256
  `bb54f6fc54f0eeffaec416ca9f64aef32b5f59b7427fa5a6579f6538e0eddc07`
  before and after replay;
- pinned compiler `13.10.3077` / SHA-256 `2ecf86a3...2515` and linker
  `7.10.3077` / SHA-256 `0d5f9712...3e3c` with verified attestation;
- complete `production-translation-units` coverage of 88/88 across two
  canonical profiles;
- a zero-unresolved, non-`/FORCE*` link and a report-bound 780,288-byte PE32
  i386 Windows GUI output.

The replay took 655,511 ms, returned `pass` with no acceptance errors, and
sealed receipt
`receipt:1ef34f8f9a7eff7abd142f10510bcdc6fc140e9254a0e8de661d7b141c3c7c04`.
Live receipt verification returned `integrity=pass` and `fresh=true`. The
`strict-live-v1` registry then classified exactly one candidate as accepted,
with zero rejected or invalid candidates. The final policy requires verified
native attestation for this product driver and has digest
`8f45b3e395b79502234b2a805c6ee797c547dc96fa654a5ba7092104e1108e88`;
the resulting registry is
`registry:0a58bcdcf8787ca1627e341d72e3a16c6ef35efb06bd562a160d90a15718881d`.
An accepted-fact query returned exactly that `whole_build_closed` fact.

The isolated output SHA-256 was
`1b66423b0ec969584fa05395352ff496e0471f5597f99d13fe3a9d14111b36f0`,
which differs from the `8e0096...fac97f` artifact recorded by the game
repository for another build of the same source checkpoint. The cause of the
binary difference was not investigated in this bounded validation. The result
is intentionally still a product-closure pass: the claim requires a complete
cold build, clean link, and bound executable format, not deterministic output
or whole-image equality. No runtime storage or runtime-scenario status was
derived from it.

The temporary clone and evidence store are not public retained evidence. The
receipt and registry IDs above identify this local run, while the controlled
driver, tests, paired historical fixtures, and reproduction procedure are the
committed regression surface.

## Request-scoped freshness acceleration: 2026-09-10

High-throughput correctness depends on a short, layered feedback loop: run
cheap exact identity checks first, observe each live dependency once, and run
expensive native builds only when new evidence is required. Keep every
applicable Oracle; remove redundant observation and return the narrowest
sufficient feedback. Speed must not come from accepting a weaker fact.

Freshness remains mandatory under `strict-live-v1`, but repeated receipts no
longer repeat identical live observations inside one registry build. A single
request-scoped observation snapshot now reuses each repository adapter result,
source binding, canonical target digest, toolchain component digest,
environment binding, runner digest, and driver-version digest. Every receipt
still independently passes document/content integrity, artifact integrity,
policy, claim/subject, source, target, toolchain, invocation, coverage, and
acceptance-error checks. No verdict is persisted or reused across registry
requests, and no time-to-live or filesystem-metadata shortcut can turn a
changed input into a fresh result.

Replay-driver TOML parsing is cached separately by the exact input bytes. A
same-size or same-mtime mutation therefore cannot reuse a parsed manifest; new
bytes are parsed and participate in the normal driver/input digests.

Before this change, two consecutive public
`factory_get_acceptance_registry` calls over 31 candidates took 15.493 and
14.132 seconds. After the final runner-fingerprint rollover of the active TH095
facts, three calls over the larger 59-candidate store took 2.683, 1.897, and
1.918 seconds. The final registry contained 14 accepted TH095 results—13
function-exact claims plus one 88-source product-closure claim—and 45 historical
rejected candidates. The optimization therefore improved this observed live
query by about 5.3–8.2 times while evaluating almost twice as many receipts and
preserving the same fail-closed policy.

The accepted-facts materialization path originally repeated freshness work
after constructing the registry and took 7.125 seconds for TH095. Sharing the
same request-scoped observations across that second check reduced three final
calls to 2.262, 2.171, and 2.169 seconds. All returned the same 14 facts and the
same registry identity. This cache is deliberately scoped to one request: a
later request observes the live repositories, tools, and artifacts again.

The registry still scales linearly with receipt documents and their unique
artifacts. If the retained store grows enough for that cost to matter, the next
safe step is a content-addressed per-repository observation index and scoped
query surface, not disabling live freshness.
