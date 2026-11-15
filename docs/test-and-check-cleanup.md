# Cleaning up tests and checks in a reconstruction repository

A check earns its place only if it can catch a real mistake that nothing
cheaper already catches. In a reconstruction repository the real mistakes
are: the wrong original binary, an incomplete function extent, changed bytes,
wrong relocation types/targets/addends, and an exact function silently
regressing. Source wording, file layout and recorded numbers are not on that
list. Exactness evidence is the canonical original-bound comparison; tests
that restate it in another form only add cost.

TH09 is the worked example: removing 429 test files and 115 per-owner
scripts took `ci.py --full` from 5 min 15 s with 117 standing failures to
about 5 s with 82 passing tests, and the 11 nonexact owners moved to one
data-driven ratchet (TH09 `scripts/check-frontier.py` with
`config/frontiers.toml`).

## 1. Measure

```bash
time python3 -m pytest -q -p no:cacheprovider --durations=30 -rf tests > full.txt
grep ^FAILED full.txt | sed 's/::.*//; s/FAILED //' | sort | uniq -c | sort -rn
```

A suite with many failures that nobody fixes is not a signal. Agents cannot
tell new failures from old ones and end up stashing and diffing failure lists
around every change.

## 2. Classify every test file

For each test file record whether it reads source files (`'src/*.cpp'`,
`ROOT / 'src' / ...`), how many string assertions it makes
(`assertIn('...')`, `assertNotIn('...')`), which repository scripts it loads
(match both `scripts/x.py` and `'scripts' / 'x.py'`), and whether it passes.

| Reads source | Loads a script | Typical content | Default |
| --- | --- | --- | --- |
| yes | no | source-spelling snapshot | delete |
| yes | per-owner script | per-owner guard or evidence pin | delete with the script |
| no | generic tool | parser, comparator, wrapper, ledger | keep |
| no | per-owner inspector | inspector unit tests | delete with the inspector |

Sample several files from each group by hand before acting on the pattern
match.

## 3. Delete when any of these holds

- **Spelling.** The test asserts that source contains or lacks a string: a
  cast form, a variable name, `volatile`, an include. Spelling is not
  behaviour, and these tests block natural-source cleanup even when the
  compiled bytes are identical.
- **Duplicate of a stronger check.** It asserts that
  `offsetof(X, f) == 0x1C` appears in source when the `static_assert` is
  already compiled, re-checks manifest sizes or relocation counts that the
  ledger validator checks, or re-checks bytes the canonical comparison
  already proves.
- **Pinned residual.** It hard-codes a nonexact owner's current byte offsets,
  field deltas or difference counts in tests or script constants, so every
  improvement needs test edits. Replace these with one ratchet (section 5).
- **Belongs to a deleted script.** One-off inspectors, probes and reports for
  owners that are already exact are redundant with the canonical comparison.
- **Failing and unmaintained.** A test that has been red for a long time is
  evidence that nothing relies on it.

## 4. Keep

Tests that exercise shared tooling on both success and failure paths:
rejection of a wrong target or drifted toolchain pins; missing or extra COFF
symbols; wrong relocation type, target or addend; stale or ambiguous ledger
rows; broken documentation links; committable private binaries; scoped
replay selecting the right exact units; and the CI command itself. Keep the
ledger and documentation validators.

## 5. Replace per-owner guards with one ratchet

Keep a single data file listing each nonexact function's source, pinned
profile, symbol, address, size, original-extent SHA-256 and the set of byte
offsets that currently differ after relocation fields are masked. One script
rebuilds the functions and fails if any byte that matched before now
differs or the size changes; a strictly smaller residual is reported and
recorded with `--update`. Recording progress is then a one-line data change.
The ratchet is diagnostic only: exact credit still comes from a canonical
unit and its complete comparison.

Test the ratchet with one passing case, one deliberate regression, one
improvement plus `--update`, and one unknown name.

## 6. Before deleting

1. `grep` the scripts you keep for the names of scripts you plan to delete,
   including `spec_from_file_location` loads, `subprocess` calls and shell
   wrappers, and confirm the exact-proof chain (build unit, compare unit,
   scoped replay, target verification, ledger validation) uses none of them.
2. `grep` ledgers (`config/*.csv`, `config/*.toml`) for script names.
   Evidence columns should name only the generic pipeline; update prose
   notes that mention deleted scripts.
3. Write and test the ratchet before removing the guards it replaces.
4. Update the handoff, tool table, architecture notes and `AGENTS.md`
   routing so no instruction names a deleted script.
5. Finish with the full tooling suite green in seconds and the ledger and
   documentation validators passing.
