# GPT-web plugin and Funnel deployment

## Scope

This is a deliberately small, single-operator integration. It packages separate
source-workspace and evidence-replay skills with the factory MCP and exposes
them, plus a target-attested analysis skill, through a fixed Tailscale Funnel
URL. It does not automate repository
creation, grant remote writes to canonical game repositories, require GitHub
access, or introduce another verification path.

The committed endpoint is:

```text
https://laptop-9d3a7045.taile42c02.ts.net/touhou-reconstruction-factory-mcp
```

It uses no token or login. Possession is not authorization: the URL is a public
endpoint. Anyone who discovers it can inspect factory metadata and committed
registered source, queue supported replays, request cancellation, and consume
bounded source-only sandbox compute. Registered IDA/Ghidra providers also expose
bounded read-only semantic queries. Arbitrary Bash exists only inside an
expiring workspace with no network, host path, dirty/untracked/ignored source,
canonical write, or fact-promotion authority. Keep registered source and
artifacts non-sensitive, monitor capacity, and disable the Funnel route when it
is not wanted.

## Components

- [`.codex-plugin/plugin.json`](../plugins/touhou-reconstruction-factory/.codex-plugin/plugin.json)
  describes the installable plugin.
- [`.mcp.json`](../plugins/touhou-reconstruction-factory/.mcp.json) binds the
  plugin to the fixed remote URL without credentials.
- [`factory-replay/SKILL.md`](../plugins/touhou-reconstruction-factory/skills/factory-replay/SKILL.md)
  teaches the model the factory's trust states and resume workflow.
- [`factory-workspace/SKILL.md`](../plugins/touhou-reconstruction-factory/skills/factory-workspace/SKILL.md)
  teaches source exploration, transactional Bash, diff handoff, and the evidence
  boundary.
- [`factory-analysis/SKILL.md`](../plugins/touhou-reconstruction-factory/skills/factory-analysis/SKILL.md)
  teaches target-attested semantic queries without native database writes or
  exactness inflation.
- [`factory-reconstruction/SKILL.md`](../plugins/touhou-reconstruction-factory/skills/factory-reconstruction/SKILL.md)
  coordinates a bounded, resumable source session while preserving the three
  authority boundaries above.
- [`gpt-web-reconstruction.md`](../prompts/gpt-web-reconstruction.md) provides a
  short installed-plugin invocation and a complete standalone prompt under the
  machine-readable `gpt-web-reconstruction-session-v1` contract.
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

To enable source work, configure `[workspace]` with a root that is a strict
child of `state_directory`. The MCP host must provide `bwrap`, `prlimit`,
`nice`, Git, and ripgrep. Omit the table to disable every workspace operation.
The committed systemd unit applies a private umask, no-new-privileges, task,
memory, swap, and core-dump limits to the whole MCP service cgroup.

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

## Reconstruction session prompt

Use the maintained prompt in
[`prompts/gpt-web-reconstruction.md`](../prompts/gpt-web-reconstruction.md).
With the plugin installed, select **@Touhou Reconstruction Factory** and fill in
only the game ID, objective, optional scope hint, measurable stop condition, and
an existing workspace ID when resuming. The longer standalone form repeats all
authority and handoff rules for testing without automatic skill selection.

The prompt deliberately does not ask GPT-web to commit or push. The remote
workspace is a committed-HEAD snapshot and exports a candidate diff. A local
Codex session reviews and applies that diff to the canonical game repository;
only then can a discovered canonical claim be replayed and considered by the
acceptance registry.

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

## TH105 workspace smoke test

After installing a plugin version that includes `factory-workspace`, start a
new conversation and use:

```text
Use the Touhou Reconstruction Factory to create a disposable TH105 source
workspace. Read its repository instructions, prove that local dirty and ignored
files are not present, run a small read-only shell inspection, and return the
workspace baseline, command state, and unchanged diff. Do not claim that the
canonical repository was modified or verified.
```

The intended sequence is `factory_describe`, repository discovery,
`factory_create_workspace`, bounded file reads/search, one isolated shell call,
command-output paging if needed, and `factory_get_workspace_diff`. For an
unchanged smoke test the diff size is zero. The returned
`source_worktree_dirty_observed` may correctly be true while the workspace still
contains only committed `HEAD`.

For a semantic/source combined test, select `th105-ida`, discover
`get_function_by_address`, query `0x00401000`, and confirm the result is bound to
the expected TH105 target while still reporting `exactness_credit="none"`.
Then create a separate TH105 workspace and inspect the corresponding committed
source. The analysis result guides the hypothesis; only a later replay can
verify it.

## Live deployment checkpoint

The fixed public URL was exercised without credentials on 2026-09-10. Remote
discovery returned exactly 29 factory tools: 15 replay/registry tools, 11
workspace tools, and three analysis tools. It exposed no upstream
`run_command`, arbitrary host path, canonical-source write, analysis mutation,
or fact-promotion tool. The public description returned policy
`strict-live-v1`, repositories TH04, TH08, TH095, and TH105, four redacted
analysis registrations, and replay-configuration digest
`f3b26f68e0bf0fd12c7d29dca3c85e8070aea082839b106586ea317003361f89`.

A public TH105 workspace smoke created
`workspace:eccb0d3deb4848c799fb1e98e6e74569` from commit
`20f993b7908d8a207a39cf13da8d7614b9a3b23f`, tree
`0614c96746c130bfdded94e63c12e8aaf8b0cd35`, and exactly 860 committed
files/8,456,219 bytes while reporting the canonical worktree as dirty. Its
isolated command `command:ea4af458f13941dd83d555a6f63eca12` confirmed that
host home, host `/etc/passwd`, the ignored `.tools` and original executable,
the canonical untracked file, and network access were absent. The command added
one disposable file; the complete 195-byte diff had SHA-256
`9013675ae8607ac868e60ed8b67ee769e65bc7b57ad369ac347a438eac499ce0`.
The workspace was then explicitly discarded. The six pre-existing TH105
working-tree changes remained unchanged and outside the snapshot.

The public analysis gateway independently attested `th105-ida` and returned
`sub_401000`, size `0x34`, for `0x00401000`, with authority
`provisional-semantic-analysis` and `exactness_credit="none"`. Bounded
`list_functions` calls also succeeded through the registered TH095 and TH04
Ghidra bridges. The registered TH08 IDA call accurately failed because the
active database did not attest as TH08 at image base `0x400000`; this is an
unavailable result, not a substituted backend or remembered success. A native
IDA mutation request was rejected by the factory allowlist.

The final public replay submitted job
`job:f04d64dde74a48db886e7293154c7ed7`. Its queue-time binding records the
same TH105 commit and tree, dirty state, one untracked file, source snapshot
`3a11765bdcc7657d09e2fa8842d72752f7a3bdab137ba4de8488623f6e4e96a8`,
and runner implementation
`fe8f2d54b6fc61c5b18fafb1c3c25d9ad93871a44d59041182bc164e92fa49e0`.
The independent worker completed it with receipt
`receipt:bedc8671518b9a8a4102280ffa2ce1aeae7871a4770044eef2631538af34c3fb`,
verdict `pass`, acceptance decision `accepted`, and registry
`registry:0d68a1d266e8c83cc47d9630c9da4014f4208777dfc87fdf7de26fb4d6cda3d8`.
The subsequent public accepted-facts query returned exactly one current 52/52
complete result for the selected target, claim type, and oracle. Materializing
the accepted TH105 snapshot produced one oracle result and input fingerprint
`e363a026621ad814bdbb1bd8e4afa935494a1811fe2f72ae261f8cc477c4651b`.

The complete local suite passed all 105 tests. The installed MCP unit also
reported `NoNewPrivileges=yes`, `PrivateTmp=yes`, a 768-task limit, a 3 GiB
memory limit with swap disabled, a private umask, and core dumps disabled.
