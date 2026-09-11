# GPT-web plugin and Funnel deployment

## Scope

This is a deliberately small, single-operator integration. It packages
autonomous live-repository reconstruction and semantic reconstruction skills,
an optional isolated-workspace skill, and separate analysis/replay skills with
the Factory MCP through one operator-private Tailscale Funnel URL. It does not
automate repository creation, require GitHub access for reconstruction, provide
Git push, or introduce another verification path.

The deployment URL is deliberately not committed. Its high-entropy path is held
only in the operator's private service environment and the ChatGPT connection.
It uses no token or login in the operator's chosen one-user development setup;
the unguessable path is the only deployment-level access boundary.
With the live-repository provider enabled, GPT-web can inspect dirty, untracked,
and ignored game state; run broad Bash, Wine, and repo-local tools; modify source;
and create local Git commits in every registered game repository. The runner has
no network, so Git push is unavailable. Registered IDA/Ghidra providers expose
target-attested semantic queries. None of these actions can publish cross-game
knowledge or bypass replay-receipt acceptance.

## Components

- [`.codex-plugin/plugin.json`](../plugins/touhou-reconstruction-factory/.codex-plugin/plugin.json)
  describes the installable plugin.
- [`.app.json`](../plugins/touhou-reconstruction-factory/.app.json) binds the
  Web-capable plugin to the already registered no-auth ChatGPT app.
- [`factory-replay/SKILL.md`](../plugins/touhou-reconstruction-factory/skills/factory-replay/SKILL.md)
  teaches the model the factory's trust states and resume workflow.
- [`factory-workspace/SKILL.md`](../plugins/touhou-reconstruction-factory/skills/factory-workspace/SKILL.md)
  teaches intentionally isolated committed-HEAD experiments; it is not the
  default source workflow.
- [`factory-analysis/SKILL.md`](../plugins/touhou-reconstruction-factory/skills/factory-analysis/SKILL.md)
  teaches target-attested semantic queries, explicit native IDA metadata edits,
  and the boundary that prevents either from inflating exactness.
- [`factory-reconstruction/SKILL.md`](../plugins/touhou-reconstruction-factory/skills/factory-reconstruction/SKILL.md)
  coordinates autonomous live source work, Bash/analysis/toolchain composition,
  local `gpt-web:` checkpoints, and evidence boundaries.
- [`factory-semantic-reconstruction/SKILL.md`](../plugins/touhou-reconstruction-factory/skills/factory-semantic-reconstruction/SKILL.md)
  runs a persistent campaign of bounded evidence-backed owner/field/protocol
  batches under independent exact and historical-platform product/runtime
  feedback.
- [`gpt-web-reconstruction.md`](../prompts/gpt-web-reconstruction.md) provides a
  short installed-plugin invocation and a complete standalone prompt under the
  machine-readable `gpt-web-reconstruction-session-v5` contract. Version 5
  separates long campaign duration from adaptive bounded Web conversations and
  preserves continuation in repository state without exposing external browser
  scheduling. Version 4 added independent exactness, production-closure, runtime-storage, and runtime-scenario
  reporting plus their coupled feedback loop. Version 3 preserves the earlier
  live-repository autonomy and Git-checkpoint contract; versions 1 through 3
  remain committed as historical contracts.
- [`gpt-web-semantic-reconstruction.md`](../prompts/gpt-web-semantic-reconstruction.md)
  provides a ready-to-run TH095 prompt and standalone fallback under
  `gpt-web-semantic-reconstruction-session-v4`. Version 4 keeps the campaign
  open while bounding each browser conversation and making proactive
  `active-incomplete` handoff normal. Version 3 removed Web-authored stop
  conditions and phase closure, defaults every resume to active-incomplete,
  adversarially reviews earlier readiness prose, and rotates coverage after a
  local plateau. Version 2 retains the earlier autonomous loop and self-audited
  stop contract; version 1 remains the historical one-batch contract.
- [`touhou-reconstruction-factory-mcp.service`](../ops/touhou-reconstruction-factory-mcp.service)
  serves stateless Streamable HTTP on loopback.
- [`touhou-reconstruction-factory-worker.service`](../ops/touhou-reconstruction-factory-worker.service)
  executes queued replays independently of chat connections.
- [`configure-funnel.sh`](../scripts/configure-funnel.sh) maps the
  operator-private route path to the same path on the loopback server.

## Bind skills to the registered ChatGPT app

An MCP server does not install skills through the MCP protocol. The installable
unit is a plugin: the plugin packages the skills and references an MCP-backed
ChatGPT app that was registered separately in Developer mode. A raw custom MCP
connection proves that the tools work, but it does not install this repository's
skill bundle.

For GPT-web, use `.app.json`; do not declare `mcp.json`, `.mcp.json`, or
`mcpServers` in this plugin. ChatGPT marks a plugin imported from a GitHub
marketplace as **Desktop only** when it declares an MCP server directly, even
when that server uses a remote HTTPS URL. The registered app reference is the
Web-capable indirection.

ChatGPT exposes three similar identifiers. They are not interchangeable:

| Value | Example or current value | Use |
| --- | --- | --- |
| Plugin-page identifier | `plugin_asdk_app_...` | Appears in the browser URL. Remove only the leading `plugin_` to obtain the app ID. |
| App Id | `asdk_app_6aa21bec66888191bd24c118e47ddee6` | Commit this value as `.app.json` `apps.<alias>.id`. |
| Version Id | `asdk_app_v_6aa21bec66988191a434524226c15aee` | Identifies one app version. Record it only for diagnostics; never use it in `.app.json`. |

The current development registration was checked on 2026-09-10:

| Field | Value |
| --- | --- |
| URL | operator-private; never committed |
| Authorization supported / used | `None` / `None` |
| App Id | `asdk_app_6aa21bec66888191bd24c118e47ddee6` |
| Version Id at observation time | `asdk_app_v_6aa21bec66988191a434524226c15aee` |
| Review status | `development` |

The committed binding is deliberately small:

```json
{
  "apps": {
    "touhou-reconstruction-factory": {
      "id": "asdk_app_6aa21bec66888191bd24c118e47ddee6",
      "required": true
    }
  }
}
```

`.codex-plugin/plugin.json` points `apps` to `./.app.json` and `skills` to
`./skills/`. Each skill also has `agents/openai.yaml` presentation metadata so
the host can show a readable name, short description, and starting prompt. The
skill instructions remain the source of workflow behavior; UI metadata does
not grant tools, authentication, or truth-promotion authority.

To create this binding again for another MCP-backed plugin:

1. Enable **Settings > Security and login > Developer mode** in ChatGPT.
2. Open the Plugins page, select the plus button, and register the remote MCP
   URL and its actual authorization mode.
3. Verify the connection with its tools before packaging it.
4. Open the connection details and copy the **App Id**. If only the page URL is
   available, convert `plugin_asdk_app_...` to `asdk_app_...` by removing the
   leading `plugin_`. Do not use **Version Id**.
5. Add `.app.json`, reference it with `"apps": "./.app.json"`, and package the
   skills under `skills/<skill-name>/SKILL.md`.
6. Keep direct MCP manifests out of a plugin that must work on GPT-web.
7. Update the plugin cachebuster, validate every skill and the plugin, import or
   sync the marketplace, install the plugin, and start a new chat.

The App Id is a reference, not an authorization secret. The referenced app
still controls service availability, permissions, authentication, and action
policy.

### Validator compatibility note

As observed on 2026-09-10, the locally installed `plugin-creator` validator
still accepts only its older `.app.json` entry shape and reports `required` as
an unknown field. Current [OpenAI package validation](https://developers.openai.com/plugins/deploy/submission-errors#mcp-server-reference-errors)
explicitly accepts boolean `required` and `optional` fields, and the current
plugin-management guidance says to use `required: true` when the plugin depends
on the app. Do not remove
`required` merely to satisfy that older local validator. The Factory release
tests enforce the current binding shape, App Id grammar, and absence of a
Desktop-only MCP manifest. Re-run the external validator after its schema is
updated and remove this dated note when the mismatch disappears.

## Local deployment

Create one stable Python environment shared by the server and worker:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[mcp]'
```

Copy `config/factory-service.example.toml` to a private path and replace every
repository path. Copy `config/factory-mcp.env.example` to
`~/.config/touhou-reconstruction-factory-mcp.env` and set the exact Python,
service-config, hostname, port, and a newly generated high-entropy path. Do not
put shell quoting around values in this systemd environment file. Do not copy
the resulting URL or path into tracked documentation, scripts, issues, or
commit messages.

To enable normal source work, configure `[repository_work]` with a root that is
a strict child of `state_directory`, a Git identity, output/time bounds, and any
immutable `shared_tool_roots`. The MCP host must provide `bwrap`, `nice`, Git,
Wine and the system dependencies required by the game scripts. Omit the table
to disable live-repository operations. Configure `[workspace]` separately only
when disposable committed-HEAD experiments are wanted; that provider also needs
`prlimit` and ripgrep.
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

### Restart and reconnect contract

Treat server readiness and GPT-web connection readiness as two separate gates.
After changing MCP code, tool schemas, annotations, or version metadata:

1. wait until no replay job is running, then restart the worker and MCP service;
2. require both user services to be active and run the read-only live validator
   against the public URL, not merely loopback;
3. open the existing connection in ChatGPT Developer mode and select
   **Refresh**;
4. confirm the refreshed server version and tool inventory, then start a new
   conversation for the reconstruction campaign.

The URL and App Id remain unchanged during an ordinary in-place deployment.
Refreshing is still required because ChatGPT caches the connection's tool
metadata, and a conversation whose first tool call occurred during the short
restart interval does not become a successful tool run retroactively. Do not
rotate the URL, recreate the app, bump the Factory again, or ask the agent to
bypass Factory merely to recover that conversation. This follows OpenAI's
[connection testing and metadata refresh procedure](https://developers.openai.com/plugins/deploy/connect-chatgpt).

Diagnose the boundary before changing code:

- if the public validator also fails, inspect the MCP service and Funnel;
- if the public validator passes but a ChatGPT retry produces no MCP journal
  ingress, refresh the Developer-mode connection, verify its registered URL,
  and use a new conversation;
- if the request reaches the MCP journal and returns an error, preserve the
  request evidence and repair that concrete server/tool failure.

Do not repeatedly restart a healthy service while diagnosing a client-side
connection cache. Report GPT-web ready only after the public validator passes;
the operator then performs the one UI-only Refresh step.

To remove only this public route while leaving other Funnel mappings intact:

```bash
set -a
source ~/.config/touhou-reconstruction-factory-mcp.env
set +a
tailscale funnel \
  --https="$FACTORY_FUNNEL_HTTPS_PORT" \
  --set-path="$FACTORY_MCP_PATH" \
  off
```

## Install in GPT-web

The repository marketplace lives at `.agents/plugins/marketplace.json`. For a
workspace GitHub import:

1. Open **Admin > Plugins > Add > Import marketplace**.
2. Use source `https://github.com/N0zoM1z0/touhou-reconstruction-factory`, leave
   **Path** empty because the marketplace is at the repository root, and select
   branch `main` for updateable imports.
3. Review the import result and make **Touhou Reconstruction Factory** available
   to the intended role. Confirm that its required app resolves to the existing
   no-auth Factory connection.
4. Install the plugin. After a repository update, use **Sync now** on the
   marketplace before reinstalling or retesting.
5. Start a new ChatGPT conversation. The plugin detail page should list
   **Factory Analysis**, **Factory Reconstruction**, **Factory Semantic
   Reconstruction**, **Factory Replay**, and **Factory Workspace** under Skills.
6. Invoke **Factory Reconstruction** or **Factory Semantic Reconstruction**
   explicitly, or use the corresponding short prompt below.

The GitHub connection in this procedure distributes and updates the plugin
package only. Reconstruction work does not use GitHub tools and the Factory MCP
does not receive GitHub authority.

If marketplace import is unavailable, keep the existing raw custom MCP
connection for tool testing. That fallback confirms the endpoint but cannot
install the repository's skills by itself. A personal/local marketplace can be
authored through ChatGPT Work or Codex in the desktop app and then installed
from the Personal source where that surface is available.

### Rotate or repair the binding

- A worker/server deployment behind the same URL does not require an App Id
  change.
- Updating the registered connection while retaining the same App Id does not
  require an `.app.json` change.
- Deleting and recreating the ChatGPT app produces a new App Id. Replace only
  `.app.json` `id`, update the plugin cachebuster, run validation, push, select
  **Sync now**, confirm the required app, and test in a new chat.
- A new Version Id alone is not a reason to edit the plugin.
- If the plugin appears as **Desktop only**, first check for `mcp.json`,
  `.mcp.json`, or `mcpServers` inside the imported plugin package.

OpenAI's current product documentation describes remote MCP connections and
plugin packaging in [Package your plugin](https://developers.openai.com/plugins/build/plugins),
[Plugin management](https://learn.chatgpt.com/docs/enterprise/plugin-management),
and [Build skills](https://learn.chatgpt.com/docs/build-skills).

## Reconstruction session prompt

Use the maintained prompt in
[`prompts/gpt-web-reconstruction.md`](../prompts/gpt-web-reconstruction.md).
With the plugin installed, select **@Touhou Reconstruction Factory** and fill in
the game ID, objective, optional scope hint, and an optional prior `gpt-web:`
commit for orientation. The longer standalone form
repeats all authority and handoff rules for testing without automatic skill
selection.

The prompt tells GPT-web to work directly in the registered live repository,
compose Bash with IDA/Ghidra/Wine/toolchains, and create local English
`gpt-web:` checkpoints after coherent tested units. It explicitly forbids Git
push and keeps commits/builds separate from replay and Truth Kernel acceptance.

For already reconstructed source, use the maintained semantic prompt in
[`prompts/gpt-web-semantic-reconstruction.md`](../prompts/gpt-web-semantic-reconstruction.md).
It selects the bundled `factory-semantic-reconstruction` skill and fixes the
historical-platform order: target exact baseline, corresponding Windows i386 or
16-bit product closure/runtime-owner feedback, semantic reconstruction under
both lanes, then portable products. The prompt intentionally lets live TH095
evidence choose the first bounded family instead of freezing a stale filename or
candidate count. It does not let GPT-web declare semantic readiness or begin a
port; that decision belongs to a later independent Codex or human review.

The fresh TH09 exact-reconstruction campaign has a complete standalone prompt
at
[`gpt-web-th09-exact-reconstruction.md`](../prompts/gpt-web-th09-exact-reconstruction.md).
It assumes no injected skill, reads both game and Factory guidance by explicit
path, recovers dirty work first, uses the Factory-native IDA provider, and keeps
exact, Windows i386 product, semantic, and port gates separate. Use it only
after the staged provider is active and passes the public smoke test.

The mature PC-98 TH04 exact campaign has its own complete prompt at
[`gpt-web-th04-exact-reconstruction.md`](../prompts/gpt-web-th04-exact-reconstruction.md).
It selects `th04-ghidra` and `target:th04-main`, preserves 16-bit MZ/OMF,
near/far, segment, relocation, and Borland/TASM/TLINK evidence, and keeps
authored-boundary discovery coupled to natural-source exact reconstruction. Its
99.5% authored-function and authored-byte targets are moving campaign pressure,
not whole-product coverage or Web closure authority.

## TH095 semantic reconstruction campaign

After syncing a plugin version containing `factory-semantic-reconstruction`,
start a new GPT-web conversation, select **@Touhou Reconstruction Factory**, and
paste the campaign prompt from
[`gpt-web-semantic-reconstruction.md`](../prompts/gpt-web-semantic-reconstruction.md).
The intended campaign sequence is:

1. discover `th095`, inspect its real HEAD and dirty/untracked state, and finish
   the mandatory recovery review before new edits whenever it is non-clean;
2. inventory `.analysis/`, establish one bounded manifested scratch root, and
   treat all old artifacts as non-authoritative until their bindings are current;
3. read the repository's semantic phase plan, treat any prior readiness or exit
   audit as an untrusted hypothesis, and actively search for a current TH095-
   local counterexample before following its handoff;
4. run target, tracking, and target-attested Ghidra preflight;
5. call `factory_report_semantic_debt` for `src`, preserving its HEAD/status
   binding and routing-only limitations;
6. supplement the lexical candidates with Bash, ledgers, exact-unit mappings,
   and target-local Ghidra evidence;
7. choose one small owner/field family, preserve both exact and reconstructed
   Windows i386 product/runtime feedback, document the evidence classes, and
   create a local English `gpt-web:` checkpoint;
8. measure and retire proven current-session analysis scratch, refresh the live
   state, and continue with another named family while the browser and context
   remain reliable;
9. when one route yields no actionable batch, rotate to another subsystem, debt
   class, protocol, persistence, runtime, or portability surface instead of
   treating that negative result as completion or the sole reason to hand off;
10. after useful coherent progress, proactively checkpoint and hand off before
   another batch would make the browser or context unreliable; and
11. report runtime receipt status as `unknown` while no deterministic Factory
   runtime provider exists, even when repo-native runtime feedback passes.

The campaign has no `STOP_CONDITION`, but each browser conversation is
deliberately bounded. GPT-web chooses the useful amount of work from batch
difficulty, validation latency, browser responsiveness, and remaining reliable
context; it then writes an `active-incomplete` continuation handoff before the
client becomes fragile. No fixed batch count is imposed. No new commit, no
router hit, or a self-authored exit audit is phase-completion authority. A
bounded route with no result cannot be the sole reason for an immediate handoff;
it triggers coverage rotation while useful work remains available.

The campaign uses repo-native exact and historical-platform checks for its fast
dirty-tree inner loop. It closes broad cold gates immediately for shared or
cross-object risk and at campaign milestones. It does not replay the complete
accepted Factory receipt set after every private checkpoint when the next
planned source commit would immediately stale those receipts; milestone
receipts always bind the current committed source, and any deferred plane is
reported as non-current.

The current TH095 worktree may contain pre-existing untracked runtime
experiments. Web cannot know whether they are intentional experiments or an
interrupted prior batch, so it must inspect and classify them before new work.
Recoverable partial work is completed first; unrelated and unknown work is
preserved and excluded. Repo-native checks remain available while the tree is
dirty, but Web must not delete or silently commit files merely to make a Factory
replay eligible.

Prompts never depend on skill injection. Both ready-to-run prompt documents name
the exact Factory contract and documentation paths and contain a complete inline
fallback. To let `factory_repository_run_shell` read those paths, mount the
Factory `contracts/` and `docs/` directories as read-only `shared_tool_roots` in
the operator configuration. If they are not mounted, the model reports that
once and continues from the inline prompt. See
[`worktree recovery and analysis artifacts`](worktree-recovery-and-analysis-artifacts.md)
for the mandatory behavior and the observed legacy storage footprint.

The single-user deployment now mounts
`/home/pentester/coding/codex_ida/touhou-reconstruction-factory/contracts` and
`.../docs` through `repository_work.shared_tool_roots`. A TH04 repository-shell
probe read both new guidance files successfully through Bubblewrap. The service
loads this operator configuration for each tool call, so adding these read-only
roots required no process restart and did not interrupt the active TH095 Web
campaign. The roots expose guidance only; the Factory evidence/job store and
non-allowlisted game repositories remain outside the command namespace.

TH09 separately allowlists registered repositories `th08` and `th095` through
its private `reference_repository_ids`. Those canonical checkouts are visible
read-only only while a TH09 shell runs. TH08 and TH095 can guide focused source
and history searches, but neither grants TH09 evidence or exactness; TH095's
ongoing semantic reconstruction is explicitly provisional. The standalone TH09
prompt names both canonical paths and requires TH09-local target and Oracle
confirmation.

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

## TH095 product-closure test

After the deployed Factory has been updated and restarted, GPT-web can exercise
the independent product plane through the same shared MCP URL:

```text
Use the Touhou Reconstruction Factory to verify TH095 production closure.
Discover the registered repository and the whole_build_closed product claim;
submit its controlled replay with a new stable idempotency key; observe the job
until terminal; and report job state, receipt verdict, production-TU coverage,
registry decision, and accepted fact separately. Do not infer function
exactness, deterministic or whole-image equality, runtime storage identity, or
runtime scenario validation from the build.
```

The intended sequence is the same generic sequence used for a function claim:

1. call `factory_list_claims(repository_id="th095",
   claim_type="whole_build_closed", limit=5, offset=0)`;
2. select only the returned extent-free product claim;
3. call `factory_submit_replay` with a new stable idempotency key;
4. reconnect and poll `factory_get_job` as needed—the cold 88-TU Wine build can
   take many minutes;
5. require `completed`, receipt `pass`, complete
   `production-translation-units` coverage, and registry `accepted` as separate
   observations;
6. query `factory_query_accepted_facts` for `whole_build_closed` and report the
   exact returned receipt scope.

If the live TH095 worktree changes between submission and execution, the job
must fail before replay as stale. If it changes after the receipt, the registry
must reject that receipt as stale. Submit a new job for the new state rather
than treating a prior product pass as permanent.

## Live-repository capability smoke test

Use a temporary registered Git repository for mutating release tests. Confirm
that `factory_get_repository_status` reports its actual dirty/untracked state,
then use `factory_repository_run_shell` to read an ignored fake toolchain, run a
configured shared tool, edit a tracked source file, and create a local
`gpt-web:` commit. Verify the returned before/after HEADs and created-commit
subject, reconnect, and page the command output. Also verify that a timeout
leaves its partial file visible and that output truncation does not abort the
remaining script.

Do not create and revert junk smoke commits in TH04, TH08, TH095, or TH105.
Against those real registrations, use status and non-mutating tool/provider
probes. Run real game build/replay scripts only when their documented ignored
outputs and current dirty state have been reviewed.

## TH105 workspace smoke test

This is now the optional isolation test, not the default reconstruction path.
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

## Current live autonomy checkpoint

The operator-private public URL was revalidated after adding the semantic
workflow on 2026-09-10. Discovery returned exactly 33 tools: the prior 32 plus the live-
bound `factory_report_semantic_debt` router. The public
description reports `execution_mode="registered-live-worktree-v1"`, source mode
`live-including-ignored`, local commit availability, no network, and no remote
Git push. The replay-configuration digest remained
`f3b26f68e0bf0fd12c7d29dca3c85e8070aea082839b106586ea317003361f89`;
Web-only execution mounts did not change replay identity.

The new router scanned TH095 `src` at live commit `339bb5a...` and its four-file
untracked status. It covered 197 UTF-8 C/C++ files and returned 227 raw-member
plus 829 anonymous-identifier candidates; direct absolute-address and
`unknown_fields` candidates were zero under this profile. All 1,056 results are
routing candidates only. The response was bound to current HEAD/status and
fixed completion, exactness, and semantic-evidence credit to false/none.

The same operator-private endpoint ran non-committing native toolchain probes
for all four registrations:

| Game | Actual path exercised | Result |
| --- | --- | --- |
| TH04 | Wine plus two deterministic Borland/TASM/TLINK compile/link/run rounds | Passed |
| TH08 | VC7 through `scripts/wineth08` and the existing `~/.wineth08` prefix | Passed |
| TH095 | VC7.1 compiled a fresh temporary C++ object through the existing `~/.wine` prefix | Passed |
| TH105 | VC8 SP1 compiled a fresh temporary C++ object through its repo-local prefix | Passed |

Each durable command recorded identical before/after HEAD and status digests and
created no commit. The probes confirm current operational reachability only;
all report zero exactness credit and do not create receipts.

Analysis validation independently attested TH04 and TH095 Ghidra plus TH105 IDA.
Bounded `list_functions(limit=1)` queries returned the expected target-bound
entries for both Ghidra projects. TH08 IDA remained accurately unavailable
because the active database was not the registered TH08 target. This proves the
important distinction: one immutable Ghidra installation may later be shared,
but project state and target attestation remain per-game.

At observation time TH04 and TH08 were clean, while TH095 and TH105 contained
existing local work. The concurrently active TH095 repository advanced
externally through `2079327` and `b2f2435` during validation; each toolchain
command itself began and ended on its freshly observed HEAD with
`created_commits=[]`. The Factory exposed rather than erased or
misattributed that state. Factory-owned repository work now shares the replay
advisory lock, while ordinary local-terminal changes remain observable external
events. No real-game smoke commit was created. Mutating Git checkpoint behavior
is covered in temporary repositories by the release suite, including a
`gpt-web:` commit after a nonzero command, durable output recovery, timeout
persistence, and output truncation that does not abort later work.

The final current-run TH105 replay completed as job
`job:6206df3280854c9e968254b615b3daf7`, produced passing receipt
`receipt:72e09c88ba2379229e29f80cf5bbee1eb3478ae49f632a04c0020033b5a0e24e`,
and was accepted by registry
`registry:fba55dacfee8a58501584fc87c1d3a09990f0cbb4f53819cdf58dae265fb8395`.
A subsequent read reported 17 candidates, one current accepted TH105 result,
16 rejected candidates, and zero invalid candidates.

## Initial isolated-provider checkpoint

The operator-private public URL was exercised without credentials on
2026-09-10. Remote discovery returned exactly 29 factory tools: 15
replay/registry tools, 11
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

That initial checkpoint's complete local suite passed all 105 tests. The
current game-knowledge boundary checkpoint is recorded separately in
[`validation.md`](validation.md). The installed MCP unit also reported
`NoNewPrivileges=yes`, `PrivateTmp=yes`, a 768-task limit, a 3 GiB
memory limit with swap disabled, a private umask, and core dumps disabled.

## TH09 Factory-native provider checkpoint

TH09 is the first new game that does not copy or run `mcp_for_gptweb`. The
private Factory configuration registers `th09`, `target:th09-main`, one shared
IDA Python/`ida-pro-mcp` stdio command, and the exact private target path. The
public GPT-web URL remains unchanged.

A separate local process loaded that staged configuration without restarting
the active Factory or interrupting TH095. Native discovery completed in about
2.6 seconds, exposed 47 atomic operations, and omitted the target-byte patch
tool. It independently matched target SHA-256, MD5, size, PE image base and
size, entry point, and six distributed mapped `.text` samples. A second fresh
call resolved `0x47D45F` as `start`, size `0x1D5`, with provisional authority
and zero exactness credit.

Twelve discovered operations update non-byte IDA database metadata: comments,
function/global/local/stack names, prototypes, and types. This is intentional
agent autonomy, not truth promotion. Their results remain target-bound analysis
hypotheses. Activation and a public GPT-web smoke test are deferred until the
active TH095 session can tolerate a Factory process restart.

The first staging attempt also exposed an important hot-reload boundary. The
running 0.4.0 server reloads its operator TOML on every call, so placing 0.5.0
native-provider fields in the watched live file caused TH095 control-plane calls
to fail before command creation even without a process restart. Restoring the
four-game live file immediately restored public describe, TH095 status, and
repository-shell execution at unchanged HEAD `0e6f0ef`, with zero tracked dirty
changes and the same four pre-existing untracked files. The TH09 registration
now lives only in `service.next.toml` until coordinated activation. Future
code-dependent provider changes must follow the same sidecar-validation pattern.
