---
name: factory-analysis
description: Query target-attested IDA or Ghidra semantic analysis through the Touhou Reconstruction Factory. Use when the user asks GPT-web to decompile, disassemble, inspect functions, callers, callees, xrefs, strings, globals, structures, or target metadata for a registered reconstruction. Do not treat analysis output as exactness evidence or request database writes.
---

# Factory Analysis

Use semantic analysis to form source hypotheses. Every result has zero exactness
credit until a separate canonical replay receipt is accepted.

## Analyze

1. Call `factory_list_repositories`, then
   `factory_list_analysis_providers` with the selected repository ID. Use only a
   returned provider; `availability="not-probed"` is not a success claim.
2. Call `factory_list_analysis_operations` with a narrow filter. Use the
   returned operation name and `input_schema`; do not invent an upstream native
   tool or argument.
3. Call `factory_analysis_call`. Encode the operation arguments as one JSON
   object string. Keep addresses, result counts, instruction counts, and search
   scope narrow.
4. Require a successful attestation in the response. Confirm the returned
   target identity, SHA-256/size where present, provider binding, operation, and
   argument digest before using the content.
5. Treat names, function boundaries, tails, EH regions, types, xrefs,
   decompilation, and disassembly as provisional evidence. Preserve
   `output_completeness`, `factory_output_truncated`,
   `factory_structured_output_omitted`, and any provider error.
6. Correlate the result with current source through the live-repository workflow
   in `factory-reconstruction`. Do not claim that analysis changed source or
   that repository tests changed the analysis database.
7. If exactness is requested, switch to `factory-replay` only after the source
   state is committed and a matching claim is discoverable.
   If no supported receipt covers the requested extent, report `unknown`.

Do not seek native database mutation or bridge Bash through the analysis tool;
they are outside its target-attested read surface. This does not restrict
Python, file access, or Bash inside the separately registered game repository.

## TH105 example

Select `th105-ida`, discover `get_function_by_address`,
`decompile_function`, or `get_xrefs_to`, and use an address such as
`0x00401000` only when it is relevant to the requested work. Confirm that the
active metadata matches `target:th105-main` before interpreting output. The IDA
candidate at that address and its decompilation do not prove the known 52-byte
standalone code-generation claim; only its accepted replay receipt does.
