# Game-Local Knowledge Input

## Authority boundary

Each game repository may keep compact, durable reconstruction knowledge at the
canonical path `.reconstruction/game-knowledge.json`. This document is input to
later human or local-Codex review. It is never a Factory publication request,
an Oracle result, an accepted fact, or a cross-game rule.

The boundary is machine-visible and fail closed:

- `document_type` is always `game-knowledge-input`;
- `authority` is always `game-local`;
- `factory_publication` is always `none`;
- every entry contains exactly one matching `game:<repository_id>` scope;
- `all`, `verified`, and `provisional` are not valid game-local vocabulary; and
- the public MCP has no tool that promotes this input into the packaged Factory
  catalog.

GPT-web may update this file directly in the registered live game repository
and include it in a coherent local `gpt-web:` checkpoint. An explicitly
disposable workspace may instead export a candidate diff for later local review.
Neither path publishes the content to the Factory catalog. Future cross-game
extraction remains a separate repository-history analysis and is intentionally
not implemented by this contract.

## Canonical document

The normative JSON Schema is
[`schemas/v1/game-knowledge-input.schema.json`](../schemas/v1/game-knowledge-input.schema.json).
New repositories can start from
[`templates/game-knowledge-v1.json`](../templates/game-knowledge-v1.json), replace
the repository ID, and retain an empty entry list until durable knowledge exists.

```json
{
  "$schema": "https://github.com/N0zoM1z0/touhou-reconstruction-factory/schemas/v1/game-knowledge-input.schema.json",
  "schema_version": 1,
  "document_type": "game-knowledge-input",
  "authority": "game-local",
  "factory_publication": "none",
  "repository_id": "th105",
  "entries": [
    {
      "id": "bounded-inspection-recipe",
      "kind": "recipe",
      "status": "reproduced",
      "statement": "Run the maintained repository script for this bounded inspection.",
      "scopes": [
        "game:th105",
        "subsystem:inspection"
      ],
      "evidence": [
        {
          "kind": "repository-path",
          "reference": "scripts/inspect.py",
          "note": "The maintained script implements the procedure."
        }
      ],
      "validations": [
        {
          "method": "python3 scripts/inspect.py",
          "result": "passed",
          "note": "The focused check exited successfully."
        }
      ],
      "limitations": [
        "This is a game-local procedure and grants no exactness credit."
      ],
      "superseded_by": []
    }
  ]
}
```

Entries are sorted by ID. Scopes and `superseded_by` are also sorted. Exact
fields reject accidental schema drift instead of silently dropping data.

## Entry vocabulary

Kinds describe what is being retained:

- `scoped-fact`: a fact useful within this game and its named target/subsystem;
- `recipe`: a repeatable local procedure;
- `pitfall`: a durable failure mode and its detector or workaround;
- `decision`: a game-local architecture or workflow choice;
- `unknown`: a question that must remain unresolved.

Statuses are deliberately disjoint from the published Factory vocabulary:

- `observed`: evidence supports the observation, but no repeatable validation is
  claimed;
- `reproduced`: at least one recorded validation passed;
- `unknown`: the entry and kind must both be `unknown`;
- `superseded`: one or more existing, acyclic replacement entry IDs are named.

Evidence kinds are `repository-path`, `commit`, `analysis-observation`,
`accepted-receipt`, and `external-reference`. Referencing an accepted receipt
does not copy its truth authority into the knowledge entry; the acceptance
registry remains the only live Truth Kernel admission authority.

Validations record a method, its actual `passed`, `failed`, or `unavailable`
result, and a note. They are records, not executable Factory tasks. A workspace
check remains candidate engineering evidence even when its result is `passed`.

Every entry requires at least one limitation. Non-unknown active entries require
evidence. The format has no confidence percentage, consequence, nomination,
promotion, or publication field that an agent can inflate.

## What belongs here

Add or replace an entry only when the information is likely to affect a future
game-local decision. Good inputs include stable ABI/source-shape observations,
repeatable build or analysis procedures, durable pitfalls, explicit decisions,
and unresolved ownership or extent questions.

Do not turn this file into a chronological journal. Session progress, raw
decompiler output, command transcripts, temporary addresses, and the current
next action belong in the replacement-style handoff or disposable workspace.
Exact target claims remain in claims and accepted receipts. Cross-game rules
remain in the Factory catalog.

## Local validation

Validate the document alone:

```bash
PYTHONPATH=/path/to/factory/src python3 -m reconstruction_factory \
  validate-game-knowledge .reconstruction/game-knowledge.json
```

During local review, also bind repository-path evidence and the registered ID:

```bash
PYTHONPATH=/path/to/factory/src python3 -m reconstruction_factory \
  validate-game-knowledge .reconstruction/game-knowledge.json \
  --repository-root . \
  --repository-id th105
```

Validation only accepts or rejects the input format. It has no publication side
effect and cannot modify either repository.
