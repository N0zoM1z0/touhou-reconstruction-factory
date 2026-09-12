# New-game bootstrap

## Architectural invariant

Every reconstruction uses the same operator-private Touhou Reconstruction
Factory MCP URL. A new game does **not** receive another Web-facing MCP server,
Funnel URL, or checkout of `mcp_for_gptweb`. The game repository is an
evidence-bearing instance; the Factory is the shared control plane.

```text
GPT-web
   |
   | one operator-private stable Streamable HTTP endpoint
   v
Touhou Reconstruction Factory MCP
   |-- registered live repository work + local Git checkpoints
   |-- Truth Kernel, replay jobs, receipts, and acceptance registry
   `-- target-bound analysis provider
          |-- native IDA stdio client (preferred; TH09 first)
          |-- native Ghidra command selector (preferred; TH10 first)
          `-- legacy IDA/Ghidra HTTP adapter (migration only)
```

The ownership boundary is deliberate:

| Location | Owns |
| --- | --- |
| Game repository | target manifest, ledgers, source, build graph, game-local workflow, game-local knowledge, ignored transient analysis state |
| Factory tracked source | ontology, adapters, provider contracts, shared workflows, prompts, regression fixtures, Truth Kernel policy |
| Factory private service configuration | canonical repo paths, private target paths, shared tool executables, mutable state roots, live provider selection |
| GPT-web | autonomous composition of repository Bash and atomic analyzer tools; coherent local commits, never remote push |

Tool sharing never implies state sharing. One IDA/Ghidra installation can serve
many games, but each provider binds one repository, one immutable target
identity, and one game-specific database/project. Wine is similarly shared as a
runtime while prefixes and target/toolchain selection remain game-bound.

## Private target staging invariant

Copy each legally supplied original game executable from the host installation
into the WSL game repository before Web work begins. Its canonical location is
`resources/<game>.exe` (for example, TH09 uses `resources/th09.exe`). Add the
exact path to the game repository's `.gitignore`, keep the file untracked and
operator-owned, and verify its hash and native-image metadata against the
tracked target manifest. The game `AGENTS.md`, standalone Web prompt, repository
scripts, and private analysis-provider binding must all name that same WSL-local
copy.

Do not solve target availability by mounting a Windows game directory into the
repository shell. Repository agents should neither search `/mnt` nor depend on
an operator-specific drive layout. `THxx_TARGET_PATH`-style variables are only
explicit local overrides, not the normal Factory contract. Shared Windows tools
such as IDA or MSVC may still be launched from their provider installation; that
does not make the host game directory a repository input.

## Accuracy-first bootstrap

These steps are ordered to create a useful feedback loop without manufacturing
progress.

1. **Recover existing state first.** If a destination already exists, inspect
   tracked, untracked, and ignored state plus recent commits before changing it.
   An interrupted Web session is a continuation candidate, not permission to
   start around dirty work.
2. **Stage and attest the target.** Copy it to the ignored
   `resources/<game>.exe` path, confirm Git ignores the exact file, record size
   and cryptographic hashes, parse the native executable format, and pin primary
   provenance. Bind repository tools and the private analyzer provider to this
   WSL-local copy. Use `unknown` for facts not demonstrated by the file or a
   pinned source.
3. **Identify only evidenced toolchain facts.** PE linker and Rich-header facts
   may identify a compiler generation. They do not reveal flags, translation
   units, library selection, resources, or link order; initialize those as
   unknown.
4. **Create zero-state Truth Kernel inputs.** Import the disassembler's
   candidate inventory as provisional boundaries/origins. Start source,
   ownership, and exactness ledgers empty. A discovered function is not
   authored, implemented, or exact.
5. **Create a whole-build skeleton immediately.** It may explicitly report
   `open` while compiler profile, source graph, and link policy are unknown. Do
   not postpone ownership, initialized data, resources, imports, relocations,
   and product closure until function exactness is complete.
6. **Keep the historical platform product before semantic work.** The faithful
   sequence is target/exact reconstruction, corresponding platform build
   closure (Windows i386 here; 16-bit for PC-98), semantic reconstruction using
   both exact and native-product/runtime Oracles, then portable ports.
7. **Register the repo once in the Factory.** Add a private repository entry and
   one target-bound analysis provider. GPT-web continues using the same Factory
   URL and selects the game by repository/provider ID.
8. **Validate without activating.** Load the candidate private configuration in
   a fresh local process from a separate file such as `service.next.toml`,
   inspect the adapter, list provider operations, and run a real semantic query.
   Do not place fields that require new code into the configuration watched by
   an older running process. This does not restart or disturb the deployed
   Factory.
9. **Activate at a deliberate boundary.** A running MCP process must load code
   changes through a planned restart. Switch the staged configuration only as
   part of that activation. Do not restart while another game's Web session or
   durable command is active. After activation, validate the public endpoint
   and start the game campaign with the standalone prompt.
10. **Allowlist adjacent hypotheses deliberately.** When a new game benefits
    from nearby reconstructions, add their registered IDs to the new game's
    private `reference_repository_ids`. The repository runner mounts only those
    checkouts read-only. Adjacent source and history can accelerate a
    hypothesis, but never transfer target facts, ownership, ABI, exactness, or
    completion; a reference that is still undergoing semantic work is more
    provisional still.
11. **Make the campaign long-lived and each Web conversation bounded.** The
    standalone prompt gives a strong phase objective, autonomous tools, fast
    feedback, and frequent checkpoints, but never asks one chat to finish the
    whole phase. Web chooses a safe handoff point from packet difficulty,
    validation latency, browser responsiveness, and context reliability. Exact
    prompts may use a moving 99.5% reviewed authored-function/authored-byte
    pressure target while continuing boundary discovery; crossing it is not
    phase closure. Do not mention an operator's browser scheduler or userscript
    in the prompt. The repository and handoff are the only continuation
    interface the reconstruction agent needs.

Run the staged native-provider check with no public-service restart:

```bash
PYTHONPATH=src .venv/bin/python scripts/validate-native-analysis-provider.py \
  --config .factory/web-live/service.next.toml \
  --provider th10-ghidra \
  --operation function \
  --arguments-json '{"addresses":["0x004537DC"]}'
```

### Hot-reload compatibility trap

The Factory MCP loads operator configuration for each public tool call. That is
useful for compatible repository/path changes, but it means configuration is
not isolated merely because the process was not restarted. On 2026-09-10, a
native TH09 provider block was briefly added to the live file while the running
0.4.0 process still had the legacy parser. TH095 calls then correctly failed
before command creation with missing legacy `endpoint`/`upstream_tool` fields
and unexpected native `command`/`arguments`/`target_path` fields.

The live four-game file was restored immediately. Public `factory_describe`,
TH095 status, and a real repository-shell command then succeeded with unchanged
TH095 HEAD and dirty counts; the native TH09 registration moved to
`service.next.toml` and passed separate validation. No TH095 source command was
created during the failure. The durable rule is: **never stage a code-dependent
configuration variant in the path watched by an incompatible live process**.

## Native IDA registration

`attested-ida-stdio-v1` replaces the old per-game MCP layer:

```toml
[[analysis_providers]]
id = "th09-ida"
repository_id = "th09"
target_identity_id = "target:th09-main"
backend = "attested-ida-stdio-v1"
command = "/absolute/path/to/ida-python.exe"
arguments = ["D:\\IDA\\python\\Lib\\site-packages\\ida_pro_mcp\\server.py"]
target_path = "/absolute/private/path/to/th09.exe"
timeout_seconds = 120

[[repositories]]
id = "th09"
path = "/absolute/path/to/th09-reconstruction/th09"
adapter_id = "windows-pe-ledgers-v1"
target_identity_ids = ["target:th09-main"]
```

The command, arguments, and target path are private binding material. Public
discovery exposes their digest and capabilities, not the paths.

Before every discovery or call, the native provider reloads the game adapter,
hashes and parses the private PE, opens one `ida-pro-mcp` stdio session, checks
active IDA metadata and entry point, and compares six deterministic distributed
`.text` samples. The actual requested operation then runs in the same session,
so the strong attestation adds no repeated process startups inside that call.

The native contract exposes all current semantic reads and useful IDA database
metadata operations (comments, names, prototypes, types, and stack metadata).
Those operations are composable and persistent in the operator's IDA database.
They remain provisional hypotheses with zero exactness credit. The target-byte
patch operation is not exposed because it would invalidate the target used by
the exactness workflow.

## Native Ghidra registration

`attested-ghidra-command-v1` replaces the legacy per-game Ghidra MCP/HTTP
bridge. The public game repository contains a fixed-grammar wrapper and Ghidra
Java scripts; the private Factory configuration binds that wrapper to one
ignored target and project:

```toml
[[analysis_providers]]
id = "th10-ghidra"
repository_id = "th10"
target_identity_id = "target:th10-main"
backend = "attested-ghidra-command-v1"
command = "/absolute/path/to/factory/.venv/bin/python"
arguments = ["/absolute/path/to/th10/scripts/ghidra.py"]
target_path = "/absolute/path/to/th10/resources/th10.exe"
implementation_files = [
  "/absolute/path/to/th10/config/target.toml",
  "/absolute/path/to/th10/config/tools.lock.toml",
  "/absolute/path/to/th10/scripts/ghidra.py",
  "/absolute/path/to/th10/scripts/ghidra/QueryProgram.java",
  "/absolute/path/to/th10/scripts/ghidra/VerifyTarget.java",
]
implementation_sha256 = "<aggregate lowercase SHA-256>"
timeout_seconds = 900
```

Install and hash-pin Ghidra/JDK once below private Factory-managed storage. A
new game gets ignored `.tools/ghidra` and `.tools/jdk` selectors plus its own
ignored `ghidra-project/<GAME>` state. Initial import is an operator bootstrap;
GPT-web receives only read-only check/decompile/function/disassembly/call/xref/
listing/string operations. Every query process verifies the target manifest,
Ghidra/JDK pins, project program, entry function, and distributed mapped bytes
before returning semantic output. Pin every implementation/config/script file
that can select or attest those surfaces in a private aggregate digest. A Web
edit to provider code must fail closed until local review refreshes that digest.

Render the complete sorted file list, per-file hashes, and aggregate binding
instead of calculating the registration by hand:

```bash
PYTHONPATH=src .venv/bin/python scripts/render-native-ghidra-registration.py \
  --repository /absolute/path/to/th10-reconstruction/th10 \
  --repository-id th10 --provider-id th10-ghidra \
  --target-identity-id target:th10-main \
  --target-path /absolute/path/to/th10/resources/th10.exe
```

Review the emitted paths and hashes, then copy the block into private service
configuration. Never commit that operator configuration to a game repository.

## TH09 reference bootstrap

TH09 is the first clean Factory-native instance. Its initial repository is
`N0zoM1z0/th09`, locally organized as `th09-reconstruction/th09`.

The attested original Japanese v1.50a executable has:

- size `685056`;
- SHA-256
  `10350095bcf95edb59e03bee9849a2dc8a7714b4927ad5909c569c550fce6822`;
- MD5 `cf634df46e05552e104fa97a971aaac0`;
- PE32 i386 image base `0x00400000`;
- entry point `0x0047D45F`; and
- VC7.1 build-3077 evidence, while compiler flags and source/link ownership
  remain unknown.

The bootstrap imported 2,159 unique nonzero IDA candidate functions, all as
`unknown/review`, and produced zero source mappings, zero implemented rows, and
zero exact rows. The generic `windows-pe-ledgers-v1` adapter reports 2,160
subjects and 4,318 imported claims, but no `OracleResult(pass)`. That is the
correct zero-state distinction between inventory and reconstructed truth.

The staged Factory-native provider was validated directly against the live TH09
IDA database on 2026-09-10. Discovery returned 47 atomic operations (all 35
read operations plus 12 database metadata operations; target-byte patching was
absent), completed in about 2.6 seconds, and passed SHA-256/MD5/size, PE image,
entry-point, and six mapped-byte checks. A target-bound
`get_function_by_address(0x47D45F)` returned `start`, size `0x1D5`, with
`authority=provisional-semantic-analysis` and `exactness_credit=none`.

The provider was activated and publicly validated in the later Factory 0.6.0
deployment; it remains the native IDA reference.

## TH10 native Ghidra reference bootstrap

TH10 is the first clean native Ghidra instance, locally organized as
`th10-reconstruction/th10`. The original Japanese v1.00a target is size
`487936`, SHA-256
`2f14760b6fbbf57549541583283badb9a19a4222b90f0a146d5aa17f01dc9040`,
PE32 i386 at image base `0x00400000`, entry `0x004537DC`. PE linker 7.10
and dominant Rich build-6030 records support only a VC7.1 SP1-era hypothesis;
compiler surfaces, flags, source partition, libraries, resources, and link order
remain unknown.

The first hash-attested Ghidra 12.1.3/JDK 21.0.12.1+1 import produced 1,195
provisional candidates, all `unknown/review`, with zero source mappings and zero
exact claims. Native discovery and a real entry-function query both passed the
Factory's independent PE identity plus six mapped-byte observations. This is
the reusable Ghidra bootstrap, not evidence that any function is authored or
reconstructed.

## Migration and future providers

`attested-ida-proxy-v1` and `attested-ghidra-proxy-v1` remain compatibility
backends so existing work continues. Do not copy them into new repositories.
Migrate one existing game at a time only after its repo/project/target binding
and representative operations pass parity checks.

TH10 is the validated native Ghidra selector reference. TH04 and TH095 remain
on compatibility bridges until their existing projects can be migrated and
representative results checked without disturbing active reconstruction state.
