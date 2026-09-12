# GPT-web MCP Service

## Design boundary

The MCP server is the typed remote boundary for several separate authorities.
Its live-repository surface exposes current game state, broad Bash, repo-local
tools, and local Git checkpoints. Its replay surface submits durable jobs,
observes state, pages evidence, and queries accepted knowledge. Its optional
workspace surface provides capability-addressed disposable experiments. Its
analysis surface routes target-attested IDA/Ghidra operations. None of these surfaces
contains another definition of reconstruction success.

This improves on the exploratory
[`mcp_for_gptweb`](https://github.com/N0zoM1z0/mcp_for_gptweb) server while
retaining what it proved useful: headless operation, Streamable HTTP, Host
validation, simple GPT-web discovery, and a broad composition surface.

The old repository's history is valuable evidence:

- `8f38474` proved that basic Streamable HTTP plus Bash was immediately useful,
  but selected work through caller-controlled host paths and had no durable
  Factory observation;
- `0d4d47f` and `bed0c6f` proved TH08/IDA calls, but embedded game-specific
  operations in the transport;
- `96b0624` repaired GPT-web discovery;
- `198c2d3` reduced the tool surface, but command lifetime was still connection
  lifetime;
- `5a9de07` captured a useful reconstruction workflow, while synchronous output
  truncation could still discard the diagnostic tail.

The Factory never accepts an arbitrary caller-supplied host path. It maps a
stable repository ID to an operator-registered live worktree and exposes broad
Bash there. The runner sees dirty, untracked, ignored, target, Wine-prefix, and
toolchain state; changes and local Git commits persist. Its Bubblewrap process
has no network, so remote Git push is unavailable. Game-specific verification
behavior remains behind adapters and replay drivers. Command output, jobs, and
evidence survive MCP disconnects and server restarts.

This is an intentional autonomy correction based on the earlier repositories:
atomic tools add identity, schemas, and evidence strength, but do not replace a
general composition surface. See
[`agent-autonomy.md`](agent-autonomy.md).
The command/state contract and the transitional Wine profiles are specified in
[`repository-work-provider.md`](repository-work-provider.md).

## GPT-web workflow

For example, a model working on TH08 performs this sequence:

1. Call `factory_list_repositories` and select the stable `th08` registration.
2. Call `factory_list_claims(repository_id="th08", ...)` and select one imported
   candidate claim. This is not yet an accepted fact.
3. Call `factory_submit_replay` with a stable key such as
   `chat-8f3a-turn-17-claim-0042`. The call returns a durable job immediately.
4. The HTTP request may end. A separate local worker claims and executes the
   factory-controlled replay.
5. In this or a later conversation, call `factory_get_job(job_id)`. Continue
   polling while state is `queued`, `leased`, `running`, or
   `cancel-requested`.
6. For `completed`, inspect all three layers: job state, `receipt_verdict`, and
   `acceptance_decision`. Do not describe a rejected receipt as verified.
7. Use `factory_get_job_output_page` for diagnostics. Follow `next_offset` until
   it is null.
8. Use `factory_query_accepted_facts` or `factory_get_accepted_snapshot` when a
   later decision requires authoritative facts.

If GPT-web retries submission after a timeout, the same idempotency key returns
the original job. Changed arguments with that key fail visibly. If a worker
dies, the lease eventually fails closed; GPT-web can inspect events and submit a
new request after repository inspection.

For source development, GPT-web performs this sequence:

1. Select a returned repository ID and call
   `factory_get_repository_status` to capture the real starting HEAD and dirty
   state.
2. Use `factory_repository_run_shell` to read repository instructions and
   compose source edits, Git operations, Wine/toolchain builds, and diagnostics.
3. Inspect the returned before/after Git state. Nonzero exit and timeout leave
   filesystem changes in place; inspect before retrying.
4. Page output with `factory_get_repository_command_output` when needed.
5. Create reviewable English `gpt-web:` commits after coherent checked units.
   A commit is a resume/review checkpoint, never a receipt and never exactness.
6. Discover and replay only claims eligible for the committed source state.

For semantic reconstruction, use the specialized
[`semantic reconstruction workflow`](semantic-reconstruction.md). The optional
`factory_report_semantic_debt` tool binds a lexical routing report to live HEAD
and dirty state; it does not replace Bash search, target analysis, or model
judgment, and no count is a progress or completion claim. Semantic work follows
the target exact baseline and corresponding historical-platform product closure
so the exact and native product/runtime lanes can act as independent regression
oracles before portable products begin.

Use the disposable workspace tools only when an isolated committed-HEAD copy is
the intended experiment. Their complete isolation contract remains in
[`workspace-provider.md`](workspace-provider.md).

For semantic target analysis, first list providers for the repository and then
list the selected provider's operation schemas. Pass one discovered operation
and a JSON object string to `factory_analysis_call`. The response binds the
current adapter target, provider identity, operation, arguments, attestation, and
observation time while fixing `exactness_credit` to `none`. Native analysis for
TH09 goes directly from the shared Factory process to `ida-pro-mcp` over stdio.
TH10 uses the Factory-native fixed-grammar Ghidra command provider and its
game-bound headless project; it does not run another MCP or HTTP bridge. IDA's
discovered operations include non-byte database metadata edits, while TH10's
native Ghidra surface is currently read-only. Target-byte patching and legacy
bridges' host Bash tools remain absent. See
[`analysis-provider.md`](analysis-provider.md).

## Tools

| Tool | Effect |
| --- | --- |
| `factory_describe` | Show redacted configuration and policy identity. |
| `factory_list_repositories` | List registered repository IDs. |
| `factory_get_repository_status` | Inspect current live HEAD, branch, upstream, and dirty counts. |
| `factory_report_semantic_debt` | Page live-worktree-bound heuristic C/C++ semantic candidates; routing only, with zero exactness or semantic-evidence credit. |
| `factory_repository_run_shell` | Run broad networkless Bash in the real registered worktree; edits and local commits persist. |
| `factory_get_repository_command_output` | Resume bounded output paging for a durable live-repository command. |
| `factory_list_analysis_providers` | List redacted target-bound IDA/Ghidra registrations. |
| `factory_list_analysis_operations` | Page factory-approved atomic schemas and attestation state. |
| `factory_analysis_call` | Run one bounded, target-bound semantic operation; native IDA may update database metadata but never target bytes. |
| `factory_create_workspace`, `factory_get_workspace` | Create or resume an expiring committed-source capability. |
| `factory_workspace_list_files`, `factory_workspace_read_file`, `factory_workspace_search` | Inspect source with bounded relative-path operations. |
| `factory_workspace_apply_patch` | Transactionally apply a checked text diff to disposable source. |
| `factory_workspace_run_shell` | Run composable Bash in a bounded, networkless source-only tmpfs. |
| `factory_get_workspace_command_output` | Resume bounded stdout/stderr paging with truncation accounting. |
| `factory_get_workspace_status`, `factory_get_workspace_diff` | Inspect changes and export a content-identified diff. |
| `factory_discard_workspace` | Remove only disposable workspace and command payloads. |
| `factory_inspect_repository` | Read an adapter summary; no acceptance implied. |
| `factory_list_claims` | Page imported replay candidates. |
| `factory_submit_replay` | Idempotently queue controlled replay. |
| `factory_get_job`, `factory_list_jobs` | Observe durable state. |
| `factory_cancel_job` | Cancel queued work or request process-group termination. |
| `factory_get_job_events` | Page append-only transition history. |
| `factory_get_job_output_page` | List receipt artifacts or page exact bytes. |
| `factory_get_acceptance_registry` | Classify every receipt candidate; return compact identity/counts by default or full candidate diagnostics on request. |
| `factory_get_accepted_snapshot` | Materialize accepted results for one repository. |
| `factory_query_accepted_facts` | Query only live accepted receipt facts; use compact identity/coverage summaries by default or full bindings on request. |
| `factory_query_knowledge` | Page only Factory-published cross-game knowledge; it never reads or promotes game-local input. |
| `factory_list_historical_fixtures` | Page hash-pinned counterexamples. |

Every tool has structured output and an accurate MCP annotation. Expected
operator/model errors become MCP tool errors (`isError=true`); an error string
is never returned inside a nominally successful response.

The job tools are claim-generic rather than game- or stage-specific. GPT-web
uses the same `factory_list_claims` and `factory_submit_replay` sequence for a
function exact claim or an extent-free `whole_build_closed` product claim; the
selected controlled driver defines the coverage domain. Runtime claim types are
discoverable vocabulary but remain unexecutable until a runtime driver and
policy allowlist are implemented.

## Installation and local configuration

Install the optional MCP v2 dependency:

```bash
python -m pip install -e '.[mcp]'
```

Copy [`factory-service.example.toml`](../config/factory-service.example.toml)
to a private operator location and replace every path. The real configuration
is authority: it registers the only repositories GPT-web may name and binds the
job database, evidence store, and acceptance policy. Do not commit secrets or
machine-local paths.

Run at least one worker independently of the MCP server:

```bash
export FACTORY_SERVICE_CONFIG=/private/path/factory-service.toml
reconstruction-factory-service worker
```

Run the worker and MCP server from the same factory installation and Python
runtime, with the same relevant environment variables. Runtime and environment
surfaces are part of replay identity. A receipt produced by a worker in one
virtual environment is correctly stale when queried by an MCP process whose
driver plan resolves a different Python executable or toolchain environment.

For a same-machine MCP client, use stdio:

```bash
touhou-reconstruction-factory-mcp --transport stdio
```

For GPT-web, place the service behind TLS and start stateless Streamable HTTP.
The default profile remains bearer-authenticated:

```bash
export FACTORY_MCP_BEARER_TOKEN='replace-with-at-least-32-random-characters'
touhou-reconstruction-factory-mcp \
  --transport streamable-http \
  --host 127.0.0.1 \
  --port 8765 \
  --mcp-path /mcp \
  --auth bearer \
  --allowed-host factory.example.internal \
  --allowed-origin https://chatgpt.com
```

The default MCP endpoint is `/mcp`. Configure GPT-web to send
`Authorization: Bearer <token>`. The built-in profile requires a minimum
32-character token, exact bearer comparison, request-size enforcement, and MCP
SDK Host/Origin validation. It intentionally binds to loopback by default. A
public deployment still requires TLS and an appropriate network/authentication
layer; the static bearer profile is not an OAuth authorization server.

For one explicitly accepted single-user development deployment, authentication
can be disabled without weakening the default:

```bash
touhou-reconstruction-factory-mcp \
  --transport streamable-http \
  --host 127.0.0.1 \
  --port 8772 \
  --mcp-path /factory-<random-hex> \
  --auth none \
  --allowed-host machine-name.example.ts.net \
  --allowed-host 127.0.0.1:8772 \
  --allowed-origin https://chatgpt.com
```

`--auth none` is intentionally explicit. With `repository_work.enabled=true`, a
caller can read and modify every registered live worktree, see ignored targets
and toolchains, run repository-local commands, and create local commits. The
runner has no network and therefore cannot perform remote Git push. Analysis,
replay, and Truth Kernel admission remain separate interfaces. This deployment
profile is intended only for the operator's chosen one-user development setup.

The HTTP MCP process may be restarted without changing job identity. The worker
may also be restarted; only a safely leased new job is claimed. An already
active expired lease is failed, not guessed safe to resume. The server supports
the ChatGPT-style `server/discover` exchange for protocol `2026-07-28` while
retaining the SDK's legacy initialization path.

## Verification

The test suite exercises live dirty-state observation, repo-local and shared
tool visibility, Git checkpoint creation, nonzero and timeout persistence,
output truncation without command abortion, database restart, idempotency conflicts, atomic
multi-worker claiming, lease expiry, queued and active cancellation, process
group termination, queue-time identity drift, receipt acceptance, output
paging, MCP discovery, structured output, model-visible tool errors, committed
source exclusion, random workspace capabilities, traversal rejection,
transactional patching, networkless shell execution, timeout rollback, and
symlink-result rejection. Analysis tests enforce loopback-only registration,
repository/target ownership, closed operation names, argument bounds, target
metadata equality, and the absence of native mutation/bridge-shell authority.
The live inventory contains no game-knowledge publication or promotion tool.

Read-only capability questions for future MCP regression runs are in
[`factory-mcp.xml`](../evaluations/factory-mcp.xml). Live validation should run
against all six registered repositories: TH04, TH08, TH09, TH095, TH10, and
TH105. The earlier four exercise mature historical fixtures and replay paths;
TH09 and TH10 exercise the zero-historical-fixture boundary and both native
analysis-provider families. TH09 additionally has a controlled exact replay
driver; TH10 does not yet gain replay acceptance from analysis alone.

## Plugin UX layer

The repository now includes an installable plugin that combines this MCP
connection with focused English workspace, analysis, and replay skills. This
matches the current OpenAI product model: a plugin can package skills and MCP
tools together, and installed skills can be selected automatically or
explicitly with `@`. See the official
[`Skills & Plugins`](https://learn.chatgpt.com/docs/skills-and-plugins) and
[`Build plugins`](https://learn.chatgpt.com/docs/build-plugins) guides.

The skills guide autonomous source development and evidence operation without
merging their trust states. They are guidance, not a capability cage: broad
repository Bash remains available alongside atomic analysis and replay tools.
They cannot duplicate receipt verification, convert `completed` into
`accepted`, or promote a commit/build result. Those invariants stay inside the
registry and Truth Kernel.

The exact fixed-URL deployment and TH105 smoke test are in
[`gpt-web-plugin.md`](gpt-web-plugin.md).
