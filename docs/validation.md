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
mode is read-only. Supply the operator-private URL through the environment or
`--url`; the script contains no deployment endpoint:

```bash
PYTHONPATH=src FACTORY_MCP_URL="$FACTORY_MCP_URL" \
  .venv/bin/python scripts/validate-live-mcp.py
```

The default checks the exact 33-tool inventory, annotations and bounded schemas,
strict policy, all five registered adapters, imported-versus-accepted evidence
separation, real Git HEAD/dirty state, the TH095 semantic router's authority and
source binding, live accepted snapshots, registry partition, explicit unknown
knowledge, and committed historical fixtures. Mature TH04/TH08/TH095/TH105
coverage must remain nonzero; fresh TH09 accurately reports zero until a
meaningful historical regression is admitted.

Mutation and bridge checks are explicit:

```bash
PYTHONPATH=src .venv/bin/python scripts/validate-live-mcp.py --url "$FACTORY_MCP_URL" --analysis
PYTHONPATH=src .venv/bin/python scripts/validate-live-mcp.py --url "$FACTORY_MCP_URL" --repository-toolchains
PYTHONPATH=src .venv/bin/python scripts/validate-live-mcp.py --url "$FACTORY_MCP_URL" --workspace
PYTHONPATH=src .venv/bin/python scripts/validate-live-mcp.py --url "$FACTORY_MCP_URL" --replay-th105
PYTHONPATH=src .venv/bin/python scripts/validate-live-mcp.py --url "$FACTORY_MCP_URL" --all
```

The workspace check creates an idempotent TH105 committed-HEAD snapshot, rejects
path traversal, confirms the source sandbox cannot reach host home, host `/etc`,
ignored `.tools`, or the network, and confirms its Git metadata is read-only. It
then verifies command output and a candidate diff across a new MCP session,
removes its marker, requires a zero-byte final diff, and discards the workspace.

The live toolchain check invokes `factory_repository_run_shell` for every real
registration. It performs two deterministic Borland/TASM/TLINK rounds for TH04,
checks TH08 VC7 through its historical Wine prefix, and compiles fresh temporary
objects with TH095 VC7.1 and TH105 VC8 SP1. It requires identical before/after
HEAD and status digests and no created commits. These are operational probes,
not Oracle receipts.

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

## Recorded 0.6.0 and overnight-pilot deployment: 2026-09-11

The portable release gate passed all 152 tests with no skips. Ruff, bytecode
compilation, Git whitespace, three CLI construction checks, 39 JSON documents,
two TOML documents, two evaluation XML documents, and an isolated 0.6.0 wheel
build passed. The two changed reconstruction skills passed validation. The
plugin cachebuster is `0.6.0+codex.20260911021613`; the older local plugin
validator still reports only its known stale-schema objection to the official
`.app.json` `required` field.

The no-auth MCP and worker restarted behind the unchanged operator-private
route. Read-only validation passed with 33 tools and five registered games. The
new policy/runner epoch classified all 76 earlier receipt candidates as stale
and none as invalid. Analysis validation target-attested TH04 and TH095 Ghidra
and the active TH09 Factory-native IDA provider. All 47 TH09 operations exposed
non-null input schemas. TH08 and TH105 IDA accurately reported unavailable
because the one active Windows IDA database was TH09.

The first durable public TH09 replay selected the existing exact claim at
`0x00401340`. Job `job:068b629593934851ba515422222f3d97` completed on its first
attempt; receipt
`receipt:2090a0819180d51f6ef1bc13b6ae1ad1d331cd0ec326b158af308971c1a85396`
passed, strict-live-v1 accepted it, and the current accepted-facts query returned
exactly that claim/receipt pair. The complete measured overnight campaign and
its preserved dirty recovery state are recorded in
[`overnight-web-pilot-2026-09-11.md`](overnight-web-pilot-2026-09-11.md).

## Recorded semantic-workflow run: 2026-09-10

The MCP-enabled release gate passed all 139 tests with no skips. Ruff, bytecode
compilation, Git whitespace, three CLI construction checks, 37 JSON documents,
two TOML documents, two evaluation XML documents, and an isolated 0.4.0 wheel
build passed. All five bundled skills passed the skill validator. The plugin
cachebuster is `0.4.0+codex.20260910093008`. The older local plugin validator
still reports only its known stale-schema error for the official `.app.json`
`required` field; the Factory tests validate the current required-app shape.

The no-auth MCP and worker restarted in place behind the unchanged Funnel URL.
Public read-only validation passed with exactly 33 tools. The new
`factory_report_semantic_debt` tool scanned the real TH095 live `src` scope at
`339bb5a...` and its four-file untracked status: 197 UTF-8 C/C++ source files,
227 raw-member candidates, 829 anonymous-identifier candidates, zero direct
absolute-address candidates, zero `unknown_fields` candidates, and 1,056 total.
The scope was complete under `c-cpp-layout-heuristics-v1`; the report was bound
to the live HEAD/status digest and returned `routing_only=true`,
`completion_metric=false`, and zero exactness/semantic-evidence credit.

Public analysis validation independently re-attested TH095 Ghidra and returned
one bounded function query under target `target:th095-main`. TH04 Ghidra and
TH105 IDA also passed; TH08 IDA accurately remained unavailable for its current
active database. The registry partition remained 17 rejected stale candidates,
zero accepted, and zero invalid. No game repository was modified by these
checks.

## Recorded product-closure run: 2026-09-10

The MCP-enabled release gate passed all 135 tests with no skips. Ruff,
bytecode compilation, Git whitespace, three CLI construction checks, 36 JSON
documents, two TOML documents, two evaluation XML documents, and an isolated
0.4.0 wheel build passed. All four bundled skills passed the skill validator.
The plugin cachebuster is `0.4.0+codex.20260910082918`. The older local plugin
validator still reports only its known stale-schema error for the official
`.app.json` `required` field; the Factory tests validate the current
required-app shape.

After an idle-job check, the same no-auth MCP and worker services were restarted
in place. Public read-only validation passed against the fixed URL with all 32
tools. The new policy/runner epoch correctly rejected all 17 historical receipt
candidates as stale and accepted none; no candidate was invalid. This is an
expected freshness boundary, not lost historical job state.

The live TH095 adapter now reports 5,154 claims and two historical fixtures. A
direct public MCP query for `claim_type=whole_build_closed` returned exactly one
extent-free product candidate with 88 sources, two profiles, i386 COFF compile,
PE32 i386 Windows GUI output, zero-unresolved policy, and
`whole_image_exact=false`. The adapter still imports zero Oracle results. The
active TH095 worktree had independently advanced to `339bb5a...` with four
untracked files, so no public replay was submitted against that moving tree.

A separate clean clone at immutable TH095 commit `3442dcf...` completed the
real 88-TU product replay. Receipt integrity and live freshness passed, and the
final strict policy admitted the sole candidate with zero rejected or invalid
entries. The receipt, registry, compiler/linker hashes, source binding, coverage,
duration, output format/hash observation, and the explicit absence of runtime
credit are recorded in [`replay-validation.md`](replay-validation.md). Unit
tests independently exercise the same extent-free coverage through the durable
job/registry path, so GPT-web uses the existing generic claim/job tools rather
than a game-specific MCP method.

## Earlier autonomy run: 2026-09-10

The MCP-enabled release gate passed all 127 tests with no skips. Ruff, bytecode
compilation, Git whitespace, three CLI construction checks, 34 JSON documents,
two TOML documents, two evaluation XML documents, and an isolated 0.4.0 wheel
build passed. All four bundled skills passed the skill validator. The plugin
cachebuster is `0.4.0+codex.20260910053008`. The older local plugin validator
reports only its known stale-schema error for the official `.app.json`
`required` field; the Factory tests validate the current required-app shape.

Public discovery returned 32 tools and the fixed URL exposed live status for all
four games. The non-committing toolchain probes passed for TH04, TH08, TH095,
and TH105 through the MCP runner, including both global legacy Wine prefixes and
both repo-local tool layouts. Each command preserved the observed real-game HEAD
and status digest.

Target-attested analysis passed for TH04 Ghidra, TH095 Ghidra, and TH105 IDA.
Both Ghidra providers also returned one bounded function query from their own
registered projects. TH08 IDA accurately remained unavailable because the
active database did not match the registered target. Every analysis response
retained `authority=provisional-semantic-analysis` and
`exactness_credit=none`.

The live worktrees were not normalized for the test: TH04 and TH08 were clean,
while TH095 and TH105 contained pre-existing local work. The concurrently active
TH095 repository advanced externally through `2079327` and `b2f2435` between
snapshots and later toolchain commands. Each command began and ended at the HEAD
it observed immediately before execution with no created commit, so the external
Codex checkpoints were not misattributed to validation. This is
intended evidence that the provider sees rather than erases current state and
does not pretend to own ordinary local-terminal activity. Factory-owned work,
analysis, snapshots, registry reads, and replay share an advisory per-repository
lock. Temporary-repository tests cover that coordination plus edits, failed and
timed-out command persistence, ignored/shared/state tool visibility, durable
output, and local `gpt-web:` commits.

The final source-bound TH105 replay produced:

- job `job:6206df3280854c9e968254b615b3daf7`;
- receipt `receipt:72e09c88ba2379229e29f80cf5bbee1eb3478ae49f632a04c0020033b5a0e24e`;
- registry `registry:fba55dacfee8a58501584fc87c1d3a09990f0cbb4f53819cdf58dae265fb8395`;
- state/verdict/decision `completed` / `pass` / `accepted`;
- four ordered events and four content-addressed artifacts.

A fresh public read after completion reported 17 receipt candidates: one
accepted, 16 rejected, and zero invalid. The accepted TH105 snapshot contained
exactly one Oracle result and fingerprint
`4470cbd274f3ab0c6078244b1863dca96a0ea4b5248b4609301ecf58114928c3`.
TH04, TH08, and TH095 remained at zero accepted results; native adapter claims
and successful operational probes were not promoted.

## Earlier acceptance/workspace run: 2026-09-10

The MCP-enabled release gate passed all 116 tests with no skips. Ruff, bytecode
compilation, Git whitespace, three CLI construction checks, 32 JSON documents,
two TOML documents, the 11-scenario MCP and 12-scenario reconstruction
evaluation XML documents, and the isolated wheel build also passed. The plugin
manifest and both modified bundled skills passed the plugin-creator and
skill-creator validators after cachebuster version
`0.3.0+codex.20260910020626` was generated.

The final public `--all` run observed the following adapter state:

| Repository | Adapter | Imported claims | Accepted oracle results | Historical fixtures |
|---|---|---:|---:|---:|
| TH04 | `th04-pc98-v1` | 4,393 | 0 | 4 |
| TH08 | `th08-vc7-ledgers-v1` | 6,925 | 0 | 2 |
| TH095 | `windows-pe-ledgers-v1` | 5,153 | 0 | 1 |
| TH105 | `windows-pe-ledgers-v1` | 10,735 | 1 | 4 |

Every adapter continued to import zero native `OracleResult` objects. The live
registry contained nine receipt candidates: one accepted, eight rejected as
stale, and zero invalid. The older receipts were rejected for changed runner,
driver, oracle, and source bindings after the Factory update. They were not
grandfathered into the new epoch. TH04, TH08, and TH095 still have no accepted
live oracle result.

Analysis probes succeeded with target attestation for `th04-ghidra`,
`th095-ghidra`, and `th105-ida`; all retained
`authority=provisional-semantic-analysis` and `exactness_credit=none`.
`th08-ida` failed closed during discovery because its active database did not
attest as TH08. The run recorded this as accurately unavailable rather than
substituting another target.

The final disposable-session check used workspace
`workspace:a2bdf85aead440d2955c8d456bb85988` and command
`command:7cc472ee8b204712af31c415593cd1e8`. It exercised the corrected
same-UID process-limit headroom through the public endpoint, resumed through a
new MCP connection, recovered output and diff, returned to a zero-byte diff,
and ended discarded.

The Factory update changed the runner implementation binding, so the accepted
replay was newly submitted rather than recovered from an obsolete pass:

- claim: `claim:th105-main:function:00401000:codegen-exact`;
- job: `job:95488603014a48f68801a34ab6a76dd2`;
- receipt: `receipt:fc2c738464c6373f35665ec8ab270b2d61f440bc59c83b90c05d6a8f9e92f825`;
- registry: `registry:cf86b181b3f46eec42072eb72b9963bc7c3e41e94ceea429589075a036f1bc20`;
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

## Recorded freshness-performance run: 2026-09-10

The release suite passed 142 tests after adding request-scoped freshness
observation reuse and exact-byte TOML parse caching. The deployed no-auth MCP
retained its 33-tool interface. Its active TH095 semantic checkpoint was cold
replayed through 13 function claims and the complete 88-source Windows i386
product claim after the runner fingerprint changed; all 14 returned native
`pass` and registry `accepted`.

Public acceptance-registry latency fell from 15.493/14.132 seconds for 31
candidates to 2.683/1.897/1.918 seconds for 59 candidates. The accepted-facts
query fell from 7.125 seconds to 2.262/2.171/2.169 seconds. The post-change
registry was stable across all reads and reported 14 accepted, 45 rejected,
and zero invalid candidates. A complete validation of the public endpoint also
passed with all 33 tools and all four configured game adapters. These are
observed timings on the single-user live host, not portable performance
guarantees.

## Recorded campaign and fail-fast run: 2026-09-10

The second release suite passed 148 tests and parsed 38 JSON, two TOML, and two
XML documents. It added exact-byte adapter TOML caching, terminal runner-stale
short-circuit tests, an auditable replay-execution fingerprint scope, compact
registry and accepted-fact projections, the semantic campaign v2 contract, and
22 independent GPT-web workflow scenarios. The semantic skill passed the
current quick validator. The local plugin validator retained its documented
schema mismatch for the current `.app.json` `required: true` field; the field
was intentionally preserved because it is the current ChatGPT app dependency
contract.

The final public MCP read-only validation passed with 33 tools and all four
configured adapters. TH095 remained at 14 accepted results after a controlled
runner rollover: 13 function-exact results and one 88-source Windows i386
product-closure result. The final store contained 73 candidates, 59 rejected
historical receipts, and zero invalid candidates.

The 73-candidate registry summary had a 0.757-second five-read median and a
308-byte response. Compact TH095 accepted facts had a 1.097-second five-read
median and an 11,561-byte response; full facts had a 1.415-second median and a
27,039-byte response. A later acceptance/MCP-only change and service restart did
not invalidate the final receipts, directly exercising the new separation
between replay-execution identity and control-plane presentation.

## Deliberate limitations

These runs prove only their explicitly listed receipt claims. The latest live
store admits 13 TH095 function-exact claims and one TH095 Windows i386 product-
closure claim; it does not thereby prove whole-image equality, every initialized-
data owner, runtime equivalence, semantic correctness, or game completion.
Unreceipted claims for TH04, TH08, TH095, and TH105 remain unknown until a
supported factory-controlled replay produces a fresh receipt accepted by policy.
Local validators prove the prompt assets, plugin structure, and recorded
behavioral scenarios; they cannot prove that a particular ChatGPT account has
refreshed the new plugin version or will automatically select the orchestration
skill. Test that UI behavior in a new conversation after refreshing the
installed plugin, preferably by selecting it explicitly with `@` for the first
run.
