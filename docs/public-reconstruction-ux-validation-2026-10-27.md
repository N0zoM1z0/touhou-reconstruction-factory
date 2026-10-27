# Public reconstruction workflow exercise, 2026-10-27

This is a dated observation, not a live readiness guarantee or exactness receipt.
The exercise used the shared public Factory MCP through two public relay IPv4
addresses, with `curl --noproxy '*' --resolve`, normal TLS/SNI verification,
HTTP 200, and the expected remote IP. No MCP probe used MagicDNS or an operator
HTTP proxy. Endpoints, command logs and private artifacts remain ignored.

## Exercised workflows

- All 13 registered repositories supplied source, instructions, Python entry
  points and command output through public repository Bash.
- Every selected repository read actual source from all 12 neighboring
  repositories: 156 directed reference checks, including read-only access.
- An initial 110 public analysis calls covered all 16 providers. Ghidra queries
  exercised function discovery, metadata, instructions, callers, callees,
  references, decompilation and string search where functions exist.
- Final native Ghidra regression exercised `function_context` on all 12
  providers with defined functions. TH05's selected loader-only project returned
  an empty function list; it was not counted as decompilation-ready.
- All three IDA providers completed public decompilation and disassembly after
  the headless fix, including addresses copied from the GUI without `0x`.
- Maintained translation units compiled to isolated ignored outputs in TH07,
  TH09, TH095, TH10, TH11 and TH20, using their existing compiler profiles.
- A TH11 scratch source deliberately failed compilation; its diagnostics were
  recovered by command ID, then the source was corrected and recompiled.
- A forced public disconnect lost the original response. Repository status
  recovered its command ID and the completed output without rerunning the work.
  An explicit shell timeout also preserved its scratch file and allowed a new
  command. One-byte and seven-byte pages recovered complete Chinese/emoji text.

## Repairs and measured changes

| Friction reproduced | Change and evidence |
| --- | --- |
| `00415e90` was rejected; `00401000` silently meant decimal | IDA/Ghidra normalize A-F hex and zero-padded 8/16-digit display addresses. Other numeric strings retain decimal meaning. Public regression included interior addresses and a padded 64-bit representation. |
| IDA decompilation tried to import PySide6 | Disable the upstream active-window probe inside the headless IDAlib process. All three providers then decompiled successfully; no GUI dependency was installed. |
| Four related Ghidra queries required four startups | `function_context` reuses existing Java scripts in one read-only launch. TH10 measured 32.92 seconds separately versus 8.16 seconds combined; all four complete component files were byte-identical. The existing preview/artifact mechanism bounds inline context. |
| A provider timeout killed its wrapper but left its child alive | Terminate the native Ghidra process group. A focused subprocess fixture verifies that the child's project-style lock is released and partial output survives. Normal public Ghidra calls passed afterward. |
| A lost shell response hid its command ID | Status includes the five most recent command records, with IDs, timing and last recorded state. A real public client timeout recovered its output through this path. |
| UTF-8 pages switched to base64 at split characters | Finish the final code point with at most three extra bytes; offsets remain byte-based. Genuine invalid/binary bytes retain the lossless base64 fallback. |
| TH06 `build.py --help` started a cold build | Parse arguments before tools run. Help and unknown-option requests now return without building. Game-local fix: `4e25087`. |
| TH11 Wine aborted with `TMPDIR` set in the sandbox | Remove that override and the unnecessary Xvfb dependency, clear display variables, and disable menu helpers. Repeated native compilation and error recovery passed; executable COFF sections and relocations matched the earlier local build. Game-local fix: `0b8d2dd`. |

The initial TH06 help probe unexpectedly replaced four ignored objects before
timeout. Their unchanged source inputs were checked, the old linked image and
receipts were backed up, the build record was reconciled to the actual objects,
and isolated then canonical relinks completed. The entire 430,080-byte `.text`
section matched the pre-exercise linked image byte for byte. This recovery did
not edit reconstruction source or acceptance ledgers and grants no new exactness.

TH05's existing bounded range script also decoded a complete 30-byte MZ range
through public Bash, read-only and with automatic analysis disabled. Empty
function discovery is a real project state: full decompilation still needs
function definitions. Neither the empty loader project nor the alternate empty
project was silently reanalyzed or promoted as ready.

## Scope and retained state

The shared endpoint and original replay worker were retained. The replay
implementation fingerprint was unchanged. Superseded candidates created during
this work were retired only after their process groups were idle. Pre-existing
TH095 untracked work was preserved. TH08 web/mods remain unregistered.

Focused checks passed: 17 analysis tests, 8 repository-work tests, 2 headless
IDA tests and 10 MCP-server tests, plus `git diff --check`. No whole-game build,
full exact replay campaign, release-wide validation, implementation hash refresh,
or new acceptance claim was used as a prerequisite for ordinary exploration.
The TH06 recovery required two links of existing objects, not a full rebuild.
