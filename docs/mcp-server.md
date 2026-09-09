# GPT-web MCP Service

## Design boundary

The MCP server is a narrow remote control for the factory. It submits durable
jobs, observes state, pages evidence, and queries accepted knowledge. It does
not contain another replay implementation or another definition of success.

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

The factory replacement has no shell, command, working-directory, or raw-path
parameter. Game-specific behavior lives behind adapters and replay drivers.
Jobs and evidence survive MCP disconnects and server restarts.

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

## Tools

| Tool | Effect |
| --- | --- |
| `factory_describe` | Show redacted configuration and policy identity. |
| `factory_list_repositories` | List registered repository IDs. |
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
| `factory_query_knowledge` | Page scoped static knowledge with explicit status. |
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
cancellation. It does not grant a shell, arbitrary path access, game-source
mutation, or registry bypass, but the endpoint is still public authority over
bounded factory work. Do not use this profile for a shared or sensitive
deployment.

The HTTP MCP process may be restarted without changing job identity. The worker
may also be restarted; only a safely leased new job is claimed. An already
active expired lease is failed, not guessed safe to resume. The server supports
the ChatGPT-style `server/discover` exchange for protocol `2026-07-28` while
retaining the SDK's legacy initialization path.

## Verification

The test suite exercises database restart, idempotency conflicts, atomic
multi-worker claiming, lease expiry, queued and active cancellation, process
group termination, queue-time identity drift, receipt acceptance, output
paging, MCP discovery, structured output, and model-visible tool errors.
The final local checkpoint passes all 89 tests with MCP SDK 2.2.0 and all 83
applicable tests in the dependency-free core environment.

Read-only capability questions for future MCP regression runs are in
[`factory-mcp.xml`](../evaluations/factory-mcp.xml). Live validation should also
run against registered TH04, TH08, TH095, and TH105 repositories because their
different adapters and replay drivers are the reason this boundary exists.

## Plugin UX layer

The repository now includes an installable plugin that combines this MCP
connection with one focused English skill. This matches the current OpenAI
product model: a plugin can package skills and MCP tools together, and installed
skills can be selected automatically or explicitly with `@`. See the official
[`Skills & Plugins`](https://learn.chatgpt.com/docs/skills-and-plugins) and
[`Build plugins`](https://learn.chatgpt.com/docs/build-plugins) guides.

The skill guides discovery, idempotent submission, reconnect-safe observation,
diagnostic paging, and accepted-evidence reporting. It remains guidance, not
authority: it cannot duplicate receipt verification, convert `completed` into
`accepted`, add arbitrary shell tools, or promote a fact. Those invariants stay
inside the MCP service, registry, and Truth Kernel.

The exact fixed-URL deployment and TH105 smoke test are in
[`gpt-web-plugin.md`](gpt-web-plugin.md).
