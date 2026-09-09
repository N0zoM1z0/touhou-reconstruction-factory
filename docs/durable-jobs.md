# Durable Replay Jobs

## Purpose

The durable job layer lets a short-lived GPT-web request start a long native
replay without making the network connection, MCP process, or model context the
owner of that work. SQLite is the coordination record. The content-addressed
artifact store is the evidence record. The acceptance registry remains the only
promotion path into the Truth Kernel.

A job is workflow state, not evidence. In particular:

- `completed` means that replay execution produced a sealed receipt and the
  current registry classified it;
- `receipt_verdict = pass` means the replay oracle reported complete equality
  under its receipt bindings;
- `acceptance_decision = accepted` means integrity, freshness, and policy checks
  admitted that receipt;
- only accepted snapshots and accepted-fact queries expose the result as trusted
  factory knowledge.

These statements are deliberately separate. A completed job may correctly
contain a failing, incomplete, or rejected result.

## State machine

```text
queued --claim--> leased --start--> running --receipt/classify--> completed
   |                  |                |
   +--cancel----------+                +--cancel request--> cancel-requested
                      |                                      |             |
                      +--cancel request----------------------+             |
                                                             +--stop------> cancelled
                                                             +--receipt---> completed

leased | running | cancel-requested --execution/config/lease failure--> failed
```

Cancellation and completion may race. If the isolated native process has
already exited and a valid receipt is completed, completion wins. Otherwise the
worker sends `SIGTERM` to the complete process group, escalates to `SIGKILL`
after a bounded grace period, reaps the leader, and only then records
`cancelled`.

An expired lease becomes `failed` with `worker-lease-expired`. It is never
automatically returned to the queue: after a worker crash, an orphaned compiler,
linker, Wine process, or repository mutation cannot be ruled out. An operator or
GPT-web session must inspect the repository and submit a new idempotency key.

## Queue-time binding

Submission takes a shared repository lock, invokes the read-only adapter, and
stores one immutable `ReplayJobSpec`. The spec binds:

- registration, adapter, target, claim, claim type, subject, and their digests;
- the full Git/source snapshot, including dirty and untracked state;
- policy ID and digest plus the replay-relevant service-configuration digest;
- driver ID, driver version, oracle ID, and declared coldness;
- the digest of every factory Python module that can affect replay semantics;
- the per-stage timeout.

The worker takes the existing exclusive repository replay lock and re-observes
these values before starting a native stage. A changed source, oracle input,
adapter interpretation, driver, policy, or factory implementation fails the job
without pretending that the new state fulfilled the old request.

Workspace policy and capacity settings are intentionally excluded from the
replay configuration digest. Changing source-sandbox limits therefore does not
invalidate an already queued canonical replay. Repository registrations,
policy, replay timeout, job/evidence locations, and worker timing remain bound.

## Storage and concurrency

`JobStore` uses SQLite WAL mode, `synchronous=FULL`, foreign keys, and
`BEGIN IMMEDIATE` for submissions and transitions. The database schema is
versioned with `PRAGMA user_version`. Job IDs are random; idempotency keys are
unique across the service.

Submitting an identical spec with the same key returns the original job.
Submitting changed arguments with that key raises a conflict. Atomic queue
claiming ensures that concurrent worker processes cannot execute the same job.
Every transition also writes an ordered append-only event.

The database does not store authoritative truth. Deleting it loses job history
but cannot manufacture an accepted fact. Conversely, copying a successful job
row without its sealed receipt, content-addressed artifacts, live repositories,
and acceptance checks does not produce truth.

## Failure rules

- Unknown or unsupported work fails explicitly; no generic shell fallback exists.
- A worker never reports success by parsing an English status string.
- Process exit, native structured output, receipt integrity, artifact integrity,
  live freshness, and acceptance policy remain independent checks.
- Output is stored in full and read by bounded byte pages. There is no lossy
  “first N characters” truncation.
- Repository paths exist only in the trusted operator configuration and are not
  accepted from MCP callers or returned in model-facing responses.

The normalized schemas are
[`replay-job.schema.json`](../schemas/v1/replay-job.schema.json),
[`durable-job.schema.json`](../schemas/v1/durable-job.schema.json), and
[`service-config.schema.json`](../schemas/v1/service-config.schema.json).
