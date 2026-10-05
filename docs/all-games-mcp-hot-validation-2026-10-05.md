# Recorded all-game MCP hot validation, 2026-10-05

This checkpoint audits the seven registered games through the actual Factory
MCP client. Game-functional tests use MCP, including Python, script checks,
analysis and exact replay submission/polling. Local commands inspect and repair
Factory code, run internal tests and manage the authorized hot deployment.
Full transcripts, endpoints and operator configuration remain ignored/private.
These measurements are dated evidence, not live availability or whole-game
exactness claims.

## Reproduced problems and repairs

TH09's native IDA and the legacy TH08/TH105 bridges rejected integer addresses
and whitespace around uppercase `0X` hex strings. IDA now shares bounded address
normalization with Ghidra: unsigned integers, decimal strings and trimmed hex
strings work. Discovery advertises the additional forms while retaining each
operation's actual parameter names and required fields. Invalid values report
accepted formats, allowing Web to correct and retry.

The legacy TH08 and TH105 bridges were connected to another game's active IDA
database. Their target checks correctly failed. Both registrations now use the
maintained `scripts/ida-headless-stdio.py` helper with separate operator-bound
IDAlib databases and private input copies. Canonical hashes, PE layout, entry
point and six mapped-byte samples remain independently attested by Factory.
No shared GUI RPC port or IDA GUI is used. Database files, user configuration
and caches are game-specific; a file lock coordinates hot service instances.
TH09's existing working stdio binding remains unchanged.

The installed Python 3.11 protocol annotations also prevented the initial
IDAlib stdio startup. The helper translates the installed protocol's TypedDict
schemas without modifying shared analyzer packages. Async tool wrappers run on
the IDAlib initialization thread. Metadata writes are saved before responding;
two fresh-session rename/read/restore/read tests passed on the new TH08 and
TH105 databases. Original names were restored. Native startup errors now carry
bounded, redacted provider diagnostics and corrective repository/provider
context instead of only an ExceptionGroup label.

Actual exact-replay submission exposed a separate hot-deployment defect: the
public configuration included TH03 while the original worker retained its six
registered games. Their global replay configuration fingerprints differed, so
the worker rejected new jobs for existing games before compilation.

The new MCP supports an explicit `--replay-config` worker binding. It reloads
both configurations per submission, requires identical replay policy, storage
and execution settings, and compares the selected game's source/target
registration. Compatible submissions retain the worker's original fingerprint.
`factory_describe.replay_submission` reports that effective fingerprint and
registered games. A game absent from the worker receives corrective feedback
before queuing; its shell and analysis remain available. Worker checks, driver
and runner fingerprints, target attestation and Oracle acceptance were retained.

## MCP evidence

The final public analysis audit passed 37 calls over TH03, TH04, TH08, TH09,
TH095, TH10 and TH105. It covered operation discovery, integer and formatted
address queries, all three IDA providers' decimal addresses, function paging
and memory reads, plus malformed-address feedback for every provider. Analyses
ran concurrently across games. Successful responses retained passed target
attestation and zero exactness credit.

Another 15 public calls verified Python and syntax compilation of the exposed
Python scripts in all seven repositories, useful nonzero stderr/exit feedback,
recovery, and exact replay submission/results for three existing games. Each
read-only shell probe preserved its own before/after HEAD and worktree digest.
Active Web work was allowed to advance normally between probes.

The three native cold replay jobs completed on the unchanged original worker:

| Game | Claim function | Unit | Scoped bytes | Source checkpoint |
| --- | --- | --- | --- | --- |
| TH09 | `0x00401510` | `zun-timer-post-increment` | 8 | `d67b33da` |
| TH10 | `0x00401f60` | `game-decomphelp-fulltu-00401f60` | 8 | `466804f8` |
| TH105 | `0x004065a0` | `gpt-web-strict-fp-math-primitives` | 8 | `8ce81618` |

Every job reported `coldness=forced-recompile`, `receipt_verdict=pass`, and
`acceptance_decision=accepted`. The public endpoint subsequently resubmitted
the same idempotency keys, reused those jobs and retrieved their accepted
results. These are three scoped function checks, not complete-game proofs.
TH03 still uses its separately validated repository-shell exact Oracle and
does not acquire a native Truth Kernel driver from this deployment.

A final 48-call public isolation test held a harmless TH03 Python command for
eight seconds and queued 42 TH03 status requests. Independent Python commands
returned in 1.302 seconds for TH08, 1.298 for TH10 and 1.297 for TH105; repository
discovery returned in 1.287 seconds. Every queued status request completed.
Same-game writer feedback remains a valid retry condition; it does not consume
another game's queue or authorize a fallback to another target.

TH03's README credit update also passed its maintained CI script through the
public repository-shell MCP in 63.683 seconds, followed by successful GitHub CI
for the published `b326e05` checkpoint.

## Deployment and release checks

Two new shared MCP candidates were tested before changing only the upstream of
the existing public route. The second includes the explicit original-worker
binding. All 33 top-level MCP tool definitions remained identical. The ten
original service PIDs stayed unchanged across both switches; the first newly
exposed service also stayed alive during the second switch. No old service or
worker was restarted, no active job was cancelled, and no original watched
configuration or analyzer installation was rewritten.

The Factory release check passed 176 tests, Ruff, bytecode compilation,
whitespace/document checks, CLI help and isolated wheel packaging. Added
regressions cover address normalization and discovery, IDAlib thread/schema
handling, compatible hot replay submissions and rejection of changed authority.
Changes remain outside the replay runner's implementation fingerprint closure.
