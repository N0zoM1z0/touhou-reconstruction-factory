"""Factory-controlled, content-bound oracle receipt envelopes."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import json
from pathlib import PurePosixPath
import re
from typing import Any, Mapping

from .errors import ValidationError
from .ontology import (
    ArtifactRef,
    ClaimType,
    Coverage,
    Extent,
    ExtentRole,
    OracleResult,
    OracleRole,
    Verdict,
    to_primitive,
)


RECEIPT_SCHEMA_VERSION = 1
RUNNER_ID = "touhou-reconstruction-factory.replay"
RUNNER_VERSION = "1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_RECEIPT_ID = re.compile(r"^receipt:[0-9a-f]{64}$")
_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]*$")


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
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _require_sha256(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValidationError(f"{field_name} must be a lowercase SHA-256 digest")


def _require_id(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValidationError(f"{field_name} must be a normalized ID")


def _require_relative_path(value: str, field_name: str) -> None:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a contained relative path")
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
        if not isinstance(self.git_commit, str) or not re.fullmatch(
            r"[0-9a-f]{40,64}", self.git_commit
        ):
            raise ValidationError("git_commit must be a full hexadecimal object ID")
        if not isinstance(self.git_tree, str) or not re.fullmatch(
            r"[0-9a-f]{40,64}", self.git_tree
        ):
            raise ValidationError("git_tree must be a full hexadecimal object ID")
        if self.repository_scope != ".":
            _require_relative_path(self.repository_scope, "repository_scope")
        _require_sha256(self.snapshot_sha256, "snapshot_sha256")
        if (
            not isinstance(self.file_count, int)
            or not isinstance(self.untracked_files, int)
            or self.file_count < 0
            or self.untracked_files < 0
        ):
            raise ValidationError("source binding counts must not be negative")
        if not isinstance(self.dirty, bool):
            raise ValidationError("source dirty state must be boolean")
        if self.untracked_files > self.file_count:
            raise ValidationError("untracked_files cannot exceed file_count")


@dataclass(frozen=True, slots=True)
class TargetBinding:
    identity_id: str
    repository_path: str
    declared_sha256: str
    observed_before_sha256: str
    observed_after_sha256: str
    declared_size: int
    observed_before_size: int
    observed_after_size: int

    def __post_init__(self) -> None:
        _require_id(self.identity_id, "target identity_id")
        _require_relative_path(self.repository_path, "target repository_path")
        _require_sha256(self.declared_sha256, "target declared_sha256")
        _require_sha256(self.observed_before_sha256, "target observed_before_sha256")
        _require_sha256(self.observed_after_sha256, "target observed_after_sha256")
        if min(
            self.declared_size,
            self.observed_before_size,
            self.observed_after_size,
        ) <= 0:
            raise ValidationError("target sizes must be positive")

    @property
    def matches(self) -> bool:
        return (
            self.declared_sha256
            == self.observed_before_sha256
            == self.observed_after_sha256
            and self.declared_size
            == self.observed_before_size
            == self.observed_after_size
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
        _require_id(self.id, "component id")
        if not self.kind or not self.logical_path:
            raise ValidationError("component kind and logical_path are required")
        _require_sha256(self.sha256, f"component {self.id} sha256")
        if self.size < 0 or self.file_count < 1:
            raise ValidationError("component size must be non-negative and file_count positive")


@dataclass(frozen=True, slots=True)
class ToolchainBinding:
    identity_id: str
    declared_fingerprint_sha256: str
    attestation: AttestationLevel
    components: tuple[ComponentObservation, ...]
    components_sha256: str
    observed_after_sha256: str
    environment_sha256: str
    environment_names: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_id(self.identity_id, "toolchain identity_id")
        _require_sha256(
            self.declared_fingerprint_sha256,
            "toolchain declared_fingerprint_sha256",
        )
        _require_sha256(self.environment_sha256, "environment_sha256")
        _require_sha256(self.components_sha256, "components_sha256")
        _require_sha256(self.observed_after_sha256, "observed_after_sha256")
        if len({item.id for item in self.components}) != len(self.components):
            raise ValidationError("toolchain component IDs must be unique")
        if self.components_sha256 != canonical_sha256(to_primitive(self.components)):
            raise ValidationError("components_sha256 does not describe toolchain components")
        if any(not isinstance(name, str) or not name for name in self.environment_names):
            raise ValidationError("environment_names must contain non-empty strings")
        if tuple(sorted(set(self.environment_names))) != self.environment_names:
            raise ValidationError("environment_names must be sorted and unique")


@dataclass(frozen=True, slots=True)
class ClaimBinding:
    claim_id: str
    claim_type: str
    claim_sha256: str
    subject_id: str
    subject_sha256: str
    extents: tuple[Extent, ...]

    def __post_init__(self) -> None:
        _require_id(self.claim_id, "claim_id")
        _require_id(self.subject_id, "subject_id")
        try:
            ClaimType(self.claim_type)
        except ValueError as error:
            raise ValidationError(f"unknown claim type: {self.claim_type}") from error
        _require_sha256(self.claim_sha256, "claim_sha256")
        _require_sha256(self.subject_sha256, "subject_sha256")


@dataclass(frozen=True, slots=True)
class InvocationStage:
    id: str
    argv: tuple[str, ...]
    cwd: str
    environment_sha256: str
    input_sha256: str

    def __post_init__(self) -> None:
        _require_id(self.id, "invocation stage id")
        if not self.argv or any(not isinstance(value, str) or not value for value in self.argv):
            raise ValidationError("invocation stage requires an ID and non-empty argv")
        if self.cwd != ".":
            _require_relative_path(self.cwd, "stage cwd")
        _require_sha256(self.environment_sha256, "stage environment_sha256")
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
        _require_id(self.stage_id, "stage execution ID")
        _require_id(self.stdout_ref, "stage stdout_ref")
        _require_id(self.stderr_ref, "stage stderr_ref")
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
        _require_id(self.driver_id, "driver_id")
        _require_sha256(self.driver_version, "driver_version")
        if not self.stages:
            raise ValidationError("invocation requires at least one stage")
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
    runner_implementation_sha256: str = ""
    runner_observed_after_sha256: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.schema_version != RECEIPT_SCHEMA_VERSION:
            raise ValidationError("unsupported oracle receipt schema version")
        if not isinstance(self.receipt_id, str) or (
            self.receipt_id and not _RECEIPT_ID.fullmatch(self.receipt_id)
        ):
            raise ValidationError("receipt_id must be empty before sealing or content-addressed")
        if not isinstance(self.created_utc, str):
            raise ValidationError("created_utc must be an ISO 8601 timestamp")
        try:
            created = datetime.fromisoformat(self.created_utc.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValidationError("created_utc must be an ISO 8601 timestamp") from error
        if created.utcoffset() != timedelta(0):
            raise ValidationError("created_utc must identify UTC")
        _require_id(self.repository_adapter_id, "repository_adapter_id")
        _require_id(self.oracle_id, "oracle_id")
        _require_sha256(self.oracle_version, "oracle_version")
        if self.runner_id != RUNNER_ID or self.runner_version != RUNNER_VERSION:
            raise ValidationError("unsupported replay runner identity")
        _require_sha256(
            self.runner_implementation_sha256,
            "runner_implementation_sha256",
        )
        _require_sha256(
            self.runner_observed_after_sha256,
            "runner_observed_after_sha256",
        )
        if self.oracle_id != self.result.oracle_id:
            raise ValidationError("receipt oracle_id differs from result")
        if self.oracle_version != self.result.oracle_version:
            raise ValidationError("receipt oracle_version differs from result")
        if self.invocation.driver_version != self.oracle_version:
            raise ValidationError("receipt oracle_version differs from driver version")
        if self.claim.claim_id != self.result.claim_id:
            raise ValidationError("receipt claim differs from result")
        if self.claim.claim_type != self.result.claim_type.value:
            raise ValidationError("receipt claim type differs from result")
        if self.target.identity_id != self.result.target_identity_id:
            raise ValidationError("receipt target differs from result")
        if self.toolchain.identity_id != self.result.toolchain_identity_id:
            raise ValidationError("receipt toolchain differs from result")
        if self.result.source_tree != self.source_before.snapshot_sha256:
            raise ValidationError("result source binding differs from receipt")
        if self.result.role is not OracleRole.ACCEPTANCE:
            raise ValidationError("oracle receipts require an acceptance result")
        if tuple(sorted(set(self.acceptance_errors))) != self.acceptance_errors:
            raise ValidationError("acceptance_errors must be sorted and unique")
        for stage in self.invocation.stages:
            expected_stage_input = canonical_sha256(
                {
                    "claim_sha256": self.claim.claim_sha256,
                    "subject_sha256": self.claim.subject_sha256,
                    "source_sha256": self.source_before.snapshot_sha256,
                    "target_sha256": self.target.observed_before_sha256,
                    "toolchain_components_sha256": self.toolchain.components_sha256,
                    "environment_sha256": self.toolchain.environment_sha256,
                    "runner_implementation_sha256": self.runner_implementation_sha256,
                    "driver_version": self.invocation.driver_version,
                    "stage": {
                        "id": stage.id,
                        "argv": stage.argv,
                        "cwd": stage.cwd,
                        "environment_sha256": stage.environment_sha256,
                    },
                }
            )
            if stage.input_sha256 != expected_stage_input:
                raise ValidationError("stage input digest differs from receipt bindings")
        refs = {artifact.id for artifact in self.artifacts}
        if len(refs) != len(self.artifacts):
            raise ValidationError("receipt artifact IDs must be unique")
        if not set(self.result.evidence_refs).issubset(refs):
            raise ValidationError("result references artifacts absent from receipt")
        for artifact in self.artifacts:
            if artifact.id != f"artifact:sha256:{artifact.sha256}":
                raise ValidationError("receipt artifact ID must be content-addressed")
        execution_refs = {
            ref
            for execution in self.invocation.executions
            for ref in (execution.stdout_ref, execution.stderr_ref)
        }
        if not execution_refs.issubset(refs):
            raise ValidationError("stage execution references artifacts absent from receipt")
        if self.native_report_ref is not None and self.native_report_ref not in refs:
            raise ValidationError("native_report_ref is absent from artifacts")
        if self.result.coverage.domain == "claimed-bytes":
            extent_bytes = sum(extent.size for extent in self.claim.extents)
            if not self.claim.extents or self.result.coverage.expected_units != extent_bytes:
                raise ValidationError("claimed-byte coverage differs from receipt extents")
        if self.result.role is OracleRole.ACCEPTANCE and self.result.verdict is Verdict.PASS:
            if self.acceptance_errors:
                raise ValidationError("a passing receipt cannot contain acceptance errors")
            if not self.target.matches:
                raise ValidationError("a passing receipt requires observed target identity")
            if self.source_before != self.source_after:
                raise ValidationError("a passing receipt requires a stable source snapshot")
            if (
                self.runner_implementation_sha256
                != self.runner_observed_after_sha256
            ):
                raise ValidationError(
                    "a passing receipt requires a stable runner implementation"
                )
            if self.invocation.coldness not in _ACCEPTANCE_COLDNESS:
                raise ValidationError("a passing receipt requires attested cold replay")
            if not self.toolchain.components:
                raise ValidationError("a passing receipt requires observed toolchain components")
            if self.toolchain.attestation is AttestationLevel.UNKNOWN:
                raise ValidationError("a passing receipt requires toolchain observation")
            if self.toolchain.components_sha256 != self.toolchain.observed_after_sha256:
                raise ValidationError("a passing receipt requires a stable toolchain surface")
            if len(self.invocation.executions) != len(self.invocation.stages):
                raise ValidationError("a passing receipt requires every stage to execute")
            if self.native_report_ref is None:
                raise ValidationError("a passing receipt requires structured native evidence")
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


def oracle_receipt_from_dict(document: Mapping[str, Any]) -> OracleReceipt:
    """Reconstruct and semantically validate an untrusted receipt document."""

    top = _strict_object(
        document,
        {
            "receipt_id",
            "created_utc",
            "repository_adapter_id",
            "oracle_id",
            "oracle_version",
            "claim",
            "source_before",
            "source_after",
            "target",
            "toolchain",
            "invocation",
            "result",
            "artifacts",
            "native_report_ref",
            "acceptance_errors",
            "schema_version",
            "runner_id",
            "runner_version",
            "runner_implementation_sha256",
            "runner_observed_after_sha256",
            "metadata",
        },
        "receipt",
    )
    claim_raw = _strict_object(
        top["claim"],
        {"claim_id", "claim_type", "claim_sha256", "subject_id", "subject_sha256", "extents"},
        "claim binding",
    )
    source_before = SourceBinding(**_strict_object(
        top["source_before"],
        {"git_commit", "git_tree", "repository_scope", "snapshot_sha256", "file_count", "dirty", "untracked_files"},
        "source_before",
    ))
    source_after = SourceBinding(**_strict_object(
        top["source_after"],
        {"git_commit", "git_tree", "repository_scope", "snapshot_sha256", "file_count", "dirty", "untracked_files"},
        "source_after",
    ))
    target = TargetBinding(**_strict_object(
        top["target"],
        {
            "identity_id", "repository_path", "declared_sha256",
            "observed_before_sha256", "observed_after_sha256", "declared_size",
            "observed_before_size", "observed_after_size",
        },
        "target binding",
    ))
    toolchain_raw = _strict_object(
        top["toolchain"],
        {
            "identity_id", "declared_fingerprint_sha256", "attestation", "components",
            "components_sha256", "observed_after_sha256", "environment_sha256",
            "environment_names",
        },
        "toolchain binding",
    )
    components = tuple(
        ComponentObservation(**_strict_object(
            item,
            {"id", "kind", "logical_path", "sha256", "size", "file_count"},
            "toolchain component",
        ))
        for item in _strict_array(toolchain_raw["components"], "toolchain components")
    )
    toolchain = ToolchainBinding(
        identity_id=toolchain_raw["identity_id"],
        declared_fingerprint_sha256=toolchain_raw["declared_fingerprint_sha256"],
        attestation=AttestationLevel(toolchain_raw["attestation"]),
        components=components,
        components_sha256=toolchain_raw["components_sha256"],
        observed_after_sha256=toolchain_raw["observed_after_sha256"],
        environment_sha256=toolchain_raw["environment_sha256"],
        environment_names=tuple(_strict_array(toolchain_raw["environment_names"], "environment names")),
    )
    invocation_raw = _strict_object(
        top["invocation"],
        {"driver_id", "driver_version", "coldness", "stages", "executions"},
        "invocation",
    )
    stages = tuple(
        InvocationStage(
            id=raw["id"],
            argv=tuple(_strict_array(raw["argv"], "stage argv")),
            cwd=raw["cwd"],
            environment_sha256=raw["environment_sha256"],
            input_sha256=raw["input_sha256"],
        )
        for item in _strict_array(invocation_raw["stages"], "invocation stages")
        for raw in [
            _strict_object(
                item,
                {"id", "argv", "cwd", "environment_sha256", "input_sha256"},
                "invocation stage",
            )
        ]
    )
    executions = tuple(
        StageExecution(**_strict_object(
            item,
            {"stage_id", "exit_code", "timed_out", "duration_ms", "stdout_ref", "stderr_ref"},
            "stage execution",
        ))
        for item in _strict_array(invocation_raw["executions"], "stage executions")
    )
    result_raw = _strict_object(
        top["result"],
        {
            "id", "oracle_id", "oracle_version", "role", "claim_id", "claim_type",
            "target_identity_id", "coverage", "verdict", "evidence_refs",
            "toolchain_identity_id", "source_tree", "normalizations", "diagnostics",
            "duration_ms",
        },
        "oracle result",
    )
    coverage_raw = _strict_object(
        result_raw["coverage"],
        {"domain", "expected_units", "observed_units", "complete", "notes"},
        "coverage",
    )
    result = OracleResult(
        id=result_raw["id"],
        oracle_id=result_raw["oracle_id"],
        oracle_version=result_raw["oracle_version"],
        role=OracleRole(result_raw["role"]),
        claim_id=result_raw["claim_id"],
        claim_type=ClaimType(result_raw["claim_type"]),
        target_identity_id=result_raw["target_identity_id"],
        coverage=Coverage(**coverage_raw),
        verdict=Verdict(result_raw["verdict"]),
        evidence_refs=tuple(_strict_array(result_raw["evidence_refs"], "result evidence_refs")),
        toolchain_identity_id=result_raw["toolchain_identity_id"],
        source_tree=result_raw["source_tree"],
        normalizations=tuple(_strict_array(result_raw["normalizations"], "result normalizations")),
        diagnostics=tuple(_strict_array(result_raw["diagnostics"], "result diagnostics")),
        duration_ms=result_raw["duration_ms"],
    )
    artifacts = tuple(
        ArtifactRef(**_strict_object(
            item,
            {"id", "sha256", "media_type", "size", "retention_class", "producer"},
            "artifact",
        ))
        for item in _strict_array(top["artifacts"], "artifacts")
    )
    return OracleReceipt(
        receipt_id=top["receipt_id"],
        created_utc=top["created_utc"],
        repository_adapter_id=top["repository_adapter_id"],
        oracle_id=top["oracle_id"],
        oracle_version=top["oracle_version"],
        claim=ClaimBinding(
            claim_id=claim_raw["claim_id"],
            claim_type=claim_raw["claim_type"],
            claim_sha256=claim_raw["claim_sha256"],
            subject_id=claim_raw["subject_id"],
            subject_sha256=claim_raw["subject_sha256"],
            extents=tuple(
                Extent(
                    address_space=raw["address_space"],
                    start=raw["start"],
                    size=raw["size"],
                    role=ExtentRole(raw["role"]),
                    sha256=raw["sha256"],
                    metadata=_plain_object(raw["metadata"], "extent metadata"),
                )
                for item in _strict_array(claim_raw["extents"], "claim extents")
                for raw in [
                    _strict_object(
                        item,
                        {"address_space", "start", "size", "role", "sha256", "metadata"},
                        "claim extent",
                    )
                ]
            ),
        ),
        source_before=source_before,
        source_after=source_after,
        target=target,
        toolchain=toolchain,
        invocation=InvocationBinding(
            driver_id=invocation_raw["driver_id"],
            driver_version=invocation_raw["driver_version"],
            coldness=Coldness(invocation_raw["coldness"]),
            stages=stages,
            executions=executions,
        ),
        result=result,
        artifacts=artifacts,
        native_report_ref=top["native_report_ref"],
        acceptance_errors=tuple(_strict_array(top["acceptance_errors"], "acceptance_errors")),
        schema_version=top["schema_version"],
        runner_id=top["runner_id"],
        runner_version=top["runner_version"],
        runner_implementation_sha256=top["runner_implementation_sha256"],
        runner_observed_after_sha256=top["runner_observed_after_sha256"],
        metadata=_plain_object(top["metadata"], "metadata"),
    )


def _strict_object(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{label} must be an object")
    actual = set(value)
    if actual != keys:
        raise ValidationError(
            f"{label} fields differ: missing={sorted(keys - actual)} extra={sorted(actual - keys)}"
        )
    return dict(value)


def _strict_array(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValidationError(f"{label} must be an array")
    return value


def _plain_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping) or not all(isinstance(key, str) for key in value):
        raise ValidationError(f"{label} must be an object with string keys")
    return dict(value)
