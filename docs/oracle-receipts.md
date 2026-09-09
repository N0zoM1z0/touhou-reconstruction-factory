# Oracle receipts

An oracle receipt is the factory's durable statement about one replay of one
claim. Native project output is evidence inside the receipt; it is not itself a
factory verdict.

The envelope is intentionally shared by PC-98 MZ/OMF and Windows PE/COFF
projects. The comparator, toolchain surface, address space, relocation policy,
and cold-build mechanism remain provider- or driver-specific.

## Required bindings

Every receipt binds all of the following values:

- the complete normalized `Claim` and `Subject`, including every declared
  extent, by canonical SHA-256;
- the declared target identity and the size and SHA-256 of the target bytes
  actually observed immediately around the replay;
- the declared `ToolchainIdentity`, the environment variables that can select
  execution surfaces, and conservative hashes of the toolchain surfaces
  observed by the driver;
- the Git commit and tree plus a content digest of every tracked or
  non-ignored untracked file in the instance repository scope, both before and
  after execution;
- the driver version, defined by the exact checked-in native scripts and
  manifests that implement its build and comparison contract;
- every shell-free invocation stage, its declared input digest, exit status,
  duration, and complete stdout and stderr artifacts;
- structured native comparison evidence, explicit coverage, normalizations,
  and the final truth-kernel `OracleResult`.

The receipt ID is the SHA-256 of the canonical envelope with an empty
`receipt_id`. Any edit invalidates the ID. Evidence artifacts use their own
content addresses and may be deduplicated by a receipt store.

## Fail-closed verdicts

The result vocabulary remains exact:

- `pass`: the acceptance contract ran with complete declared coverage and all
  receipt invariants hold;
- `fail`: the oracle fully evaluated the claim and disproved it;
- `incomplete`: the available replay did not cover or attest enough to decide;
- `error`: the oracle contract could not execute reliably, including timeout,
  malformed output, source mutation during replay, or identity drift.

A zero process exit code is never sufficient for `pass`. In particular, an
incremental comparison, a target hash copied only from a manifest, a compiler
binary without its relevant headers and execution surface, or a report whose
address and size do not match the claim remains incomplete or erroneous.

Dirty source trees are not automatically rejected. Reconstruction work often
needs verification before commit. Instead, the runner hashes the exact live
source state and rejects any receipt whose state changes during execution. A
later consumer can therefore test freshness against the same source digest.

## Coldness vocabulary

`coldness` states how stale candidate output is excluded:

- `isolated-double-build`: two separately materialized builds agree;
- `clean-output-graph`: the native generated-output graph is cleaned before
  the selected target is rebuilt;
- `forced-recompile`: the compiler is unconditionally invoked and overwrites
  the selected candidate object;
- `incremental`: an existing artifact may have satisfied the request;
- `unknown`: the driver cannot prove how the candidate was produced.

Only the first three values can support an acceptance pass. They are not
claimed to be interchangeable: the precise mechanism remains visible in the
receipt.

## Native repository policy

Drivers are narrow translators, not compatibility promises. A project with a
weak native workflow is allowed to produce only `incomplete` receipts until
its build or comparator is strengthened. The factory must not parse arbitrary
ledger command strings, execute user-provided shell fragments, infer extent
coverage from names, or reinterpret a native diagnostic as acceptance.

The normative machine shape is
[`schemas/v1/oracle-receipt.schema.json`](../schemas/v1/oracle-receipt.schema.json).
