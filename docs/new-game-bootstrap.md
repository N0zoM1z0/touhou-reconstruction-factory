# New-game bootstrap

## Architectural invariant

Every reconstruction uses the same public Touhou Reconstruction Factory MCP
URL. A new game does **not** receive another Web-facing MCP server, Funnel URL,
or checkout of `mcp_for_gptweb`. The game repository is an evidence-bearing
instance; the Factory is the shared control plane.

```text
GPT-web
   |
   | one stable Streamable HTTP endpoint
   v
Touhou Reconstruction Factory MCP
   |-- registered live repository work + local Git checkpoints
   |-- Truth Kernel, replay jobs, receipts, and acceptance registry
   `-- target-bound analysis provider
          |-- native IDA stdio client (preferred; TH09 first)
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

## Accuracy-first bootstrap

These steps are ordered to create a useful feedback loop without manufacturing
progress.

1. **Recover existing state first.** If a destination already exists, inspect
   tracked, untracked, and ignored state plus recent commits before changing it.
   An interrupted Web session is a continuation candidate, not permission to
   start around dirty work.
2. **Attest the target.** Record size and cryptographic hashes, parse the native
   executable format, and pin primary provenance. Use `unknown` for facts not
   demonstrated by the file or a pinned source.
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
   a fresh local process, inspect the adapter, list provider operations, and run
   a real semantic query. This does not restart or disturb the deployed Factory.
9. **Activate at a deliberate boundary.** A running MCP process must load code
   changes through a planned restart. Do not restart while another game's Web
   session or durable command is active. After activation, validate the public
   endpoint and start the game campaign with the standalone prompt.

Run the staged native-provider check with no public-service restart:

```bash
PYTHONPATH=src .venv/bin/python scripts/validate-native-analysis-provider.py \
  --config .factory/web-live/service.toml \
  --provider th09-ida \
  --operation get_function_by_address \
  --arguments-json '{"address":"0x47d45f"}'
```

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

The provider is staged in private configuration but must not be described as
available through the public endpoint until the active Factory process has been
deliberately restarted and the public validation has passed.

## Migration and future providers

`attested-ida-proxy-v1` and `attested-ghidra-proxy-v1` remain compatibility
backends so existing work continues. Do not copy them into new repositories.
Migrate one existing game at a time only after its repo/project/target binding
and representative operations pass parity checks.

A Factory-native Ghidra project selector is still incomplete. The desired
boundary is already fixed—one shared immutable Ghidra/JDK installation with
game-bound project and target state—but the current TH04 and TH095 HTTP adapters
must remain until the native broker is implemented and verified. Record this as
unknown/incomplete rather than claiming TH09's IDA mechanism already solves it.
