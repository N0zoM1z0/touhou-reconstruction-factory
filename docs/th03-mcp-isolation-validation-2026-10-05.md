# Recorded TH03 MCP isolation and Oracle validation, 2026-10-05

This is a dated observation, not a declaration of current availability or
whole-game exactness. All game-functional checks in this audit called the
actual shared public Factory MCP through its MCP client. Local commands only
inspected or repaired Factory code, ran its internal release suite, and managed
the authorized hot deployment; they did not substitute for game tool calls.
Private endpoint configuration, transcripts and complete responses remain in
ignored operator state.

## Reproduced failures and repairs

The previous analysis gateway capped all games together at two providers.
Concurrent real TH04 and TH095 checks caused a TH03 check to fail immediately
with generic capacity feedback. Capacity is now independent per repository,
with two different providers per game and exclusive execution per provider.
Conflicting requests wait for up to 60 seconds, bounded by a shorter provider
timeout. Cancellation and exceptions release capacity. A queue timeout names
the repository and provider and gives retry guidance.

A second public MCP stress check put 42 TH04 status requests behind a harmless
12-second TH04 Python command. Synchronous file-lock waits occupied the shared
thread pool: an unrelated TH03 Python command took 9.498 seconds and repository
discovery took 9.426 seconds. Per-repository asynchronous MCP queues now precede
thread execution for shell, status, semantic-debt and output-page calls. File
locks remain in place for coordination with other services and replay workers.
The same public stress check after deployment returned the TH03 command in
0.168 seconds and discovery in 0.149 seconds while TH04 remained active.

Same-repository writer conflicts now identify the repository/provider and tell
Web when to retry. Repository command timeout validation reports its configured
numeric range. Broad Bash and Python execution, arbitrary local scripts,
repository-local compilers and ignored tool state remain available; no fixed
compiler or recovery task catalog was introduced. Target attestation and Oracle
acceptance rules were not relaxed.

## Public MCP coverage

The audit exercised discovery for seven repositories and TH03's four native
Ghidra providers, with all 33 public tool definitions identical across the hot
switches. Actual TH04, TH095 and TH03 analysis checks completed concurrently.
Two overlapping requests for the same TH03 provider both completed, in sequence.
An independent TH03 Python command returned in 0.185 seconds while a TH04
Python command ran for 12 seconds.

TH03 read the maintained TH04 math source through `/references/th04` from a
nested working directory. Append-open was denied and reference bytes remained
unchanged. Invalid addresses and unknown arguments returned accepted forms or
fields; corrected segmented and integer address calls both returned the real
26-byte polar function with passed attestation. Operation discovery and fresh
checks for MAIN, MAINL, OP and ZUN all passed.

Repository-shell feedback checks covered a Python exit code of 7, retained
stderr and an ignored file, recovery using that retained file, a real command
timeout with partial stdout, and a successful following command. A 40,000-byte
output was recovered exactly through three output pages.

The compiler and scoped exact Oracle check ran through
`factory_repository_run_shell`, with empty DISPLAY and WAYLAND_DISPLAY. It
attests the real Borland compiler/assembler/linker/DOS execution path, runs
adversarial exact-Oracle controls, and invokes the maintained TH03 driver for
two independent full cold source builds, owned-extent byte and relocation
comparison, MAP checks and DOS ABI/behavior probes. The reviewed local scope is
10 MAIN functions, 393 bytes; this is not a whole-game claim.

The complete public MCP audit passed 35 calls. Compiler/Oracle execution took
150.945 seconds and produced the TH03-local receipt
`.analysis/th03-main-exact/factory-mcp-final-20261005T062406/receipt.json`.
Its pass flag, two rounds, 393-byte scope, every function/owner's raw-byte and
relocation equality, identical products and game-object metadata-normalized
identity were checked inside the MCP command. TH03, TH04 and TH095 HEADs and
worktree status digests were unchanged across the audit.

During this exact Oracle command, an actual TH04 Python call returned in
0.228 seconds and discovery in 0.201 seconds. A TH03 analysis request returned
a same-repository writer conflict in 0.226 seconds, explicitly identifying
TH03 and its provider and instructing a retry. It did not occupy another game's
capacity.

## Deployment and authority boundary

Two new shared candidates were started on verified unused loopback ports.
Each was tested through MCP before its hot proxy switch; only the upstream of
the existing public route changed. No old MCP or replay worker was restarted,
no existing configuration or provider implementation binding was refreshed,
and no active job was cancelled. Prior process IDs remained unchanged.

The internal Factory release suite passed 170 tests, Ruff, bytecode compilation,
whitespace/document checks, CLI help and isolated wheel packaging. Regression
checks cover cross-game analysis isolation, same-provider waiting, cancellation
cleanup, and a repository backlog under an intentionally small thread pool.

These changes are outside the replay implementation fingerprint closure. Its
files remain unchanged, preserving existing worker and queued-job identities.
TH03 still has no native Truth Kernel replay driver: repository-shell exact
Oracle success is a scoped local receipt and does not publish Factory acceptance.
