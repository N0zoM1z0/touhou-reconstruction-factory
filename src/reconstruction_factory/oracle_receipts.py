"""Factory-controlled, content-bound oracle receipt envelopes."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
import hashlib
import json
from pathlib import PurePosixPath
import re
from typing import Any, Mapping

from .errors import ValidationError
from .ontology import ArtifactRef, OracleResult, OracleRole, Verdict, to_primitive


RECEIPT_SCHEMA_VERSION = 1
RUNNER_ID = "touhou-reconstruction-factory.replay"
RUNNER_VERSION = "1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_RECEIPT_ID = re.compile(r"^receipt:[0-9a-f]{64}$")


class Coldness(str, Enum):
    """How the driver prevents a prior candidate artifact from proving a claim."""

    ISOLATED_DOUBLE_BUILD = "isolated-double-build"
    CLEAN_OUTPUT_GRAPH = "clean-output-graph"
    FORCED_RECOMPILE = "forced-recompile"
    INCREMENTAL = "incremental"
    UNKNOWN = "unknown"


class AttestationLevel(str, Enum):
    """Strength of a binding observation, without implying canonicality."""

    VERIFIED = "verified"
    OBSERVED = "observed"
    UNKNOWN = "unknown"


_ACCEPTANCE_COLDNESS = {
    Coldness.ISOLATED_DOUBLE_BUILD,
    Coldness.CLEAN_OUTPUT_GRAPH,
    Coldness.FORCED_RECOMPILE,
}


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _require_sha256(value: str, field_name: str) -> None:
    if not _SHA256.fullmatch(value):
        raise ValidationError(f"{field_name} must be a lowercase SHA-256 digest")


def _require_relative_path(value: str, field_name: str) -> None:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts:
        raise ValidationError(f"{field_name} must be a contained relative path")


@dataclass(frozen=True, slots=True)
class SourceBinding:
    git_commit: str
    git_tree: str
    repository_scope: str
    snapshot_sha256: str
    file_count: int
    dirty: bool
    untracked_files: int

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[0-9a-f]{40,64}", self.git_commit):
            raise ValidationError("git_commit must be a full hexadecimal object ID")
        if not re.fullmatch(r"[0-9a-f]{40,64}", self.git_tree):
            raise ValidationError("git_tree must be a full hexadecimal object ID")
        if self.repository_scope != ".":
            _require_relative_path(self.repository_scope, "repository_scope")
        _require_sha256(self.snapshot_sha256, "snapshot_sha256")
        if self.file_count < 0 or self.untracked_files < 0:
            raise ValidationError("source binding counts must not be negative")
        if self.untracked_files > self.file_count:
            raise ValidationError("untracked_files cannot exceed file_count")


@dataclass(frozen=True, slots=True)
class TargetBinding:
    identity_id: str
    repository_path: str
    declared_sha256: str
    observed_sha256: str
    declared_size: int
    observed_size: int

    def __post_init__(self) -> None:
        if not self.identity_id:
            raise ValidationError("target identity_id must not be empty")
        _require_relative_path(self.repository_path, "target repository_path")
        _require_sha256(self.declared_sha256, "target declared_sha256")
        _require_sha256(self.observed_sha256, "target observed_sha256")
        if self.declared_size <= 0 or self.observed_size <= 0:
            raise ValidationError("target sizes must be positive")

    @property
    def matches(self) -> bool:
        return (
            self.declared_sha256 == self.observed_sha256
            and self.declared_size == self.observed_size
        )


@dataclass(frozen=True, slots=True)
class ComponentObservation:
    id: str
    kind: str
    logical_path: str
    sha256: str
    size: int
    file_count: int

    def __post_init__(self) -> None:
        if not self.id or not self.kind or not self.logical_path:
            raise ValidationError("component id, kind, and logical_path are required")
        _require_sha256(self.sha256, f"component {self.id} sha256")
        if self.size < 0 or self.file_count < 1:
            raise ValidationError("component size must be non-negative and file_count positive")


@dataclass(frozen=True, slots=True)
class ToolchainBinding:
    identity_id: str
    declared_fingerprint_sha256: str
    attestation: AttestationLevel
    components: tuple[ComponentObservation, ...]
    environment_sha256: str
    environment_names: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.identity_id:
            raise ValidationError("toolchain identity_id must not be empty")
        _require_sha256(
            self.declared_fingerprint_sha256,
            "toolchain declared_fingerprint_sha256",
        )
        _require_sha256(self.environment_sha256, "environment_sha256")
        if len({item.id for item in self.components}) != len(self.components):
            raise ValidationError("toolchain component IDs must be unique")
        if tuple(sorted(set(self.environment_names))) != self.environment_names:
            raise ValidationError("environment_names must be sorted and unique")


@dataclass(frozen=True, slots=True)
class ClaimBinding:
    claim_id: str
    claim_type: str
    claim_sha256: str
    subject_id: str
    subject_sha256: str
    extents: tuple[Mapping[str, Any], ...]

    def __post_init__(self) -> None:
        if not self.claim_id or not self.claim_type or not self.subject_id:
            raise ValidationError("claim binding identifiers must not be empty")
        _require_sha256(self.claim_sha256, "claim_sha256")
        _require_sha256(self.subject_sha256, "subject_sha256")


@dataclass(frozen=True, slots=True)
class InvocationStage:
    id: str
    argv: tuple[str, ...]
    cwd: str
    input_sha256: str

    def __post_init__(self) -> None:
        if not self.id or not self.argv or any(not value for value in self.argv):
            raise ValidationError("invocation stage requires an ID and non-empty argv")
        if self.cwd != ".":
            _require_relative_path(self.cwd, "stage cwd")
        _require_sha256(self.input_sha256, "stage input_sha256")
        if any("\x00" in value for value in self.argv):
            raise ValidationError("invocation argv must not contain NUL")


@dataclass(frozen=True, slots=True)
class StageExecution:
    stage_id: str
    exit_code: int | None
    timed_out: bool
    duration_ms: int
    stdout_ref: str
    stderr_ref: str

    def __post_init__(self) -> None:
        if not self.stage_id or not self.stdout_ref or not self.stderr_ref:
            raise ValidationError("stage execution references must not be empty")
        if self.duration_ms < 0:
            raise ValidationError("stage duration must not be negative")
        if self.timed_out and self.exit_code is not None:
            raise ValidationError("a timed-out stage cannot report an exit code")


@dataclass(frozen=True, slots=True)
class InvocationBinding:
    driver_id: str
    driver_version: str
    coldness: Coldness
    stages: tuple[InvocationStage, ...]
    executions: tuple[StageExecution, ...]

    def __post_init__(self) -> None:
        if not self.driver_id:
            raise ValidationError("driver_id must not be empty")
        _require_sha256(self.driver_version, "driver_version")
        if len({stage.id for stage in self.stages}) != len(self.stages):
            raise ValidationError("invocation stage IDs must be unique")
        if tuple(item.stage_id for item in self.executions) != tuple(
            item.id for item in self.stages[: len(self.executions)]
        ):
            raise ValidationError("stage executions must be an ordered prefix of stages")


@dataclass(frozen=True, slots=True)
class OracleReceipt:
    receipt_id: str
    created_utc: str
    repository_adapter_id: str
    oracle_id: str
    oracle_version: str
    claim: ClaimBinding
    source_before: SourceBinding
    source_after: SourceBinding
    target: TargetBinding
    toolchain: ToolchainBinding
    invocation: InvocationBinding
    result: OracleResult
    artifacts: tuple[ArtifactRef, ...]
    native_report_ref: str | None = None
    acceptance_errors: tuple[str, ...] = ()
    schema_version: int = RECEIPT_SCHEMA_VERSION
    runner_id: str = RUNNER_ID
    runner_version: str = RUNNER_VERSION
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.schema_version != RECEIPT_SCHEMA_VERSION:
            raise ValidationError("unsupported oracle receipt schema version")
        if self.receipt_id and not _RECEIPT_ID.fullmatch(self.receipt_id):
            raise ValidationError("receipt_id must be empty before sealing or content-addressed")
        if not self.created_utc or not self.repository_adapter_id:
            raise ValidationError("receipt timestamp and adapter ID are required")
        if self.runner_id != RUNNER_ID or self.runner_version != RUNNER_VERSION:
            raise ValidationError("unsupported replay runner identity")
        if self.oracle_id != self.result.oracle_id:
            raise ValidationError("receipt oracle_id differs from result")
        if self.oracle_version != self.result.oracle_version:
            raise ValidationError("receipt oracle_version differs from result")
        if self.claim.claim_id != self.result.claim_id:
            raise ValidationError("receipt claim differs from result")
        if self.claim.claim_type != self.result.claim_type.value:
            raise ValidationError("receipt claim type differs from result")
        if self.target.identity_id != self.result.target_identity_id:
            raise ValidationError("receipt target differs from result")
        if self.toolchain.identity_id != self.result.toolchain_identity_id:
            raise ValidationError("receipt toolchain differs from result")
        refs = {artifact.id for artifact in self.artifacts}
        if len(refs) != len(self.artifacts):
            raise ValidationError("receipt artifact IDs must be unique")
        if not set(self.result.evidence_refs).issubset(refs):
            raise ValidationError("result references artifacts absent from receipt")
        if self.native_report_ref is not None and self.native_report_ref not in refs:
            raise ValidationError("native_report_ref is absent from artifacts")
        if self.result.role is OracleRole.ACCEPTANCE and self.result.verdict is Verdict.PASS:
            if self.acceptance_errors:
                raise ValidationError("a passing receipt cannot contain acceptance errors")
            if not self.target.matches:
                raise ValidationError("a passing receipt requires observed target identity")
            if self.source_before.snapshot_sha256 != self.source_after.snapshot_sha256:
                raise ValidationError("a passing receipt requires a stable source snapshot")
            if self.invocation.coldness not in _ACCEPTANCE_COLDNESS:
                raise ValidationError("a passing receipt requires attested cold replay")
            if not self.toolchain.components:
                raise ValidationError("a passing receipt requires observed toolchain components")
            if self.toolchain.attestation is AttestationLevel.UNKNOWN:
                raise ValidationError("a passing receipt requires toolchain observation")
            if len(self.invocation.executions) != len(self.invocation.stages):
                raise ValidationError("a passing receipt requires every stage to execute")
            if any(
                item.timed_out or item.exit_code != 0
                for item in self.invocation.executions
            ):
                raise ValidationError("a passing receipt requires successful stages")

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)

    def seal(self) -> OracleReceipt:
        if self.receipt_id:
            raise ValidationError("receipt is already sealed")
        document = self.to_dict()
        document["receipt_id"] = ""
        digest = canonical_sha256(document)
        return replace(self, receipt_id=f"receipt:{digest}")


def verify_receipt_integrity(document: Mapping[str, Any]) -> str:
    """Return the receipt digest after checking its content-addressed ID."""

    receipt_id = document.get("receipt_id")
    if not isinstance(receipt_id, str) or not _RECEIPT_ID.fullmatch(receipt_id):
        raise ValidationError("receipt document has an invalid receipt_id")
    payload = dict(document)
    payload["receipt_id"] = ""
    digest = canonical_sha256(payload)
    if receipt_id != f"receipt:{digest}":
        raise ValidationError("receipt content digest does not match receipt_id")
    return digest
