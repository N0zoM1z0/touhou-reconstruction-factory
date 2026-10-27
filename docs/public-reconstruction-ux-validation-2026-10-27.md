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

## Additional reconstruction exercise

A second public round exercised concurrent work, oversized output, native DOS
compilation and a real large IDA function. It reused the endpoint and bypassed
MagicDNS/proxies with both freshly resolved public relay addresses.

| Additional finding | Repair and observed regression |
| --- | --- |
| Reading an earlier completed log waited behind a new eight-second writer | Completed capture reads bypass the worktree queue/lock. Public latency fell from 7.80 to 0.75 seconds, while the writer was still active. Reads of active captures fail promptly with retry guidance; orphan-record recovery remains available. |
| TH105 function `0x00620920` returned 489,975 text bytes, but only 262,144 were delivered and the rest could not be recovered | Native IDA now defaults to the existing 8,000-character preview model and retains complete oversized text and JSON. The measured response frame fell from 542,127 to 23,119 bytes. Public Bash recovered all 7,185 lines, verified the old prefix unchanged, and checked that full JSON and text agreed. |
| A mixed valid/invalid Ghidra batch returned a long stack tail which omitted the useful error | Return a short error summary, retain full `provider.log`, and preserve partial query files. Public readback recovered the valid address's output and complete diagnostics; the next query to that provider succeeded. |
| A normal 4-KiB IDA memory read was rejected by the old 256-byte cap | Allow up to 65,536 bytes and advertise the limit. A public 64-KiB read was recovered from its retained result and compared byte-for-byte with the corresponding canonical TH09 PE range. A second-relay 4-KiB read also passed. |
| TH08 agent instructions still blocked all IDA work on a GUI database switch | Game-local documentation now distinguishes the headless `th08-ida` provider from the legacy GUI bridge. Public decompilation, metadata previews and compilation passed; documentation checkpoint `049a4a26` remains local. |

Additional public compiler checks produced valid objects from maintained source
in TH03, TH04, TH075, TH08 and TH105. TH03's isolated stage needed its normal
`compat/rec98` adapters and ReC98 header tree; adding those dependencies resolved
ordinary compiler diagnostics without changing source. TH05 replayed only the
existing 30-byte `main-player-angle` unit, with two isolated positive producers
and a compiled negative mutation. It passed and reused the existing toolchain
attestation; no acceptance ledger or Factory accepted fact was updated.

Long UTF-8 stdout and stderr were recovered over multiple pages without byte
loss. A separate 12,500,017-byte diagnostic stream exceeded the 8,388,608-byte
capture cap: truncation was explicit, the final captured page had correct byte
offsets, and the complete repository-local log remained readable. These checks
did not start a whole-game build or complete replay campaign.

One earlier public read request timed out before HTTP response headers. No
matching command execution record existed. The cause remains unknown; it was
not reproduced in twelve subsequent alternating relay checks, all of which
returned verified TLS/HTTP 200 responses in approximately 0.82–1.03 seconds.
This is not a claim that public transport cannot fail.

The second round passed 18 analysis, 9 repository-work, 10 MCP-server and
2 headless-IDA checks, plus `git diff --check`. The original replay worker and
replay implementation fingerprint remained unchanged. Game reconstruction
source and acceptance ledgers were preserved; only the TH08 documentation was
changed. Superseded candidate services were retired after becoming idle.
