# Historical Regression Fixtures

Historical fixtures are the first executable layer of the factory's shared
cross-game knowledge base. Each fixture records a small fact that was proved in
an existing reconstruction repository and the verdict that a factory contract
must produce from that fact.

Fixtures are deliberately narrower than project status. TH04, TH08, TH095, and
TH105 need not be complete for a boundary error, target-identity change, or
relocation-content mismatch to be established. A fixture says only what its
inputs prove.

## Integrity and provenance

Every fixture contains:

- a full 40-character source commit, not a branch name;
- repository-relative evidence paths;
- a bounded observation that distinguishes recorded fact from interpretation;
- exact input values and an expected verdict;
- a SHA-256 entry in the packaged manifest.

The loader rejects malformed envelopes, unsafe provenance paths, unknown
fields, unlisted fixture files, missing fixture files, and digest changes. The
Python evaluator then validates every contract-specific field. The JSON Schema
documents the stable interchange envelope; the evaluator is stricter about the
shape of each contract input.

The fixtures store only structural metadata, hashes, counts, and short factual
descriptions. They do not copy executable bodies or other copyrighted payloads.

## Verdict semantics

`pass` means the complete stated contract is satisfied. `fail` means observed
evidence contradicts the tested claim. `incomplete` means the available
coverage cannot support acceptance. `error` is reserved for an oracle that
could not execute; malformed fixture data raises a validation error instead.

This distinction is central to accuracy-first operation:

- TH04's five-byte disassembler boundary is `incomplete`, because it does not
  cover the independently accepted 398-byte function extent.
- TH08's relocated `0.0` literal is `fail`, because target bytes at the same
  destination prove `128.0`.
- TH095's historical link is `fail` for whole-build closure even though all 88
  source objects compiled and 696 functions were exact.
- TH105 evidence bound to the earlier executable is `fail` against the active
  target even though both manifests use the string `1.06a`.
- TH105 physical ownership arithmetic may be established while exactness stays
  `incomplete`; owned bytes never become exact bytes implicitly.
- TH08 source-present counts are address-cardinality counts; one implemented
  constructor name covers two distinct target functions.
- TH04 toolchain identity covers fourteen required hash surfaces. Pinning only
  the compiler executable leaves identity coverage `incomplete`.
- TH105's retained standalone VC8 giant-root candidate is `fail`, because 239
  byte differences remain. Different LTCG context explains the bounded search
  gap but cannot erase an observed byte mismatch.
- TH04 exact evidence rebound from one unit to another is `fail` even when all
  required oracle IDs say pass; evidence scope is part of the truth claim.
- TH04's mutable DOS tool probes use distinct case-insensitive, 8.3-safe
  workspaces for concurrent invocations.

## Initial contracts

| Contract | Protected inference | Initial evidence |
| --- | --- | --- |
| `boundary-coverage` | A tool-created function is a complete source boundary | TH04 Gengetsu foreground renderer |
| `relocation-destination-content` | Matching relocation form and destination imply matching referenced data | TH08 item auto-collection threshold |
| `whole-build-closure` | Function or object success implies a linked product | TH095 whole-build audit |
| `target-binding` | A version label is sufficient target identity | TH105 v1.06a target reset |
| `owned-extent-exactness` | A provisional main span is complete ownership, or ownership implies exactness | TH105 Reimu and Sakuya multi-chunk roots |
| `source-presence-cardinality` | A source-name set has the same cardinality as target functions | TH08 overloaded `Float3` constructors |
| `toolchain-surface-coverage` | Hashing the compiler alone identifies the exact toolchain | TH04 Borland/TASM/TLINK profile |
| `codegen-context-comparison` | Similar source shape or a different compiler context can waive observed byte differences | TH105 VC8 LTCG giant root |
| `exact-promotion-evidence` | Passing evidence can be reused across units or extents | TH04 adversarial promotion tests |
| `workspace-isolation` | Concurrent mutable tool invocations may share an output workspace | TH04 Borland attestation probes |

These contracts are platform-neutral even when their first counterexample is
platform-specific. Platform and toolchain providers decide whether a contract
is applicable; they do not redefine its truth semantics.

## Running the suite

```bash
PYTHONPATH=src python3 -m reconstruction_factory fixtures
```

The command verifies manifest coverage and hashes before evaluating anything.
It exits nonzero if any observed verdict or ordered diagnostic list differs
from the fixture expectation.

Fixture source objects can also be checked against explicit local clones:

```bash
PYTHONPATH=src python3 -m reconstruction_factory verify-provenance \
  --repository th04=/path/to/th04 \
  --repository th08=/path/to/th08 \
  --repository th095=/path/to/th095 \
  --repository th105=/path/to/th105
```

This verifies the clone's `origin`, resolves every full commit, and requires
every evidence path at that commit to be a Git blob. It reads committed objects
rather than trusting the current working tree.

An alternate fixture directory can be supplied for tests or review:

```bash
PYTHONPATH=src python3 -m reconstruction_factory fixtures --directory path/to/fixtures
```

Adding a fixture requires source archaeology, an immutable commit, precise
evidence paths, a contract evaluator, negative tests, and a regenerated
manifest digest. A plausible story without those elements belongs in an
`unknown` research note, not in the verified suite.
