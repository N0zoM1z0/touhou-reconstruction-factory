# Release and live validation

## Validation contract

The Factory has two complementary validation entry points.

`scripts/validate-release.py` is the portable release gate. Run it with the
same MCP-enabled Python environment used by the service:

```bash
PYTHONPATH=src .venv/bin/python scripts/validate-release.py
```

It fails on:

- Ruff or Git whitespace errors;
- any unit, integration, MCP, workspace, receipt, registry, adapter, provider,
  regression, or Web-workflow asset test failure;
- Python bytecode compilation errors;
- malformed tracked or untracked-nonignored JSON, TOML, or evaluation XML;
- broken CLI construction; or
- failure to build exactly one wheel through an isolated PEP 517 build.

The MCP dependency is mandatory for this gate. Running the test suite with a
Python environment that omits the optional dependency can legitimately skip MCP
tests, so the release script rejects that environment instead of reporting an
incomplete pass.

`scripts/validate-live-mcp.py` checks the deployed no-auth endpoint. Its default
mode is read-only:

```bash
PYTHONPATH=src .venv/bin/python scripts/validate-live-mcp.py
```

The default checks the exact 29-tool inventory, annotations and bounded schemas,
strict policy, all four registered adapters, imported-versus-accepted evidence
separation, live accepted snapshots, registry partition, explicit unknown
knowledge, and per-game historical fixtures.

Mutation and bridge checks are explicit:

```bash
PYTHONPATH=src .venv/bin/python scripts/validate-live-mcp.py --analysis
PYTHONPATH=src .venv/bin/python scripts/validate-live-mcp.py --workspace
PYTHONPATH=src .venv/bin/python scripts/validate-live-mcp.py --replay-th105
PYTHONPATH=src .venv/bin/python scripts/validate-live-mcp.py --all
```

The workspace check creates an idempotent TH105 committed-HEAD snapshot, rejects
path traversal, confirms the source sandbox cannot reach host home, host `/etc`,
ignored `.tools`, or the network, and confirms its Git metadata is read-only. It
then verifies command output and a candidate diff across a new MCP session,
removes its marker, requires a zero-byte final diff, and discards the workspace.

The replay check discovers rather than invents the known TH105 smoke claim. It
submits a durable job, requires `completed`, `pass`, and `accepted` independently,
then finds that exact receipt through the current accepted-facts query and checks
its events and artifacts. To re-check an existing submission without creating
another receipt, pass its original key:

```bash
PYTHONPATH=src .venv/bin/python scripts/validate-live-mcp.py \
  --all \
  --replay-idempotency-key <existing-identical-key>
```

## Recorded run: 2026-09-10

The MCP-enabled release gate passed all 108 tests with no skips. Ruff, bytecode
compilation, Git whitespace, three CLI construction checks, 29 JSON documents,
two TOML documents, two ten-scenario evaluation XML documents, and the isolated
wheel build also passed. The plugin manifest and all four bundled skills passed
the plugin-creator and skill-creator validators after cachebuster version
`0.3.0+codex.20260910004949` was generated.

The final public `--all` run observed the following adapter state:

| Repository | Adapter | Imported claims | Accepted oracle results | Historical fixtures |
|---|---|---:|---:|---:|
| TH04 | `th04-pc98-v1` | 4,393 | 0 | 4 |
| TH08 | `th08-vc7-ledgers-v1` | 6,925 | 0 | 2 |
| TH095 | `windows-pe-ledgers-v1` | 5,153 | 0 | 1 |
| TH105 | `windows-pe-ledgers-v1` | 10,735 | 2 | 4 |

Every adapter continued to import zero native `OracleResult` objects. The live
registry contained eight receipt candidates: two accepted, six rejected as
stale, and zero invalid. The two accepted TH105 results are separate fresh
receipts for the same narrow canonical claim; they are repeated evidence, not
two reconstructed functions. TH04, TH08, and TH095 still have no accepted live
oracle result.

Analysis probes succeeded with target attestation for `th04-ghidra`,
`th095-ghidra`, and `th105-ida`; all retained
`authority=provisional-semantic-analysis` and `exactness_credit=none`.
`th08-ida` failed closed during discovery because its active database did not
attest as TH08. The run recorded this as accurately unavailable rather than
substituting another target.

The final disposable-session check used workspace
`workspace:e3aac033403a4b17891c2e9e817e665d` and command
`command:59947db7670743bd8b85aaa2e78dc621`. It resumed through a new MCP
connection, recovered output and diff, returned to a zero-byte diff, and ended
discarded. A separate server-process restart test used workspace
`workspace:f499c79bb132477b84f8dc5b1f9bc572` and command
`command:fb774e27679f40efb1918a53f92ce685`; after restarting the MCP service it
recovered the same idempotent capability, command output, and diff, then also
returned to zero bytes and was discarded.

The accepted replay was recovered idempotently rather than submitted again:

- claim: `claim:th105-main:function:00401000:codegen-exact`;
- job: `job:45a319b18ad54f5cbf074699b87838d1`;
- receipt: `receipt:fb8ef9db855bab54bd46ac39398d477ddb40bb7d27a8ee2b4737ad985ada5878`;
- registry: `registry:c21f9a94ff6a52cb7e95cbee33395027a0590b7bddb14210d3dc52366f63517f`;
- state/verdict/decision: `completed` / `pass` / `accepted`;
- durable evidence: four ordered job events and four content-addressed
  artifacts.

After the restart, the MCP and worker services were active. The MCP retained
`NoNewPrivileges=yes`, `PrivateTmp=yes`, `TasksMax=768`, a 3 GiB memory cap,
zero swap, `UMask=0077`, and disabled core dumps. The Factory Funnel mapping
remained the fixed public path to the loopback MCP service; no additional
Factory MCP route was added. The pre-existing TH105 canonical dirty state
remained exactly five modified files plus the untracked
`src/ui/CNumberLifetime.cpp`; no validation workspace content entered it.

## Deliberate limitations

This run proves the current service contract and only the narrow TH105 replay
claim above. It does not prove whole-image closure, LTCG physical ownership,
runtime equivalence, game completeness, or any exact claim for TH04, TH08, or
TH095. Those remain unknown until a supported factory-controlled replay produces
a fresh receipt accepted by policy. Local validators prove the prompt assets,
plugin structure, and ten behavioral scenarios; they cannot prove that a
particular ChatGPT account has refreshed the new plugin version or will
automatically select the orchestration skill. Test that UI behavior in a new
conversation after refreshing the installed plugin, preferably by selecting it
explicitly with `@` for the first run.
