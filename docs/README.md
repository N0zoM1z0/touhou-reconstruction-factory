# Documentation authority map

This index separates current operating contracts from historical evidence.
Read it before using a document to direct an agent or change the Factory.

## Authority order

When two sources appear to conflict, use this order:

1. current source code, schemas, policy documents, machine-readable contracts,
   and executable checks;
2. the current design and workflow documents listed below;
3. dated validation and bootstrap records, only for the checkpoint they name;
4. the architecture working paper and repository archaeology, as rationale and
   discovery history.

No recorded receipt ID, accepted count, provider result, repository commit, or
latency is a live fact. Inspect current Git state and query the current Factory
service when the task depends on live state.

## Current operating documents

| Concern | Document |
| --- | --- |
| Shared terms and Truth Kernel | [`ontology.md`](ontology.md) |
| Independent verification planes | [`verification-planes.md`](verification-planes.md) |
| Platform and toolchain capabilities | [`providers.md`](providers.md) |
| Existing-repository imports | [`adapters.md`](adapters.md) |
| Replay evidence envelope | [`oracle-receipts.md`](oracle-receipts.md) |
| Receipt admission and accepted facts | [`acceptance-registry.md`](acceptance-registry.md) |
| Durable replay lifecycle | [`durable-jobs.md`](durable-jobs.md) |
| Shared GPT-web MCP surface | [`mcp-server.md`](mcp-server.md) |
| Live repository Bash and checkpoints | [`repository-work-provider.md`](repository-work-provider.md) |
| Optional isolated experiments | [`workspace-provider.md`](workspace-provider.md) |
| Target-attested IDA/Ghidra operations | [`analysis-provider.md`](analysis-provider.md) |
| Agent autonomy and evidence boundaries | [`agent-autonomy.md`](agent-autonomy.md) |
| Semantic campaign workflow | [`semantic-reconstruction.md`](semantic-reconstruction.md) |
| Dirty-work recovery and artifact lifecycle | [`worktree-recovery-and-analysis-artifacts.md`](worktree-recovery-and-analysis-artifacts.md) |
| New-game and native-provider bootstrap | [`new-game-bootstrap.md`](new-game-bootstrap.md) |
| Game-local knowledge input | [`game-knowledge.md`](game-knowledge.md) |
| Reviewed cross-game knowledge | [`knowledge-base.md`](knowledge-base.md) |
| Historical regression contracts | [`regression-fixtures.md`](regression-fixtures.md) |
| Release and live validation procedure | [`validation.md`](validation.md) |
| Plugin packaging and private deployment | [`gpt-web-plugin.md`](gpt-web-plugin.md) |

Use [`../contracts/README.md`](../contracts/README.md) to select the current
machine-readable session contract and [`../prompts/README.md`](../prompts/README.md)
to select a launch prompt. Standalone prompts remain complete even when ChatGPT
does not inject a plugin skill.

## Point-in-time evidence records

These files preserve measurements and failure history. Their dates, commits,
counts, IDs, and availability observations must not be presented as current
without a new observation:

- [`replay-validation.md`](replay-validation.md): chronological replay,
  acceptance, durable-job, and performance checkpoints beginning 2026-09-09;
- [`overnight-web-pilot-2026-09-11.md`](overnight-web-pilot-2026-09-11.md): the
  first concurrent TH09 exact and TH095 semantic Web pilot;
- [`th10-native-ghidra-bootstrap-2026-09-12.md`](th10-native-ghidra-bootstrap-2026-09-12.md):
  the TH10 repository and native-Ghidra activation record; and
- the dated `Recorded ...` sections in [`validation.md`](validation.md) and the
  historical deployment checkpoints in [`gpt-web-plugin.md`](gpt-web-plugin.md).

## Architecture archaeology

[`factory-analysis.md`](factory-analysis.md) is the original 2026-09-10 working
paper built from repository and commit archaeology. It explains why the
Factory exists and preserves rejected design directions. It is not a current
runbook, contract index, live inventory, or implementation-status report.

Keep historical evidence when it explains a durable invariant. Correct its
classification or add a later record rather than silently rewriting a past
observation into present tense.
