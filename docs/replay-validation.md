# Controlled replay validation

This document records the first live integration validation of the
factory-controlled replay contract. It is deliberately narrow: four known
exact claims test four materially different repository/toolchain workflows.
It does not claim that any game is complete or that every native oracle is
sound.

## Validation snapshot

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
