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

## Initial contracts

| Contract | Protected inference | Initial evidence |
| --- | --- | --- |
| `boundary-coverage` | A tool-created function is a complete source boundary | TH04 Gengetsu foreground renderer |
| `relocation-destination-content` | Matching relocation form and destination imply matching referenced data | TH08 item auto-collection threshold |
| `whole-build-closure` | Function or object success implies a linked product | TH095 whole-build audit |
| `target-binding` | A version label is sufficient target identity | TH105 v1.06a target reset |
| `owned-extent-exactness` | A provisional main span is complete ownership, or ownership implies exactness | TH105 Reimu and Sakuya multi-chunk roots |

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

An alternate fixture directory can be supplied for tests or review:

```bash
PYTHONPATH=src python3 -m reconstruction_factory fixtures --directory path/to/fixtures
```

Adding a fixture requires source archaeology, an immutable commit, precise
evidence paths, a contract evaluator, negative tests, and a regenerated
manifest digest. A plausible story without those elements belongs in an
`unknown` research note, not in the verified suite.
