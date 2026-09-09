# GPT-web plugin and Funnel deployment

## Scope

This is a deliberately small, single-operator integration. It packages one
factory skill with the existing 15 bounded MCP tools and exposes them through a
fixed Tailscale Funnel URL. It does not automate repository creation, edit game
sources, require GitHub access, or introduce another verification path.

The committed endpoint is:

```text
https://laptop-9d3a7045.taile42c02.ts.net/touhou-reconstruction-factory-mcp
```

It uses no token or login. Possession is not authorization: the URL is a public
endpoint. Anyone who discovers it can inspect factory metadata, queue supported
replays, and request cancellation. The server still exposes no shell, arbitrary
path, upload, source mutation, or fact-promotion tool. Keep the registered
repositories and artifacts non-sensitive, monitor the queue, and disable the
Funnel route when it is not wanted.

## Components

- [`.codex-plugin/plugin.json`](../plugins/touhou-reconstruction-factory/.codex-plugin/plugin.json)
  describes the installable plugin.
- [`.mcp.json`](../plugins/touhou-reconstruction-factory/.mcp.json) binds the
  plugin to the fixed remote URL without credentials.
- [`factory-replay/SKILL.md`](../plugins/touhou-reconstruction-factory/skills/factory-replay/SKILL.md)
  teaches the model the factory's trust states and resume workflow.
- [`touhou-reconstruction-factory-mcp.service`](../ops/touhou-reconstruction-factory-mcp.service)
  serves stateless Streamable HTTP on loopback.
- [`touhou-reconstruction-factory-worker.service`](../ops/touhou-reconstruction-factory-worker.service)
  executes queued replays independently of chat connections.
- [`configure-funnel.sh`](../scripts/configure-funnel.sh) maps the fixed public
  path to the same path on the loopback server.

## Local deployment

Create one stable Python environment shared by the server and worker:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[mcp]'
```

Copy `config/factory-service.example.toml` to a private path and replace every
repository path. Copy `config/factory-mcp.env.example` to
`~/.config/touhou-reconstruction-factory-mcp.env` and set the exact Python,
service-config, hostname, port, and path values. Do not put shell quoting around
values in this systemd environment file.

Install and start both user units:

```bash
mkdir -p ~/.config/systemd/user
cp ops/touhou-reconstruction-factory-{mcp,worker}.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now touhou-reconstruction-factory-worker.service
systemctl --user enable --now touhou-reconstruction-factory-mcp.service
scripts/configure-funnel.sh
```

The worker and server must use the same factory checkout, Python executable,
service configuration, and replay-relevant environment. Otherwise the registry
correctly rejects receipts as stale. Inspect local state with:

```bash
systemctl --user status touhou-reconstruction-factory-{mcp,worker}.service
journalctl --user -u touhou-reconstruction-factory-mcp.service -n 100
journalctl --user -u touhou-reconstruction-factory-worker.service -n 100
tailscale funnel status
```

To remove only this public route while leaving other Funnel mappings intact:

```bash
tailscale funnel \
  --https=443 \
  --set-path=/touhou-reconstruction-factory-mcp \
  off
```

## Install in GPT-web

The repository marketplace lives at `.agents/plugins/marketplace.json`. Import
`N0zoM1z0/touhou-reconstruction-factory` as a plugin marketplace, install
**Touhou Reconstruction Factory**, and begin a new conversation so the newly
installed skill is available. The plugin should connect directly to the fixed
MCP URL and should not ask for a bearer token.

The exact marketplace controls available in ChatGPT can vary by account and
workspace. If repository marketplace import is not available, first create a
custom plugin from the same fixed MCP URL to test the tool connection. That
fallback tests MCP but does not necessarily install the bundled skill.

OpenAI's current product documentation describes remote MCP connections and
plugin packaging in [MCP](https://learn.chatgpt.com/docs/extend/mcp),
[Build plugins](https://learn.chatgpt.com/docs/build-plugins), and
[Skills & Plugins](https://learn.chatgpt.com/docs/skills-and-plugins).

## TH105 acceptance smoke test

Start with this prompt, either relying on automatic selection or selecting the
plugin explicitly with `@`:

```text
Use the Touhou Reconstruction Factory to verify the known TH105 smoke-test
claim. Show the repository and discovered claim, retain the durable job ID,
wait for a terminal state, and report receipt verdict and current registry
acceptance separately. Do not infer LTCG ownership or whole-image exactness.
```

The intended tool sequence is:

1. `factory_describe` and `factory_list_repositories`;
2. `factory_list_claims(repository_id="th105", claim_type="codegen_exact",
   limit=5, offset=0)`;
3. confirm the discovered candidate is
   `claim:th105-main:function:00401000:codegen-exact`;
4. `factory_submit_replay` with a unique stable idempotency key;
5. `factory_get_job` until terminal;
6. confirm execution state, receipt verdict, and acceptance decision separately;
7. confirm the receipt remains current through an accepted-facts or snapshot
   query.

A correct success is narrow: exact standalone VC8 code generation for the
returned 52-byte function extent under the receipt's bound source, target,
toolchain, environment, oracle, and runner identities. LTCG physical ownership,
linked-owner layout, whole-image closure, and game completeness remain unknown.

If any discovery result, target binding, replay output, freshness check, or
policy decision differs, the correct smoke-test result is rejected, failed, or
unknown—not a remembered success from an earlier receipt.

## Live deployment checkpoint

The fixed public URL was exercised without credentials on 2026-09-09. Remote
discovery returned exactly the factory's 15 bounded tools, policy
`strict-live-v1`, and repositories TH04, TH08, TH095, and TH105. Filtered TH105
claim discovery returned the expected 52-byte candidate first.

The smoke test submitted job
`job:cb18ab0823c64e0e94a3893e09ddfabe`. Its queue-time source binding records
TH105 commit `20f993b7908d8a207a39cf13da8d7614b9a3b23f`, dirty state, one untracked
file, and snapshot digest
`3a11765bdcc7657d09e2fa8842d72752f7a3bdab137ba4de8488623f6e4e96a8`.
This is a precise live-state result, not a clean-release claim.

The independent worker completed the job with receipt
`receipt:165ddfd4de16c88b78efed46b5e6427eee0c94e607bb488d4e15adb2e54eccb6`,
verdict `pass`, acceptance decision `accepted`, and registry
`registry:5df414aaf0f999865183f320db6dc3cdb302dc8669f942d2926c7aaae37ec78b`.
The remote accepted-facts query returned exactly this current 52/52 result for
the selected target, claim type, and oracle. Materializing the accepted TH105
snapshot produced one oracle result and input fingerprint
`37ed883aaed2c413b9a7a706302337e8f24772763e6f906c7a733e175a45e385`.
Repeating the public submission with the same idempotency key returned the same
job with `reused=true`.

As an environment-binding negative check, invoking the registry from an
ordinary interactive shell with a different effective toolchain environment
returned zero accepted facts and a different registry identity. The server and
worker units, which share one environment file, continued to accept the live
receipt. This is expected fail-closed behavior: a receipt is not portable to a
different effective replay environment merely because it passed elsewhere.
