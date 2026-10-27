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
accept trimmed hexadecimal/decimal strings and unsigned integers; native MZ
also accepts `segment:offset`. Keep requests bounded and page larger results.
`check` only opens the selected project; it is not a complete verification.

All registered repositories are available read-only at `/references/<id>` from
any selected repository shell. Use Bash freely to connect source, history and
analysis. Neighboring code is a useful hypothesis, not proof about this target.

Run repository-native compiler/comparison/Oracle commands when the work needs
them, scoped to changed units. Explicit exact replay and receipt acceptance
remain separate. Ordinary browsing, discovery and decompilation do not trigger
whole-project verification. Historical stronger attestation procedures are
preserved in dated records and Git history, not imposed on exploratory calls.
