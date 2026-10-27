---
name: factory-analysis
description: Use repository-selected IDA or Ghidra for autonomous source investigation, with Bash and read-only references to all registered repositories. Analysis never grants exactness credit.
---

# Factory Analysis

1. Select a repository/provider from `factory_list_repositories` and
   `factory_list_analysis_providers`.
2. Discover operation arguments with `factory_list_analysis_operations`, then
   call `factory_analysis_call` for a useful bounded query. Ghidra discovery
   does not start the analyzer.
   For native Ghidra function investigation, `function_context` returns
   metadata, callers, callees and decompilation in a single analyzer launch.
   An instruction address inside a defined function is sufficient for native
   Ghidra decompilation; the returned header identifies its actual entry.
3. Confirm the returned repository/target and read the actual verification
   scope. Ghidra exploratory calls report `not-checked`; native IDA checks
   database metadata only. Neither is complete target verification.
   Native Ghidra previews default to 8,000 characters; `max_output_chars` can
   increase the preview. Read `output.artifact_path` with repository Bash for
   the complete result, using `next_line` or function start/end lines to select
   a range. Reading another page does not require another Ghidra call.
   Native IDA uses the same text preview budget. Oversized IDA returns also
   provide `structured_artifact_path` for the complete JSON representation.
   Ghidra errors provide a complete diagnostics log and preserve partial text.
4. Treat names, extents, types, xrefs and decompilation as hypotheses with
   `exactness_credit=none`. Preserve useful errors and truncation information.
5. Compose repository Bash and searches under `/references/<id>` freely.
   Every other registered repository is mounted read-only automatically.
6. Native IDA metadata edits are available when advertised. Read important
   edits back and record durable conclusions in source or local notes.
7. Run affected compiler/comparison/Oracle commands when needed. Full
   environment scans, implementation pin refreshes and complete replay are not
   prerequisites for exploration. Only explicitly accepted receipts establish
   exactness.
