# GPT-web MCP Service

## Design boundary

The MCP server is the typed remote boundary for two separate authorities. Its
replay surface submits durable jobs, observes state, pages evidence, and queries
accepted knowledge. Its workspace surface develops committed source in
capability-addressed disposable sandboxes. Its analysis surface routes only
factory-allowlisted reads through target-attested loopback IDA/Ghidra bridges.
None of these surfaces contains another definition of reconstruction success.

This improves on the exploratory
[`mcp_for_gptweb`](https://github.com/N0zoM1z0/mcp_for_gptweb) server while
retaining what it proved useful: headless operation, Streamable HTTP, Host
validation, bearer-protected deployment, and simple GPT-web discovery.

The old repository's history is valuable evidence:

- `8f38474` proved basic Streamable HTTP access, but exposed unrestricted Bash;
- `0d4d47f` and `bed0c6f` proved TH08/IDA calls, but embedded game-specific
  operations in the transport;
- `96b0624` repaired GPT-web discovery;
- `198c2d3` reduced the tool surface, but command lifetime was still connection
  lifetime;
- `5a9de07` captured a useful reconstruction workflow, while synchronous output
  truncation could still discard the diagnostic tail.

The factory replacement never accepts a host path or exposes a host shell. It
does accept POSIX-relative workspace paths and arbitrary Bash inside a
source-only Bubblewrap boundary. This preserves agent composability without
mounting the canonical worktree, ignored targets/toolchains, operator home,
network, jobs, evidence, or Truth Kernel state. Game-specific verification
behavior remains behind adapters and replay drivers. Jobs and evidence survive
MCP disconnects and server restarts.

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

For source development, GPT-web instead performs this sequence:

1. Create a workspace for a returned repository ID with a stable idempotency
   key and retain its random capability ID.
2. Note the exact baseline commit and whether dirty canonical work was observed
   and therefore omitted.
3. List, read, and search files using relative paths; read repository
   instructions before changing source.
4. Apply a text patch or compose arbitrary Bash in the isolated tmpfs.
5. Inspect command exit state, filesystem-commit state, and complete paged
   output independently.
6. Inspect workspace status and page the complete diff with its SHA-256.
7. Return that diff for local review/application. Do not report that the
   canonical repository changed and do not treat workspace tests as receipts.

The complete isolation and handoff contract is in
[`workspace-provider.md`](workspace-provider.md).

For semantic target analysis, first list providers for the repository and then
list the selected provider's operation schemas. Pass one discovered operation
and a JSON object string to `factory_analysis_call`. The response binds the
current adapter target, bridge identity, operation, arguments, attestation, and
observation time while fixing `exactness_credit` to `none`. Native analysis
writes and the legacy bridges' host Bash tools are unreachable. See
[`analysis-provider.md`](analysis-provider.md).

## Tools

| Tool | Effect |
| --- | --- |
| `factory_describe` | Show redacted configuration and policy identity. |
| `factory_list_repositories` | List registered repository IDs. |
| `factory_list_analysis_providers` | List redacted target-bound IDA/Ghidra registrations. |
| `factory_list_analysis_operations` | Page factory-approved read schemas and attestation state. |
| `factory_analysis_call` | Run one bounded, read-only, target-bound semantic query. |
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
| `factory_get_acceptance_registry` | Classify every receipt candidate. |
| `factory_get_accepted_snapshot` | Materialize accepted results for one repository. |
| `factory_query_accepted_facts` | Query only live accepted receipt facts. |
| `factory_query_knowledge` | Page only Factory-published cross-game knowledge; it never reads or promotes game-local input. |
| `factory_list_historical_fixtures` | Page hash-pinned counterexamples. |

Every tool has structured output and an accurate MCP annotation. Expected
operator/model errors become MCP tool errors (`isError=true`); an error string
is never returned inside a nominally successful response.

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
  --mcp-path /touhou-reconstruction-factory-mcp \
  --auth none \
  --allowed-host machine-name.example.ts.net \
  --allowed-host 127.0.0.1:8772 \
  --allowed-origin https://chatgpt.com
```

`--auth none` is intentionally noisy and explicit. Anyone who can discover the
public URL can inspect registered metadata, submit replay jobs, and request job
cancellation. When the workspace provider is enabled, they can also read the
committed source of every registration and consume bounded isolated compute and
workspace slots. Registered analysis providers also permit bounded semantic
queries and small raw-byte reads from the attested target. Callers still cannot
name a host path, invoke bridge Bash, read dirty/untracked/ignored source, reach
the workspace network, mutate canonical source or analysis databases, or bypass
the registry. This is not caller authentication: use only non-sensitive
registered source/targets, accept the residual denial-of-service risk, and
disable the route when it is not wanted.

The HTTP MCP process may be restarted without changing job identity. The worker
may also be restarted; only a safely leased new job is claimed. An already
active expired lease is failed, not guessed safe to resume. The server supports
the ChatGPT-style `server/discover` exchange for protocol `2026-07-28` while
retaining the SDK's legacy initialization path.

## Verification

The test suite exercises database restart, idempotency conflicts, atomic
multi-worker claiming, lease expiry, queued and active cancellation, process
group termination, queue-time identity drift, receipt acceptance, output
paging, MCP discovery, structured output, model-visible tool errors, committed
source exclusion, random workspace capabilities, traversal rejection,
transactional patching, networkless shell execution, timeout rollback, and
symlink-result rejection. Analysis tests enforce loopback-only registration,
repository/target ownership, closed operation names, argument bounds, target
metadata equality, and the absence of native mutation/bridge-shell authority.
The 2026-09-10 release checkpoint passes all 105 tests.

Read-only capability questions for future MCP regression runs are in
[`factory-mcp.xml`](../evaluations/factory-mcp.xml). Live validation should also
run against registered TH04, TH08, TH095, and TH105 repositories because their
different adapters and replay drivers are the reason this boundary exists.

## Plugin UX layer

The repository now includes an installable plugin that combines this MCP
connection with focused English workspace, analysis, and replay skills. This
matches the current OpenAI product model: a plugin can package skills and MCP
tools together, and installed skills can be selected automatically or
explicitly with `@`. See the official
[`Skills & Plugins`](https://learn.chatgpt.com/docs/skills-and-plugins) and
[`Build plugins`](https://learn.chatgpt.com/docs/build-plugins) guides.

The skills guide source development and evidence operation without merging
their trust states. They remain guidance, not authority: they cannot duplicate
receipt verification, convert `completed` into `accepted`, promote a workspace
test, or write the canonical repository. Those invariants stay inside the MCP
service, registry, and Truth Kernel.

The exact fixed-URL deployment and TH105 smoke test are in
[`gpt-web-plugin.md`](gpt-web-plugin.md).
