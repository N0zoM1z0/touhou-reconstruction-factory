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

## System and reconstruction flow

```mermaid
flowchart LR
    H["Human<br/>scope · stop condition · release"]:::human --> I["Installed Factory Plugin<br/>four bundled skills<br/>registered ChatGPT app binding"]:::control
    K[("Factory repository memory<br/>ontology · providers · adapters<br/>fixtures · knowledge · prompt · skills")]:::memory --> I
    I --> W["GPT-web agent<br/>factory-reconstruction skill<br/>resumable bounded session"]:::agent
    W --> D["One shared Factory MCP<br/>discover IDs · read adapter snapshot<br/>candidate claims · knowledge · resume"]:::control
    K --> D
    D --> C["Selected canonical game repository<br/>committed HEAD + machine-readable ledgers<br/>original target identity"]:::repo
    C --> E["Target-attested evidence<br/>committed source + bounded IDA/Ghidra<br/>analysis exactness credit: none"]:::evidence
    E --> S["Disposable source workspace<br/>natural C/C++ · focused checks<br/>source-only Bash · candidate diff"]:::work
    S -.-> G["Game-local knowledge input<br/>observed · reproduced · unknown<br/>publication authority: none"]:::repo
    S -->|"complete diff + workspace ID"| L["Local Codex handoff<br/>review · apply · test · commit<br/>new canonical game source"]:::human
    G -->|"same reviewable diff"| L
    L --> J["Durable canonical replay<br/>discovered claim + source · target<br/>toolchain · extent bound receipt"]:::oracle
    J --> A{"Integrity + freshness<br/>+ live policy<br/>accepted?"}:::gate
    A -->|"Rejected / invalid / stale"| X["Preserve diagnostics<br/>artifacts + explicit unknowns<br/>define the next bounded task"]:::reject
    A ==>|"Accepted"| T["Truth Kernel<br/>current accepted facts<br/>and accepted snapshots"]:::done
    T --> Q["GPT-web query / next task<br/>report receipt scope<br/>never inflate completeness"]:::agent
    X --> Q
    L -.-> P["Later local Codex retrospective<br/>history · scripts · tests · receipts<br/>Factory publication not automated"]:::memory
    P -.-> K

    P98["PC-98 era family<br/>TH01–TH05<br/>currently validated: TH04"]:::platform --> C
    PE["Windows PE era family<br/>TH06+<br/>currently validated: TH08 / TH095 / TH105"]:::platform --> C

    B["Registered read-only<br/>IDA / Ghidra bridge"]:::evidence -->|"independent target attestation"| E
    U["Dirty · untracked · ignored<br/>private targets / toolchains"]:::reject -.->|"observed, never copied"| S
    L -.-> R["Later local-only phase<br/>game runtime validation + portability"]:::platform

    classDef human fill:#fff1c2,stroke:#b7791f,color:#3b2f0b,stroke-width:2px;
    classDef agent fill:#ede9fe,stroke:#7c3aed,color:#2e1065,stroke-width:2px;
    classDef memory fill:#dbeafe,stroke:#2563eb,color:#172554,stroke-width:2px;
    classDef control fill:#e0e7ff,stroke:#4338ca,color:#1e1b4b,stroke-width:2px;
    classDef evidence fill:#cffafe,stroke:#0891b2,color:#083344,stroke-width:2px;
    classDef work fill:#fef3c7,stroke:#d97706,color:#451a03,stroke-width:2px;
    classDef oracle fill:#dcfce7,stroke:#16a34a,color:#052e16,stroke-width:2px;
    classDef gate fill:#f3f4f6,stroke:#4b5563,color:#111827,stroke-width:2px;
    classDef reject fill:#fee2e2,stroke:#dc2626,color:#450a0a,stroke-width:2px;
    classDef done fill:#ccfbf1,stroke:#0f766e,color:#042f2e,stroke-width:2px;
    classDef platform fill:#f5f3ff,stroke:#6d28d9,color:#2e1065,stroke-width:2px;
    classDef repo fill:#f8fafc,stroke:#475569,color:#0f172a,stroke-width:2px;
```

The main row is the normal reader journey from scope to accepted truth. Solid
arrows are operational or data-flow edges, dashed arrows mark excluded inputs
or later out-of-scope work, and the thick **Accepted** edge is the only route
into truth. There is intentionally no direct edge from an imported claim,
analysis result, or workspace test to the Truth Kernel.

The same control-plane architecture serves both eras. PC-98 and Windows PE use
different platform/toolchain providers, adapters, target identities, and replay
drivers; they converge only on the shared ontology, receipt envelope,
acceptance policy, durable workflow, and GPT-web interface.

## Development

The core has no runtime dependencies outside Python 3.11 or newer. The GPT-web
service uses the optional, version-bounded MCP v2 dependency.

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m reconstruction_factory --help
PYTHONPATH=src python3 -m reconstruction_factory inspect /path/to/repo --summary
PYTHONPATH=src python3 -m reconstruction_factory fixtures
PYTHONPATH=src python3 -m reconstruction_factory knowledge
PYTHONPATH=src python3 -m reconstruction_factory validate-game-knowledge --help
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
Game repositories use a separate, non-publishing
[`game-local knowledge input`](docs/game-knowledge.md) that GPT-web may update
only as part of a reviewable workspace diff.

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
page complete evidence, and query only accepted facts. It also provides
capability-addressed disposable source workspaces: bounded repository primitives
plus arbitrary Bash isolated from the host, canonical worktree, ignored targets,
credentials, and network. See
[`durable replay jobs`](docs/durable-jobs.md) and the
[`GPT-web MCP service`](docs/mcp-server.md).

Workspace source development and verification remain different authorities. A
workspace exports a tested reviewable diff; a local operator applies it to the
game repository, and only a later canonical replay receipt can enter the Truth
Kernel. The exact boundary is specified in the
[`disposable workspace provider`](docs/workspace-provider.md).

IDA and Ghidra remain separate provisional authorities. The MCP analysis
gateway exposes only registered loopback bridges, factory-allowlisted read
operations, independent target binding, bounded/redacted output, and zero
exactness credit. See the [`attested analysis provider`](docs/analysis-provider.md).

The repository also publishes a minimal plugin that combines the remote MCP
connection with an end-to-end reconstruction workflow plus separate analysis,
source-workspace, and evidence-preserving replay skills. A reusable short prompt
and a complete standalone prompt live in
[`prompts/gpt-web-reconstruction.md`](prompts/gpt-web-reconstruction.md).
The single-user deployment
and first TH105 web test are documented in
[`GPT-web plugin and Funnel deployment`](docs/gpt-web-plugin.md).

Run the complete local release gate with the MCP-enabled service environment:

```bash
PYTHONPATH=src .venv/bin/python scripts/validate-release.py
```

The deployed endpoint has a read-only validation mode and explicit opt-in live
analysis, disposable-workspace, and TH105 replay checks:

```bash
PYTHONPATH=src .venv/bin/python scripts/validate-live-mcp.py
PYTHONPATH=src .venv/bin/python scripts/validate-live-mcp.py --all
```

The second command creates and discards a temporary TH105 workspace and submits
one canonical TH105 smoke replay. See [`docs/validation.md`](docs/validation.md)
for the validation contract and latest recorded run.
