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

Three contracts are supported during migration:

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

The private single-operator configuration staged for the next activation
registers:

| Provider | Repository | Backend | Target scope |
| --- | --- | --- | --- |
| `th04-ghidra` | `th04` | attested headless Ghidra | `target:th04-main` |
| `th08-ida` | `th08` | attested IDA Pro | `target:th08-main` |
| `th09-ida` | `th09` | Factory-native IDA Pro | `target:th09-main` |
| `th095-ghidra` | `th095` | attested headless Ghidra | `target:th095-main` |
| `th105-ida` | `th105` | attested IDA Pro | `target:th105-main` |

The already-running public process intentionally remains on its pre-TH09 code
and configuration while the TH095 Web campaign is active. TH09 must not be
reported publicly available until a deliberate restart and public validation.

This is operator configuration, not a cross-game claim that one backend is
universally correct. A provider can be absent, offline, busy, or correctly fail
attestation; the result is unavailable/unknown rather than fallback to a
different target.

The checked TH04 and TH095 deployments currently select Ghidra 12.1.3 and
JDK 21.0.12.1+1 from separate repo-local directories; their Ghidra `bom.json`
files have the same SHA-256. They run one bridge service per project. A future migration may
deduplicate that payload into one immutable Factory tool installation and let a
broker select the registered game/project. Project state, request serialization,
and target attestation must remain per-game. Sharing Ghidra's executable is not
permission to share a Ghidra project or analysis identity.

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
retains its bridge attestation. Ghidra operation schemas remain static and
`not-probed` until a real operation performs that compatibility bridge's
toolchain/project/target checks.

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
false. Do not infer a complete function or reference set unless the selected
operation itself supplies adequate pagination or extent evidence.

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
