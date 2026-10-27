# Repository analysis

Factory provides a selected repository's IDA or Ghidra alongside composable
Bash. Analysis is exploratory: every result has
`authority=provisional-semantic-analysis` and `exactness_credit=none`.

Use `factory_list_repositories`, `factory_list_analysis_providers`, and
`factory_list_analysis_operations` to find the current repository, provider and
argument schema, then call `factory_analysis_call`. Choose a useful bounded
query directly; a full environment check is not a prerequisite.

Ghidra operation discovery returns schemas with `attestation_state=not-probed`
and does not launch Ghidra. Calls open the selected existing project read-only,
with analysis disabled, and execute its existing query/decompiler scripts.
There is no complete tool-installation scan, implementation hash gate, target
replay, database dump or distributed-byte preflight. Results explicitly report
`attestation.status=not-checked`; this is not a full attestation claim.

Native IDA uses one selected headless database and compares its metadata to the
repository target manifest. It does not rehash the executable or issue entry
point and distributed-memory checks before every query. Its verification scope
is `database-metadata-only`. Metadata edits such as names, comments and types
remain available on providers that advertise them.

Native IDA also accepts `max_output_chars` in operation arguments, with an
8,000-character default and 65,536-character maximum. Small results retain their
structured representation. Oversized results retain complete text at
`output.artifact_path` and complete JSON at `output.structured_artifact_path`;
the inline structured representation is omitted when it would defeat the
preview budget. Read these files with repository Bash instead of rerunning a
large decompilation. These are the complete upstream returns, not additional
exactness or upstream-completeness claims.
`read_memory_bytes` accepts up to 65,536 bytes per call; its former 256-byte
restriction is unnecessary with retained output. Large hex dumps stay in the
same bounded preview/file flow.

Analysis target descriptions come from the small target manifest, without
loading or validating complete function, origin, source or acceptance ledgers.
An incomplete reconstruction ledger must not prevent the agent from using
analysis to repair it.

Private registrations contain the provider/repository IDs, target ID, launch
command and arguments, target path, and timeout. Historical
`implementation_files` and `implementation_sha256` fields are accepted but
ignored. Editing or retiring a helper does not require a new hash binding.
A missing executable or failing query produces an ordinary operation error;
registration does not run a readiness campaign.

The existing backend names (`attested-ghidra-command-v1`,
`attested-ida-stdio-v1`, and legacy loopback proxy variants) remain compatible
identifiers. Read the reported verification scope rather than inferring it
from the historical name. All games use one public Factory MCP; analyzer
installations can be shared while projects and writable state remain per game.

The Ghidra operations are `check`, `function`, `decompile`, `disassemble`,
`callers`, `callees`, `xrefs_to`, `xrefs_from`, `list_functions`, and
`search_strings`. Discovery describes their actual fields. Address arguments
accept trimmed hexadecimal/decimal strings and unsigned integers. Hex strings
can use `0x`, A-F digits, or zero-padded 8/16-digit display addresses; other
numeric strings are decimal. Native MZ
also accepts `segment:offset`. Keep requests bounded and page larger results.
`check` only opens the selected project; it is not a complete verification.
Native Ghidra also offers `function_context` with the same address arguments:
function metadata, callers, callees and decompilation run in one process.
Use it when investigating a function instead of paying startup cost four times.
Native `decompile` and `function_context` also accept instruction addresses
inside an existing function. A small Factory script resolves the containing
function before calling the repository's decompiler; output names its entry.
This does not create functions or run automatic project analysis.
The operator may select a different existing project with `--project-name`;
no implementation fingerprint needs refreshing.

Native Ghidra returns an 8,000-character text preview by default. Pass
`max_output_chars` in the operation arguments to request up to 65,536 characters.
This bounds the preview, not the complete MCP frame or a tokenizer's token count;
MCP clients may receive both text and structured representations.

Every successful query retains its complete output at the returned repository-relative
`output.artifact_path`. Truncated previews report `next_line`, total lines and
characters; large decompilation batches also list function names, addresses and
start/end lines, including functions outside the preview. Read a desired range
with existing repository Bash, for example `sed -n '200,260p' <artifact_path>`.
Do not rerun Ghidra just to read the next page. `factory_output_truncated` refers
to the inline preview; the retained file is complete. Failed queries that wrote
partial output report its retained path in the error. These ignored analysis
files may be retired when no longer needed, like other game-local diagnostics.
Ghidra failures return a short error summary and retain the complete process
diagnostics at a reported `provider.log` path alongside any partial query text.
Timeouts stop the wrapper and its analyzer subprocesses together, releasing the
project lock. Any already-written partial files are retained and reported.

This takes the useful parts of REA's
[recoverable result delivery](https://github.com/morluto/rea/blob/92213a91557a8ea378757a97ac0a1a34b94332ef/src/server/ToolResultDelivery.ts)
and [accounting for repeated MCP representations](https://github.com/morluto/rea/blob/92213a91557a8ea378757a97ac0a1a34b94332ef/src/server/toolResultEncoding.ts),
using existing files and Bash rather than introducing an evidence/cache service.

All registered repositories are available read-only at `/references/<id>` from
any selected repository shell. Use Bash freely to connect source, history and
analysis. Neighboring code is a useful hypothesis, not proof about this target.

Run repository-native compiler/comparison/Oracle commands when the work needs
them, scoped to changed units. Explicit exact replay and receipt acceptance
remain separate. Ordinary browsing, discovery and decompilation do not trigger
whole-project verification. Historical stronger attestation procedures are
preserved in dated records and Git history, not imposed on exploratory calls.
