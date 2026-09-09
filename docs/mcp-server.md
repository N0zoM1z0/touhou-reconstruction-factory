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

For GPT-web, place the service behind TLS on a private network or authenticated
reverse proxy and start stateless Streamable HTTP:

```bash
export FACTORY_MCP_BEARER_TOKEN='replace-with-at-least-32-random-characters'
touhou-reconstruction-factory-mcp \
  --transport streamable-http \
  --host 127.0.0.1 \
  --port 8765 \
  --allowed-host factory.example.internal \
  --allowed-origin https://chatgpt.com
```

The MCP endpoint is `/mcp`. Configure GPT-web to send
`Authorization: Bearer <token>`. The built-in profile requires a minimum
32-character token, exact bearer comparison, request-size enforcement, and MCP
SDK Host/Origin validation. It intentionally binds to loopback by default. A
public deployment still requires TLS and an appropriate network/authentication
layer; the static bearer profile is not an OAuth authorization server.

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
The final local checkpoint passes all 87 tests with MCP SDK 2.2.0 and all 83
applicable tests in the dependency-free core environment.

Read-only capability questions for future MCP regression runs are in
[`factory-mcp.xml`](../evaluations/factory-mcp.xml). Live validation should also
run against registered TH04, TH08, TH095, and TH105 repositories because their
different adapters and replay drivers are the reason this boundary exists.

## Deferred plugin UX layer

Version 0.2.0 deliberately finishes and validates the server boundary before
packaging a ChatGPT plugin. The next usability layer should be an installable
factory plugin that bundles this MCP connection with a small set of English
skills. This matches the current OpenAI product model: a plugin can package
skills and MCP tools together, installed skills can be selected automatically
or explicitly with `@`, and a newly installed plugin becomes available in new
ChatGPT conversations. See the official
[`Skills & Plugins`](https://learn.chatgpt.com/docs/skills-and-plugins) and
[`Build plugins`](https://learn.chatgpt.com/docs/build-plugins) guides.

The first plugin skills should remain narrow:

- **discover and submit**: select only a registered repository and imported
  claim, generate a stable idempotency key, submit once, and retain the job ID;
- **resume and diagnose**: recover a job in a later conversation, interpret its
  event history, page every relevant artifact without losing the tail, and
  distinguish execution failure from receipt rejection;
- **report accepted evidence**: query the current registry, cite job/receipt/
  registry identities, and explicitly label stale, rejected, or unknown state;
- **coordinate GitHub**: use a separately authorized GitHub plugin for issues,
  commits, CI, and pull requests while using the factory MCP only for replay and
  truth queries.

The skill layer is guidance, not authority. It must not duplicate receipt
verification, convert `completed` into `accepted`, add arbitrary shell tools,
or let a GitHub write promote a fact. Those invariants remain enforced by the
server and Truth Kernel even if a model ignores or misapplies a skill.

Before publishing that plugin, test automatic selection, explicit `@` use,
fresh-conversation resume, MCP reauthentication, pagination, cancellation, and
mixed GitHub/factory operation. The MCP service may require separate connection
or authentication during plugin installation; the plugin must present that as
setup state rather than an apparent replay failure.
