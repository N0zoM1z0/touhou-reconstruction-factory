# Release and live validation

The validation contract below is current. The checkpoint sections between it
and `Deliberate limitations` are point-in-time evidence records, including
headings that begin with `Recorded`, `Bounded`, or `Earlier`; they are not a
live status page. Never carry their receipt IDs, counts, commits, timings, or
provider availability forward without a new observation.

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
strict policy, all six registered adapters, imported-versus-accepted evidence
separation, real Git HEAD/dirty state, the TH095 semantic router's authority and
source binding, live accepted snapshots, registry partition, explicit unknown
knowledge, and committed historical fixtures. Mature TH04/TH08/TH095/TH105
historical-fixture coverage must remain nonzero; the newer TH09 and TH10
registrations accurately report zero historical fixtures until meaningful
regressions are reviewed and admitted.

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

The live toolchain check invokes `factory_repository_run_shell` for the five
maintained operational probes. It performs two deterministic
Borland/TASM/TLINK rounds for TH04, checks TH08 VC7 through its historical Wine
prefix, compiles fresh temporary objects with TH095 VC7.1 and TH105 VC8 SP1,
and makes TH10 attest its pinned VC7.1 SP1 components before headlessly
compiling normal C/C++ COFF and C++ LTCG, compiling a resource, and linking a
PE32 i386 image. It requires identical before/after HEAD and status digests and
no created commits. These are capability probes, not target-codegen or product
closure receipts.

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

## Recorded 0.7.0 TH10 native-Ghidra deployment: 2026-09-12

The portable release gate passed all 155 tests with no skips. Ruff, bytecode
compilation, Git whitespace, three CLI construction checks, 42 JSON documents,
two TOML documents, two evaluation XML documents, and an isolated 0.7.0 wheel
build passed. The native-Ghidra analysis skill passed its quick validator. The
plugin cachebuster is `0.7.0+codex.20260912065904`; the local plugin validator
still reports only its recorded stale-schema objection to the ChatGPT
`.app.json` `required` field, which remains intentionally present.

The MCP and worker were restarted together behind the unchanged private Funnel
route and stayed active with zero restarts. Public read-only validation passed
the same 33 tools and six registered games. TH10 reported 2,390 imported claims,
zero accepted Oracle results, and zero historical fixtures. Across the current
runner epoch the registry accurately classified all 125 older candidates as
rejected and none as invalid; activation did not manufacture accepted facts.

The public analysis run target-attested TH04 and TH095 legacy Ghidra, TH10
Factory-native Ghidra, and the currently active TH105 IDA database. TH08 and
TH09 IDA accurately reported unavailable because a different Windows database
was active. TH10 exposed all ten bounded schemas, passed `check` and
`list_functions(limit=1)`, and returned the entry function at `0x004537DC`
through a separate public call. That result carried target `target:th10-main`,
transport `factory-native-command`, six mapped-byte samples, implementation
binding `62c66f14aa31c4ed6ed51a57276c2b14ad2b2f7110402a2ad750319228a58f9a`,
provisional authority, and zero exactness credit.

A public TH10 live-repository probe verified the target, Ghidra/JDK pins, all
1,195 provisional tracking rows, progress artifacts, public CI, and readable
TH08/TH09/TH095 adjacent repositories. It exited zero with unchanged HEAD and
status and created no commit. TH10's public GitHub CI passed independently at
commit `2c0a6ab`.

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

### Recorded GPT-web reconnect boundary: 2026-09-11

A GPT-web semantic campaign attempted after the 0.6.0 deployment reported a
connection error for both `factory_list_repositories` and `factory_describe` and
correctly stopped without touching TH095. At diagnosis time both user services
were active with zero automatic failure restarts, a new public Streamable HTTP
handshake returned Factory 0.6.0 and all 33 tools, and the MCP journal contained
no failed or denied request from that Web attempt. The established evidence did
not support a repository, tool-schema, or server-handler failure; it located the
interruption before MCP ingress. It could not distinguish a call made during the
short restart interval from stale client-side connection state.

The operational repair is to retain the fixed private URL and App Id, require a
passing public validator after every deployment, then select **Refresh** on the
Developer-mode connection and begin a new conversation. The detailed decision
tree is recorded in
[`Restart and reconnect contract`](gpt-web-plugin.md#restart-and-reconnect-contract).
No second server restart or Factory version change is required for this
recovery.

## Recorded semantic closure-boundary correction: 2026-09-11

The TH095 history supplied a direct falsification of Web-authored phase closure:
SEM-059 reported the compact enemy `+0x285C` state as readerless and declared
readiness, while the next conversation found the missed `enter_subroutine`
consumer and recovered its ECL subroutine table in SEM-060. SEM-062 later
reviewed seven named Enemy/ECL residual families, but its active source state
still contained 991 lexical routing candidates across 197 C/C++ files, only 33
C/C++-like paths had changed across the 63 semantic Web checkpoints, and runtime
storage/scenario validation remained unknown. Those counts are work-routing
evidence, not completion percentages; the counterexample establishes the
authority error independently of them.

Semantic campaign contract v3 therefore removed the Web-authored stop
condition, defaults every new conversation to `active-incomplete`, requires an
adversarial attempt to falsify inherited readiness prose, and reserves phase
closure and port authorization to a later independent Codex or human review.
A bounded negative search must rotate to another coverage surface and cannot by
itself justify completion or an immediate handoff.

The live TH09/TH095 browser runs then exposed a separate duration bug: v3's
instruction to continue in the same conversation could eventually make the Web
client unusable. General contract v5 and semantic contract v4 preserve the
open-ended campaign but make each conversation adaptive and bounded. Web chooses
when another batch would threaten browser or context reliability, closes or
reverts the active transaction, checkpoints coherent work, and hands off as
`active-incomplete`. The external browser mechanism used by the operator to
start later chats is intentionally absent from prompts and contracts. The
prompt, bundled skill/reference, plugin defaults, ontology, reader flow, and
evaluation scenarios use this corrected separation.

The review also caught a mutable ignored-product distinction instead of
silently choosing one hash: SEM-062 recorded a 780,288-byte product with SHA-256
`37ac38ca...6251`, while a later same-source-HEAD ignored build report recorded
`384a6458...3160`. Compile/link closure is the durable claim; neither
rebuild-local hash is treated as a stable source invariant without a
deterministic-artifact contract.

## Bounded Web-conversation prompt validation: 2026-09-11

General reconstruction contract v5 and semantic contract v4 were checked with
the nine focused `test_web_assets.py` scenarios. They preserve the v4/v3
evidence and authority contracts while requiring adaptive bounded browser
conversations, repository-backed continuation, no fixed batch quota, and no Web
phase closure. The same check binds the new TH04 prompt to `th04-ghidra`,
`target:th04-main`, 16-bit MZ/OMF and Borland/TASM/TLINK rules; binds TH09 to
`th09-ida`, `target:th09-main`, VC7.1 Windows i386; and confirms both exact
prompts express the moving 99.5% authored-function/authored-byte pressure target
without relabeling it as whole-game coverage.

Both changed bundled skills passed `quick_validate.py`; the focused test module
passed Ruff; the new contracts parsed as JSON; the evaluation XML parsed through
the focused tests; and `git diff --check` passed. The older system plugin
validator still rejects the registered ChatGPT `.app.json` app entry's
`required` field. That is the already recorded validator/schema mismatch, not a
new package error; removing the field would break the working registered-app
binding. Cachebuster `0.6.0+codex.20260911063659` publishes the changed skill
text when the plugin is next synced. No MCP or worker restart is required for
the prompt/document changes.

Focused validation passed all eight `tests.test_web_assets` tests, Ruff for the
changed test module, Git whitespace checks, three changed JSON parses, and the
changed evaluation XML parse. The semantic skill passed the current quick
validator. The plugin validator retained its already documented mismatch with
the required ChatGPT `.app.json` `required` field; that current app dependency
contract was not weakened to satisfy the older validator. A full release suite
and live MCP restart were deliberately not run: this correction changes
documentation, prompt/skill, machine-readable campaign policy, evaluation text,
and plugin cache identity, but no MCP implementation, provider, runner,
registry, or replay behavior.

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

Each recorded run proves only its explicitly listed receipt claims. In
particular, the 0.7.0 activation record above observed zero accepted candidates
in its new runner epoch and 125 older rejected candidates; older sections record
different stores and runner epochs. None is an evergreen description of the
live registry. Query it again before reporting accepted facts.

An accepted bounded exact or product-closure receipt does not thereby prove
whole-image equality, every initialized-data owner, runtime equivalence,
semantic correctness, or game completion. Every claim without a current,
supported, policy-accepted Factory replay remains unknown, for all registered
games.
Local validators prove the prompt assets, plugin structure, and recorded
behavioral scenarios; they cannot prove that a particular ChatGPT account has
refreshed the new plugin version or will automatically select the orchestration
skill. Test that UI behavior in a new conversation after refreshing the
installed plugin, preferably by selecting it explicitly with `@` for the first
run.
