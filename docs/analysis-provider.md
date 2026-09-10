# Attested Analysis Provider

## Purpose and authority

The analysis provider gives GPT-web bounded semantic access to the target used
by a reconstruction repository without exposing a native IDA/Ghidra endpoint,
its host Bash tool, its local filesystem, or database mutation operations.

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
an ID, repository ID, target identity ID, backend, exact endpoint, one upstream
tool name, and timeout. Configuration accepts only exact loopback HTTP URLs.
Endpoints, ports, paths, and host files are omitted from public responses.

Two bridge contracts are supported:

- `attested-ida-proxy-v1` calls only upstream `ida_call`;
- `attested-ghidra-proxy-v1` calls only upstream `ghidra_call`.

The legacy bridges may also implement `run_command`, but the factory never
names or forwards that tool. The public MCP therefore cannot cross from an
analysis request into legacy host Bash.

The live single-operator configuration currently registers:

| Provider | Repository | Backend | Target scope |
| --- | --- | --- | --- |
| `th04-ghidra` | `th04` | attested headless Ghidra | `target:th04-main` |
| `th08-ida` | `th08` | attested IDA Pro | `target:th08-main` |
| `th095-ghidra` | `th095` | attested headless Ghidra | `target:th095-main` |
| `th105-ida` | `th105` | attested IDA Pro | `target:th105-main` |

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
operation pages and input schemas. IDA operation discovery also invokes the
registered bridge attestation and independently compares active IDA SHA-256,
MD5, and file size with the factory adapter's current target identity. Ghidra
operation schemas are fixed by the provider contract and remain `not-probed`
until a real operation performs the bridge's toolchain/project/target checks.

`factory_analysis_call` accepts a provider ID, one discovered operation name,
and a JSON object string containing only that operation's arguments. The JSON
envelope is used because IDA and Ghidra expose different evolving query schemas;
it avoids dozens of transport-level MCP tools while retaining operation-level
discovery and factory validation.

Factory validation remains closed-world:

- IDA operation names must be in the factory's versioned read allowlist;
- all rename, create, delete, set, declare, patch, and other database mutation
  tools are absent;
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

1. inspect an attested target with read-only analysis operations;
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
