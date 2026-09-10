# Cross-Game Knowledge Base

The factory is the shared knowledge layer above individual game repositories.
Its job is not to copy every note. It preserves rules that affect truth,
acceptance, provider selection, or workflow safety across projects.

This published catalog is a different authority from the canonical
`.reconstruction/game-knowledge.json` input owned by one game repository. The
game-local format, its intentionally weaker vocabulary, and its Web-write
boundary are specified in [`game-knowledge.md`](game-knowledge.md).

The machine-readable catalog is packaged at
`src/reconstruction_factory/knowledge/catalog.json`. Every entry states its
scope, evidence fixtures, operational consequences, and limitations. The
loader verifies all fixture references and rejects a `verified` entry without
evidence.

## Status vocabulary

- `verified`: the statement has one or more executable historical fixtures.
- `provisional`: bounded evidence exists, but the statement is not ready to
  impose a general acceptance rule.
- `unknown`: the question is intentionally open. It cannot impose verified
  consequences.
- `superseded`: retained for history but no longer active guidance.

These statuses apply only to the Factory-published catalog. Game-local entries
use `observed`, `reproduced`, `unknown`, and `superseded`; they cannot declare
`verified` or `provisional` and cannot use the `all` scope.

## Scope vocabulary

`all` is reserved for ontology-level implications that do not depend on a
binary container or compiler. Narrower entries use provider IDs such as
`pc98-mz-omf`, `windows-pe-coff`, `borland16`, `msvc7`, and `msvc8-ltcg`.

A fixture from one game does not automatically prove that its mechanism occurs
in every game. The catalog may still record a universal logical implication—for
example, a target hash mismatch invalidates target binding—while its
limitations state how narrow the observed counterexample is.

## Querying

```bash
PYTHONPATH=src python3 -m reconstruction_factory knowledge
```

The command emits deterministic JSON including status counts. The initial
catalog contains ten verified rules and two explicit unknowns. The unknown
runtime and general LTCG-reproduction entries are deliberate boundaries, not
missing data to be filled by guesses.

TH095's whole-build lesson is backed by paired historical fixtures: one
checkpoint compiles 88/88 production units but fails with unresolved symbols,
while the later checkpoint compiles 88/88 and links cleanly despite retaining
696 exact functions out of 697 source-present functions. Together they preserve
the independence of exactness, product closure, whole-image equality, and
runtime validation.

## Publication boundary

Neither GPT-web nor the public MCP can publish, nominate, or promote game-local
input. `factory_query_knowledge` reads only the catalog packaged with this
Factory repository. The game-local validator has no write side effect.

For now, cross-game extraction is a later human/local-Codex analysis of the
completed or otherwise stable game repository, including its Git history,
scripts, tests, receipts, durable local knowledge, failures, and limitations.
No automatic promotion workflow is implemented.

## Future promotion rule

Promoting a catalog entry to `verified` requires:

1. immutable source commit and repository-relative evidence paths;
2. a minimal fixture containing only the facts needed by the rule;
3. a fail-closed evaluator with negative or unknown-evidence tests;
4. explicit scope and limitations;
5. passing manifest integrity, unit, and relevant live-parity validation.

Narrative archaeology can guide future work, but it does not become an active
factory rule until this promotion path is complete.
