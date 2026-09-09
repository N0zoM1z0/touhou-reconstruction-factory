# Touhou Reconstruction Factory

This repository is the control plane for evidence-first Touhou reconstruction
projects. It defines a language-neutral truth kernel, composes compatible
platform and toolchain providers, imports existing repositories without
modifying them, and preserves historical oracle failures as regression
contracts.

The factory is not a source monorepo and is not a directory copier. A project
specification selects a coherent family of providers and produces a
`ReconstructionKit` whose claims, oracle results, artifacts, gates, and
workflows share one vocabulary.

The architecture and repository archaeology are recorded in
[`docs/factory-analysis.md`](docs/factory-analysis.md). The normative vocabulary
is in [`docs/ontology.md`](docs/ontology.md).

## Development

The v0 foundation has no runtime dependencies outside Python 3.11 or newer.

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m reconstruction_factory --help
PYTHONPATH=src python3 -m reconstruction_factory inspect /path/to/repo --summary
PYTHONPATH=src python3 -m reconstruction_factory fixtures
PYTHONPATH=src python3 -m reconstruction_factory knowledge
PYTHONPATH=src python3 -m reconstruction_factory verify-provenance --help
```

Game repository adapters are read-only. They never run a compiler, mutate a
ledger, or infer an exact claim from a progress percentage.

The governing principle is **accuracy before completeness**. Unknown or
incomplete state is valid output. Guessed identity, extent, origin, ownership,
or exactness is not.

The existing-repository import contract and live parity procedure are described
in [`docs/adapters.md`](docs/adapters.md).

Cross-game lessons are retained as hash-pinned, executable counterexamples.
Their evidence and verdict semantics are described in
[`docs/regression-fixtures.md`](docs/regression-fixtures.md).
Verified lessons and explicit unknowns are indexed by scope in the
[`cross-game knowledge base`](docs/knowledge-base.md).
