# TH09 and TH095 overnight GPT-web pilot

## Scope and evidence boundary

This report records the first simultaneous overnight use of a fresh
Factory-native exact reconstruction and an established semantic reconstruction.
The observation window is 2026-09-11 00:00 through 10:03 Singapore time
(2026-09-10 16:00 through 2026-09-11 02:03 UTC). Counts come from durable
Factory repository-command records and local Git history, not chat summaries.

The report distinguishes successful infrastructure operation, expected
negative compiler/Oracle feedback, Git checkpoints, and Truth Kernel
acceptance. It does not infer correctness from command or commit volume.

| Measure | TH09 exact campaign | TH095 semantic campaign |
|---|---:|---:|
| Durable repository commands | 584 | 637 |
| Zero-exit commands | 561 | 597 |
| Nonzero commands | 23 | 40 |
| Timed-out commands | 0 | 2 |
| Factory infrastructure errors | 0 | 0 |
| `gpt-web:` commits | 36 | 53 |
| Period-wide changed-file summary | 56 files, +4,379/-161 | 33 files, +5,332/-415 |

The same MCP and worker instance ran without interruption from 01:08 until the
planned maintenance stop after the Web sessions ended. Command failures
persisted their diagnostic state as designed, and both repositories retained a
coherent uncommitted next batch at shutdown rather than losing work.

## TH09 result

TH09 began as the first repository bootstrapped directly against the shared
Factory MCP and Factory-native IDA provider. The period contains 36 Web
checkpoints plus three operator bootstrap/provider corrections. Its committed
head contains 45 target-bound exact functions covering 4,469 bytes. The
preserved dirty batch adds `Supervisor::TickTimer @ 0x0042F4F0`, bringing the
reviewed live ledgers to 46 functions and 4,540 bytes; it is not described as a
commit or accepted receipt until checkpointed and replayed.

The campaign repeatedly compiled VC7.1 i386 COFF units and replayed reviewed
relocations into the original executable extent. It kept unresolved LZSS
origins at `unknown/review`, and kept a 570/571-byte `Lzss::Encode` candidate
source-present but non-exact. These negative decisions are stronger evidence of
the accuracy policy than a raw completion count: plausible source did not
silently become truth.

The native IDA bridge passed target attestation and bounded reads after the
WSL-local original executable was staged. Before this release the Factory
imported the exact claims but had no TH09 replay driver, so the Truth Kernel
correctly contained no TH09 accepted exact fact. Release 0.6.0 adds that missing
driver; a direct cold replay against the live target passed with complete
claimed-byte coverage before deployment. The strict live policy now admits this
driver after the same receipt integrity, source freshness, target, toolchain,
coldness, and coverage checks used by the other exact drivers. This policy and
runner change intentionally creates a new freshness epoch for older receipts.

## TH095 result

TH095 created 53 semantic checkpoints while holding the canonical exact
baseline at 696 functions and 336,486 bytes. The campaign repeatedly preserved
the independent 88-translation-unit VC7.1 i386 compile/link lane. All 53
semantic commits updated the durable semantic record, so later sessions can
recover the evidence, limitations, and named next batch from Git rather than
conversation state.

Three durable whole-build jobs ran after semantic milestones. Each completed on
its first attempt, produced a `pass` receipt, and was accepted under the live
policy at the source state it checked. The jobs ran at 20:18-20:21, 23:13-23:15,
and 00:21-00:23 UTC. Later source changes correctly made earlier receipts stale;
strict freshness returning no currently accepted whole-build fact for the dirty
tree is conservative behavior, not evidence loss.

The preserved dirty SEM-060 batch recovers the compact enemy ECL subroutine
slot table. Its recorded focused lane passes 22/22 exact units with no private-
label ledger refresh, and its historical-platform lane compiles and links all
88 production translation units. The campaign-wide 696-unit replay remains
deliberately deferred to a committed milestone.

The untracked `config/runtime-scenarios.json` and `scripts/runtime-diff.py`
remain experimental inputs. They have no Factory runtime receipt and do not
prove deterministic behavior, original/reconstructed equivalence, or runtime
scenario closure. Release 0.6.0 therefore leaves TH095 runtime validation
`unknown` rather than promoting those files.

## Failures that improved the Factory

The two TH095 timeouts came from broad recursive searches entering ignored Wine
state and following `dosdevices/z:` toward the host filesystem. They were not
MCP, worker, repository-lock, compiler, or analyzer failures. Factory guidance
now starts with Git-aware tracked searches and bounded `rg` exclusions, while
retaining unrestricted composable Bash and allowing explicit searches inside a
named ignored evidence path.

The native IDA schema adapter fix was already committed during the pilot but
could not affect the long-running process. The maintenance restart activates it
along with the TH09 replay driver and the updated standalone prompts/plugin.
The TH09 prompt also now prevents count-maximizing selection drift: after at
most two packets chosen mainly for low size/risk, the campaign must attempt a
larger, central, complex, data-owner, or previously blocked frontier. An honest
non-exact or unknown result satisfies that exploration requirement; false
promotion never does.

## Post-pilot conversation-duration correction

Continued TH09 and TH095 use exposed a client-side failure not visible in the
service counts above: a productive campaign can make one GPT-web browser
conversation too large to remain responsive. The earlier semantic instruction
to keep working in the same conversation and the TH09 fixed “at most two easy
packets” scheduler both confused campaign persistence with chat duration.

The replacement keeps the useful pressure—TH04/TH09 pursue a moving 99.5%
reviewed authored-function and authored-byte target while continuing boundary
discovery, and TH095 remains `active-incomplete`—but lets Web decide how much
coherent work fits in the current conversation. It checkpoints and hands off
before client or context reliability degrades. A negative search alone cannot
justify an immediate handoff, and a handoff cannot imply phase completion.

The operator currently uses a separate browser userscript to submit later
conversations. That mechanism is intentionally not named in the agent prompt or
workflow ontology. Repository Git state, evidence, and the handoff are the only
continuation interface the model needs. This separation keeps the Factory
portable and prevents the reconstruction agent from spending attention on a
personal orchestration implementation.

## Storage and recovery state

TH09 `.analysis/` was 17,436,939 bytes. TH095 `.analysis/` was 1,408,444,500
bytes and unchanged by the latest semantic batch; most of that is pre-existing
legacy Wine/GDB state. No bulk cleanup is justified by this pilot.

At shutdown, neither dirty tree was normalized or discarded:

- TH09 retained the nine-path exact `Supervisor::TickTimer` batch.
- TH095 retained the two-path SEM-060 batch plus four untracked paths:
  `EnemyManagerUpdate.i`, `config/runtime-scenarios.json`, `droid.resume.txt`,
  and `scripts/runtime-diff.py`.

Every next Web session must review these paths first. The coherent batches may
be completed and checkpointed; unknown or unrelated files remain preserved.

## Assessment

The autonomy and persistence model met the pilot goal: two Web agents produced
89 reviewable checkpoints and 1,221 durable commands without an infrastructure
error, while exact, build, runtime, and accepted-fact states stayed separate.
The remaining gaps are substantive rather than transport-related: checkpoint
and replay the two preserved batches, establish a durable TH095 runtime Oracle,
and continue closing TH09 exact and historical-platform product ownership.

## Release 0.6.0 maintenance result

The portable release gate passed 152 tests, Ruff, bytecode compilation, Git
whitespace checks, 39 JSON documents, two TOML documents, two evaluation XML
documents, three CLI construction probes, and an isolated 0.6.0 wheel build.
The two changed bundled skills passed their validator. The plugin cachebuster is
`0.6.0+codex.20260911021613`; the older local plugin validator retains its known
stale-schema objection to the official `.app.json` `required` field.

The worker and MCP restarted in place behind the unchanged operator-private
route. Read-only live validation returned 33 tools, all five repositories, 76
older policy/runner-stale receipts rejected, and zero invalid receipts. TH04 and
TH095 Ghidra plus the active TH09 native IDA provider passed target attestation.
All 47 advertised TH09 IDA operations carried a real input schema. TH08 and
TH105 IDA accurately reported unavailable because the single active Windows IDA
database was TH09; the validator now distinguishes this expected target state
from a provider failure.

A public MCP submission for the existing TH09 exact claim at `0x00401340`
completed as job `job:068b629593934851ba515422222f3d97`. Receipt
`receipt:2090a0819180d51f6ef1bc13b6ae1ad1d331cd0ec326b158af308971c1a85396`
reported `pass`, the strict registry decision was `accepted`, and the current
accepted-facts query returned exactly that claim/receipt pair. This closes the
previous TH09 import-only gap without granting product, runtime, or historical-
fixture credit.
