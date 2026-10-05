# Recorded read-only reference mount validation, 2026-10-05

This dated record reports observed checks, not current service availability.

TH03's public Factory repository shell successfully read the actual TH04
maintained `src/shared/math/vector.cpp` and `polar.hpp`. The existing canonical
read-only mount worked, but discovery exposed only the reference ID. Web
callers therefore needed operator knowledge of the host path.

Repository discovery now returns `reference_repository_mounts`, including a
stable `/references/<id>` path and an explicit read-only flag. The shell adds
aliases only for the selected repository's registered reference allowlist;
the canonical mount remains read-only. No MCP tool definition changed.

Observed validation covered:

- Bubblewrap reading through both canonical and alias paths, denied writes,
  repository writes/checkpoints, and replay-independent configuration.
- The complete portable release suite: 164 tests, Ruff, whitespace,
  document parsing, CLI entry points and isolated wheel build passed.
- A new shared loopback instance with identical metadata for all 33 tools.
- Actual TH04 source read through the alias from TH03's `src` working
  directory, denied append-open, identical source bytes afterward, and
  unchanged TH03 HEAD/worktree digest. An unallowed reference alias was absent.
- Public proxy switch followed by the same reference checks, a target-attested
  TH03 native Ghidra query and existing repository status checks.
- Both earlier shared MCP processes and the existing replay worker retained
  their original PIDs. Their configuration and enabled state were preserved.

The first candidate port was occupied. Only the new candidate was stopped;
the port's existing owner was left running. The candidate was moved to a
verified free port before validation and public cutover. Operator routes,
ports, backups and receipts remain in ignored state.

Release validation also exposed the TH03 adapter's intentional omission from
the older replay import fingerprint. TH03 currently has no native replay
driver. The audit now permits exactly its inspection-only descriptor subclass
and verifies its AST has no executable overrides, decorators, calls, or new
dependencies, and that no builtin driver advertises its adapter ID. Existing
replay implementation files and queued-job identities are unchanged. Registering
a TH03 native replay driver requires including its adapter in the fingerprint
and a coordinated worker migration; repository-shell Oracle runs do not
publish Truth Kernel acceptance.

## Follow-up native MZ address calls

A public TH03 function query exposed a representation mismatch: the headless
wrapper accepted `segment:offset`, but the Factory rejected it as a malformed
linear address. Native MZ validation and discovery now accept this representation.
Hex strings, decimal strings, unsigned integers, a single `address`, and scalar
or list `addresses` are normalized so Web can reuse displayed addresses directly.
Invalid inputs include accepted fields and formats in their retry guidance.
PE and IDA retain their original address-space boundary. Byte/database
attestation and exact receipt policy are unchanged.

The release suite passed 166 tests. A new shared candidate and the unchanged
public route both queried the real 26-byte polar function using a segmented
address and an integer linear address, with passed target attestation. Reference
read/write-denial checks and all existing repository status calls still passed.
All 33 public tool definitions remained identical; all four prior MCP/worker
processes retained their PIDs during the second hot switch.
