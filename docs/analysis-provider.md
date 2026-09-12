# Attested Analysis Provider

## Purpose and authority

The analysis provider gives GPT-web bounded semantic access to the target used
by a reconstruction repository. The preferred architecture is one shared
Factory MCP that owns its local analyzer client; a game repository does not run
or expose a second MCP server. Private executable paths, target paths, mutable
analysis projects, and host Bash stay outside the public protocol.

Analysis output is always provisional. The response envelope fixes this
semantics in machine-visible fields:

- `authority = "provisional-semantic-analysis"`;
- `exactness_credit = "none"`;
- the registered repository and target identity;
- a provider-binding SHA-256;
- target attestation state;
- operation and canonical argument digest;
- observation time and bounded output metadata.

A decompilation, name, xref, candidate boundary, or database type can guide
source recovery. None proves source authorship, compilation identity, byte
equality, relocation closure, physical ownership, or a complete extent. Those
claims still require a factory-controlled canonical replay receipt.

## Registration boundary

Each provider is operator-registered in the private service configuration with
an ID, repository ID, target identity ID, backend, and timeout. Private backend
selection fields are part of the provider-binding digest but are omitted from
public responses.

Four contracts are supported during migration:

- `attested-ghidra-command-v1` is Factory-native. It declares a local command
  wrapper, exact private target, one shared immutable Ghidra/JDK installation,
  and a game-specific ignored project. The Factory launches the command itself;
  every bounded read performs target/project attestation in the same headless
  process as the query;
- `attested-ida-stdio-v1` is Factory-native. It declares the shared IDA Python
  executable, `ida-pro-mcp` server argument, and exact private target file. The
  Factory launches stdio itself; there is no endpoint or upstream wrapper tool;
- `attested-ida-proxy-v1` calls only upstream `ida_call`;
- `attested-ghidra-proxy-v1` calls only upstream `ghidra_call`.

The last two are legacy loopback compatibility contracts and accept only exact
loopback HTTP URLs. Those bridges may also implement `run_command`, but the Factory never
names or forwards that tool. The public MCP therefore cannot cross from an
analysis request into legacy host Bash.

TH09 is the first fully Factory-native game. It does not contain
`mcp_for_gptweb`, a private HTTP bridge, or a game-specific Web URL. Its public
repository declares target and workflow facts; the operator's private Factory
configuration selects the shared analyzer installation and target path. Older
games remain on compatibility providers only until their working analysis
state can be migrated and re-attested.

TH10 is the first fully Factory-native Ghidra game. Its public repository owns
the small headless wrapper and Java query scripts, while private Factory state
owns the single shared Ghidra/JDK payload and `resources/th10.exe`. The mutable
`ghidra-project/TH10` database remains game-specific and ignored. This selector
replaces both the legacy per-game HTTP bridge and any per-game public URL.

The private single-operator configuration registers:

| Provider | Repository | Backend | Target scope |
| --- | --- | --- | --- |
| `th04-ghidra` | `th04` | attested headless Ghidra | `target:th04-main` |
| `th08-ida` | `th08` | attested IDA Pro | `target:th08-main` |
| `th09-ida` | `th09` | Factory-native IDA Pro | `target:th09-main` |
| `th095-ghidra` | `th095` | attested headless Ghidra | `target:th095-main` |
| `th10-ghidra` | `th10` | Factory-native headless Ghidra | `target:th10-main` |
| `th105-ida` | `th105` | attested IDA Pro | `target:th105-main` |

This is operator configuration, not a cross-game claim that one backend is
universally correct. A provider can be absent, offline, busy, or correctly fail
attestation; the result is unavailable/unknown rather than fallback to a
different target.

The checked TH04 and TH095 deployments remain on their legacy per-project
bridges until deliberate migration. TH10 proves the replacement boundary:
Ghidra 12.1.3 and Temurin JDK 21.0.12.1+1 are hash-pinned once in private
Factory-managed storage, selected by ignored repo-local links, and paired with
one mutable project per game. Sharing analyzer binaries is never permission to
share project or target identity.

## Discovery and calls

`factory_list_analysis_providers` returns configured IDs but deliberately marks
availability `not-probed`. `factory_list_analysis_operations` returns bounded
operation pages and input schemas. Native IDA discovery performs one fresh
closed loop before exposing tools:

1. reload the repository adapter and resolve exactly one registered target;
2. hash the private executable and compare SHA-256, MD5, and size;
3. parse the private PE and compare declared image base, image size, entry point,
   and `.text` extent;
4. start the shared `ida-pro-mcp` stdio client and compare active IDA metadata;
5. confirm the active entry point and six deterministic distributed mapped
   `.text` byte samples; and
6. expose only tools actually advertised by that initialized session and
   selected by the Factory contract.

If another IDA database is open, the hash, layout, entry, or mapped-byte check
fails. The Factory does not guess which game was intended. Legacy IDA discovery
retains its bridge attestation. Native Ghidra discovery launches a read-only
`check`: the wrapper hashes its configured Ghidra/JDK surfaces and private EXE,
opens the registered per-game project, then verifies SHA-256, MD5, PE layout,
entry function, and six distributed mapped `.text` samples. The ten static
operation schemas are exposed only after that closed loop passes. Legacy Ghidra
discovery remains `not-probed` until a real bridge operation.

`factory_analysis_call` accepts a provider ID, one discovered operation name,
and a JSON object string containing only that operation's arguments. The JSON
envelope is used because IDA and Ghidra expose different evolving query schemas;
it avoids dozens of transport-level MCP tools while retaining operation-level
discovery and factory validation.

Factory validation remains closed-world but preserves useful analyzer autonomy:

- IDA operation names must be in the Factory's versioned atomic allowlist;
- native IDA exposes semantic reads plus comments, renames, prototypes, type
  declarations, and local/stack metadata edits;
- native IDA never exposes target-byte patching; metadata edits remain
  provisional analysis state and receive zero exactness credit;
- legacy IDA remains read-only until migrated;
- native Ghidra exposes ten bounded, read-only operations: check, decompile,
  function metadata, disassembly, callers, callees, both xref directions,
  paged function listing, and bounded string search;
- raw IDA memory reads are limited to 256 bytes per call;
- list counts, offsets, strings, arrays, nesting, addresses, Ghidra instruction
  counts, and xref/search limits are bounded;
- arguments cannot contain command, script, path, file, Python, or code
  authority fields;
- at most two different providers run concurrently, and one provider cannot
  receive overlapping factory requests;
- successful output is redacted for known Linux/Windows host paths and private
  provider endpoint components, then bounded to 256 KiB across text and
  structured content.

The upstream bridge may impose a smaller limit without returning a cryptographic
completeness statement. The factory therefore reports
`output_completeness = "upstream-not-attested"` even when its own
`factory_output_truncated` and `factory_structured_output_omitted` values are
false. Native Ghidra instead reports `factory-bounded-native-ghidra`: the
Factory owns the operation bound and output envelope, but the result is still
not proof of a complete authored extent. Do not infer completeness unless the
selected operation and independent boundary evidence justify it.

## Native Ghidra registration

`attested-ghidra-command-v1` uses a private command binding without creating
another MCP server:

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

The repo-local wrapper accepts only fixed subcommands and writes temporary query
output below ignored `.analysis/`; it does not accept shell source, arbitrary
scripts, or caller-selected paths. For each discovery or call, the Factory
independently hashes and parses the registered PE, then requires the same
headless process to emit an exact attestation marker after verifying the Ghidra
program and distributed mapped bytes. Requested semantic output is returned
only when those observations agree. The live registration pins the complete
reviewed wrapper/config/Java-script file set, not merely the command path; a
repository edit therefore makes the provider unavailable until an operator
reviews it and deliberately refreshes the aggregate implementation binding.
`scripts/render-native-ghidra-registration.py` produces the complete reviewed
file list and digest for this private block; it prints to stdout and never edits
service configuration.

## Relationship to repository work

Analysis state is not granted authority merely because GPT-web also has broad
repository Bash. A normal Web iteration composes both surfaces:

1. inspect an attested target with atomic analysis operations, optionally
   improving native IDA metadata as hypotheses become clearer;
2. inspect the selected live repository, including its current dirty and ignored
   state;
3. edit source and run repository-native build, Wine, comparison, and diagnostic
   scripts through composable Bash;
4. inspect the diff and create a coherent local `gpt-web:` Git checkpoint;
5. submit a supported factory replay for a committed claim;
6. query the acceptance registry for current verified facts.

The provider envelope makes the selected target and provisional authority
machine-visible. Repository Bash may use whatever native files and tools the
game intentionally exposes, but its output and its commits still receive zero
exactness credit. An analysis database edit or successful build cannot silently
become Truth Kernel state.
