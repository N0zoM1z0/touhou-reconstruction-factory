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

The core has no runtime dependencies outside Python 3.11 or newer. The GPT-web
service uses the optional, version-bounded MCP v2 dependency.

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m reconstruction_factory --help
PYTHONPATH=src python3 -m reconstruction_factory inspect /path/to/repo --summary
PYTHONPATH=src python3 -m reconstruction_factory fixtures
PYTHONPATH=src python3 -m reconstruction_factory knowledge
PYTHONPATH=src python3 -m reconstruction_factory verify-provenance --help
PYTHONPATH=src python3 -m reconstruction_factory replay --help
PYTHONPATH=src python3 -m reconstruction_factory verify-receipt --help
PYTHONPATH=src python3 -m reconstruction_factory acceptance-registry --help
PYTHONPATH=src python3 -m reconstruction_factory inspect-accepted --help
PYTHONPATH=src python3 -m reconstruction_factory accepted-knowledge --help
PYTHONPATH=src python3 -m reconstruction_factory.service_cli --help
python3 -m pip install -e '.[mcp]'
touhou-reconstruction-factory-mcp --help
```

Game repository adapters are read-only. They never run a compiler, mutate a
ledger, or infer an exact claim from a progress percentage. The separate
`replay` command may create native ignored build products under an exclusive
repository lock; it rejects any change to tracked or non-ignored source state.

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

Factory-controlled replay and content-addressed evidence are specified in
[`docs/oracle-receipts.md`](docs/oracle-receipts.md).
The first live TH04/TH08/TH095/TH105 replay matrix and its exact limitations
are recorded in [`docs/replay-validation.md`](docs/replay-validation.md).
Only receipts admitted by an explicit live policy can enter accepted snapshots
or receipt-backed knowledge queries; see the
[`acceptance registry contract`](docs/acceptance-registry.md).

Long replays can now be submitted as SQLite-backed durable jobs and executed by
a separate worker. Job completion, oracle pass, and policy acceptance remain
three different states. The typed MCP v2 surface lets GPT-web submit, reconnect,
page complete evidence, and query only accepted facts without receiving shell,
working-directory, or raw-path authority. See
[`durable replay jobs`](docs/durable-jobs.md) and the
[`GPT-web MCP service`](docs/mcp-server.md).
