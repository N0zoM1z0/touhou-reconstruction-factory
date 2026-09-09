"""Normative in-memory model for the reconstruction truth kernel.

The model deliberately separates durable truth claims from temporary work
coordination. Dataclasses validate local invariants; ``RepositorySnapshot``
validates graph references and target binding.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from enum import Enum
import re
from typing import Any, Mapping, Sequence

from .errors import ValidationError


SCHEMA_VERSION = 1
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._:-]*$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_MD5_PATTERN = re.compile(r"^[0-9a-f]{32}$")


def _require_id(value: str, field_name: str = "id") -> None:
    if not _ID_PATTERN.fullmatch(value):
        raise ValidationError(
            f"{field_name} must match {_ID_PATTERN.pattern!r}: {value!r}"
        )


def _require_sha256(value: str, field_name: str = "sha256") -> None:
    if not _SHA256_PATTERN.fullmatch(value):
        raise ValidationError(f"{field_name} must be 64 lowercase hexadecimal characters")


class StringEnum(str, Enum):
    """String-valued enum with stable JSON serialization."""


class SubjectKind(StringEnum):
    PRODUCT = "product"
    FUNCTION = "function"
    EXTENT = "extent"
    DATA = "data"
    SOURCE_UNIT = "source_unit"
    OBJECT = "object"
    SECTION = "section"
    IMAGE = "image"


class ExtentRole(StringEnum):
    PRIMARY = "primary"
    OWNED_CHUNK = "owned_chunk"
    EXCLUSION = "exclusion"
    COMPARISON = "comparison"


class ClaimType(StringEnum):
    TARGET_ATTESTED = "target_attested"
    BOUNDARY_REVIEWED = "boundary_reviewed"
    ORIGIN_CLASSIFIED = "origin_classified"
    SOURCE_PRESENT = "source_present"
    COMPILE_SUCCEEDED = "compile_succeeded"
    CODEGEN_EXACT = "codegen_exact"
    OWNED_EXTENT_EXACT = "owned_extent_exact"
    RELOCATION_DATA_EXACT = "relocation_data_exact"
    SOURCE_OWNERSHIP = "source_ownership"
    OBJECT_OWNERSHIP = "object_ownership"
    PHYSICAL_OWNERSHIP = "physical_ownership"
    SEMANTIC_OWNERSHIP = "semantic_ownership"
    WHOLE_BUILD_CLOSED = "whole_build_closed"
    WHOLE_IMAGE_EXACT = "whole_image_exact"
    SEMANTIC_EVIDENCE = "semantic_evidence"
    PORTABLE_RUNTIME_VALIDATED = "portable_runtime_validated"


class OriginKind(StringEnum):
    AUTHORED_GAME = "authored_game"
    COMPILER_GENERATED = "compiler_generated"
    LIBRARY = "library"
    THIRD_PARTY = "third_party"
    IMPORT_THUNK = "import_thunk"
    ORIGINAL_ASSEMBLY = "original_assembly"
    DATA = "data"
    PADDING = "padding"
    UNKNOWN = "unknown"


class EvidenceClass(StringEnum):
    OBSERVED = "observed"
    CORROBORATED = "corroborated"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


class OracleRole(StringEnum):
    DIAGNOSTIC = "diagnostic"
    ACCEPTANCE = "acceptance"


class Verdict(StringEnum):
    PASS = "pass"
    FAIL = "fail"
    INCOMPLETE = "incomplete"
    ERROR = "error"


class Severity(StringEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class Project:
    id: str
    name: str
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _require_id(self.id)
        if self.schema_version != SCHEMA_VERSION:
            raise ValidationError(f"unsupported project schema version: {self.schema_version}")
        if not self.name.strip():
            raise ValidationError("project name must not be empty")


@dataclass(frozen=True, slots=True)
class Product:
    id: str
    project_id: str
    role: str
    target_identity_id: str
    required: bool = True

    def __post_init__(self) -> None:
        for name, value in (
            ("id", self.id),
            ("project_id", self.project_id),
            ("target_identity_id", self.target_identity_id),
        ):
            _require_id(value, name)
        if not self.role.strip():
            raise ValidationError("product role must not be empty")


@dataclass(frozen=True, slots=True)
class TargetIdentity:
    id: str
    project_id: str
    product_id: str
    game: str
    version: str
    region: str
    format: str
    size: int
    sha256: str
    md5: str | None = None
    canonicality: str = "unknown"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name, value in (
            ("id", self.id),
            ("project_id", self.project_id),
            ("product_id", self.product_id),
        ):
            _require_id(value, name)
        if self.size <= 0:
            raise ValidationError("target size must be positive")
        _require_sha256(self.sha256)
        if self.md5 is not None and not _MD5_PATTERN.fullmatch(self.md5):
            raise ValidationError("md5 must be 32 lowercase hexadecimal characters")
        for name, value in (
            ("game", self.game),
            ("version", self.version),
            ("region", self.region),
            ("format", self.format),
            ("canonicality", self.canonicality),
        ):
            if not value.strip():
                raise ValidationError(f"{name} must not be empty")


@dataclass(frozen=True, slots=True)
class ToolchainIdentity:
    id: str
    project_id: str
    provider_id: str
    family: str
    fingerprint_sha256: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name, value in (
            ("id", self.id),
            ("project_id", self.project_id),
            ("provider_id", self.provider_id),
        ):
            _require_id(value, name)
        _require_sha256(self.fingerprint_sha256, "fingerprint_sha256")
        if not self.family.strip():
            raise ValidationError("toolchain family must not be empty")


@dataclass(frozen=True, slots=True)
class Extent:
    address_space: str
    start: str
    size: int
    role: ExtentRole = ExtentRole.PRIMARY
    sha256: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_id(self.address_space, "address_space")
        if not self.start.strip():
            raise ValidationError("extent start must not be empty")
        if self.size <= 0:
            raise ValidationError("extent size must be positive")
        if self.sha256 is not None:
            _require_sha256(self.sha256)


@dataclass(frozen=True, slots=True)
class Subject:
    id: str
    target_identity_id: str
    kind: SubjectKind
    name: str
    extents: tuple[Extent, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_id(self.id)
        _require_id(self.target_identity_id, "target_identity_id")
        if not self.name.strip():
            raise ValidationError("subject name must not be empty")
        if self.kind in {SubjectKind.FUNCTION, SubjectKind.EXTENT, SubjectKind.DATA} and not self.extents:
            raise ValidationError(f"{self.kind.value} subject requires at least one extent")


@dataclass(frozen=True, slots=True)
class Claim:
    id: str
    subject_id: str
    type: ClaimType
    target_identity_id: str
    value: Mapping[str, Any]
    evidence_class: EvidenceClass
    toolchain_identity_id: str | None = None
    evidence_refs: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name, value in (
            ("id", self.id),
            ("subject_id", self.subject_id),
            ("target_identity_id", self.target_identity_id),
        ):
            _require_id(value, name)
        if self.toolchain_identity_id is not None:
            _require_id(self.toolchain_identity_id, "toolchain_identity_id")
        for dependency in self.dependencies:
            _require_id(dependency, "dependency")


@dataclass(frozen=True, slots=True)
class ArtifactRef:
    id: str
    sha256: str
    media_type: str
    size: int
    retention_class: str
    producer: str

    def __post_init__(self) -> None:
        _require_id(self.id)
        _require_sha256(self.sha256)
        if self.size < 0:
            raise ValidationError("artifact size must not be negative")
        if not self.media_type or not self.retention_class or not self.producer:
            raise ValidationError("artifact media type, retention class, and producer are required")


@dataclass(frozen=True, slots=True)
class Coverage:
    domain: str
    expected_units: int
    observed_units: int
    complete: bool
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.domain.strip():
            raise ValidationError("coverage domain must not be empty")
        if self.expected_units < 0 or self.observed_units < 0:
            raise ValidationError("coverage counts must not be negative")
        if self.complete and self.expected_units != self.observed_units:
            raise ValidationError("complete coverage requires expected_units == observed_units")


@dataclass(frozen=True, slots=True)
class OracleResult:
    id: str
    oracle_id: str
    oracle_version: str
    role: OracleRole
    claim_id: str
    claim_type: ClaimType
    target_identity_id: str
    coverage: Coverage
    verdict: Verdict
    evidence_refs: tuple[str, ...]
    toolchain_identity_id: str | None = None
    source_tree: str | None = None
    normalizations: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = ()
    duration_ms: int | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("id", self.id),
            ("oracle_id", self.oracle_id),
            ("claim_id", self.claim_id),
            ("target_identity_id", self.target_identity_id),
        ):
            _require_id(value, name)
        if not self.oracle_version.strip():
            raise ValidationError("oracle_version must not be empty")
        if self.toolchain_identity_id is not None:
            _require_id(self.toolchain_identity_id, "toolchain_identity_id")
        if self.role is OracleRole.ACCEPTANCE and self.verdict is Verdict.PASS:
            if not self.coverage.complete:
                raise ValidationError("an acceptance pass requires complete coverage")
            if not self.evidence_refs:
                raise ValidationError("an acceptance pass requires durable evidence")
        if self.duration_ms is not None and self.duration_ms < 0:
            raise ValidationError("duration_ms must not be negative")


@dataclass(frozen=True, slots=True)
class Metric:
    name: str
    value: int | float
    scope_id: str
    unit: str = "count"
    total: int | float | None = None
    caveat: str = ""

    def __post_init__(self) -> None:
        _require_id(self.name, "metric name")
        _require_id(self.scope_id, "scope_id")
        if self.total is not None and self.total < 0:
            raise ValidationError("metric total must not be negative")


@dataclass(frozen=True, slots=True)
class Diagnostic:
    code: str
    severity: Severity
    message: str
    source: str = ""

    def __post_init__(self) -> None:
        _require_id(self.code, "diagnostic code")
        if not self.message.strip():
            raise ValidationError("diagnostic message must not be empty")


@dataclass(frozen=True, slots=True)
class WorkLease:
    """Temporary coordination state; never evidence for a truth claim."""

    id: str
    work_packet_id: str
    holder: str
    branch: str
    started_utc: str
    subject_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_id(self.id)
        _require_id(self.work_packet_id, "work_packet_id")
        if not self.holder.strip() or not self.branch.strip() or not self.started_utc.strip():
            raise ValidationError("work lease holder, branch, and start time are required")
        for subject_id in self.subject_ids:
            _require_id(subject_id, "subject_id")


@dataclass(frozen=True, slots=True)
class RepositorySnapshot:
    project: Project
    products: tuple[Product, ...]
    targets: tuple[TargetIdentity, ...]
    toolchains: tuple[ToolchainIdentity, ...]
    subjects: tuple[Subject, ...]
    claims: tuple[Claim, ...]
    oracle_results: tuple[OracleResult, ...] = ()
    artifacts: tuple[ArtifactRef, ...] = ()
    metrics: tuple[Metric, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()
    adapter_id: str = "unknown"
    input_fingerprint_sha256: str = "0" * 64
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _require_id(self.adapter_id, "adapter_id")
        _require_sha256(self.input_fingerprint_sha256, "input_fingerprint_sha256")
        if self.schema_version != SCHEMA_VERSION:
            raise ValidationError(f"unsupported snapshot schema version: {self.schema_version}")

        products = _unique_by_id(self.products, "product")
        targets = _unique_by_id(self.targets, "target")
        toolchains = _unique_by_id(self.toolchains, "toolchain")
        subjects = _unique_by_id(self.subjects, "subject")
        claims = _unique_by_id(self.claims, "claim")
        results = _unique_by_id(self.oracle_results, "oracle result")
        _unique_by_id(self.artifacts, "artifact")

        for product in self.products:
            if product.project_id != self.project.id:
                raise ValidationError(f"product {product.id} belongs to another project")
            if product.target_identity_id not in targets:
                raise ValidationError(f"product {product.id} references an unknown target")
        for target in self.targets:
            if target.project_id != self.project.id or target.product_id not in products:
                raise ValidationError(f"target {target.id} has invalid project/product binding")
        for toolchain in self.toolchains:
            if toolchain.project_id != self.project.id:
                raise ValidationError(f"toolchain {toolchain.id} belongs to another project")
        for subject in self.subjects:
            if subject.target_identity_id not in targets:
                raise ValidationError(f"subject {subject.id} references an unknown target")
        for claim in self.claims:
            subject = subjects.get(claim.subject_id)
            if subject is None:
                raise ValidationError(f"claim {claim.id} references an unknown subject")
            if claim.target_identity_id != subject.target_identity_id:
                raise ValidationError(f"claim {claim.id} is bound to a different target than its subject")
            if claim.toolchain_identity_id and claim.toolchain_identity_id not in toolchains:
                raise ValidationError(f"claim {claim.id} references an unknown toolchain")
            for dependency in claim.dependencies:
                if dependency not in claims:
                    raise ValidationError(f"claim {claim.id} has unknown dependency {dependency}")
        for result in self.oracle_results:
            claim = claims.get(result.claim_id)
            if claim is None:
                raise ValidationError(f"oracle result {result.id} references an unknown claim")
            if result.claim_type is not claim.type:
                raise ValidationError(f"oracle result {result.id} has a different claim type")
            if result.target_identity_id != claim.target_identity_id:
                raise ValidationError(f"oracle result {result.id} is bound to a different target")
            if result.toolchain_identity_id and result.toolchain_identity_id not in toolchains:
                raise ValidationError(f"oracle result {result.id} references an unknown toolchain")

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic JSON-compatible representation."""

        return to_primitive(self)


def _unique_by_id(items: Sequence[Any], noun: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for item in items:
        if item.id in result:
            raise ValidationError(f"duplicate {noun} id: {item.id}")
        result[item.id] = item
    return result


def to_primitive(value: Any) -> Any:
    """Convert truth-kernel values to stable JSON-compatible primitives."""

    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {item.name: to_primitive(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): to_primitive(value[key]) for key in sorted(value)}
    if isinstance(value, (tuple, list)):
        return [to_primitive(item) for item in value]
    return value

