"""Policy-gated registry for verified oracle receipts."""

from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass, field, replace
from enum import Enum
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any, Mapping

from .adapters import inspect_repository
from .artifact_store import ArtifactStore
from .errors import AcceptanceError, FactoryError, ValidationError
from .ontology import (
    ArtifactRef,
    ClaimType,
    RepositorySnapshot,
    Verdict,
    to_primitive,
)
from .oracle_receipts import (
    AttestationLevel,
    Coldness,
    OracleReceipt,
    canonical_sha256,
    oracle_receipt_from_dict,
    verify_receipt_integrity,
)
from .replay_identity import repository_lock
from .replay_runner import FreshnessObservationCache, verify_live_freshness


ACCEPTANCE_POLICY_SCHEMA_VERSION = 1
ACCEPTANCE_REGISTRY_SCHEMA_VERSION = 1
_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class AcceptanceDecision(str, Enum):
    """Whether a candidate can contribute truth to an accepted view."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"
    INVALID = "invalid"


_ATTESTATION_RANK = {
    AttestationLevel.UNKNOWN: 0,
    AttestationLevel.OBSERVED: 1,
    AttestationLevel.VERIFIED: 2,
}


@dataclass(frozen=True, slots=True)
class AcceptancePolicy:
    """Explicit allowlist and evidence threshold for receipt promotion."""

    id: str
    description: str
    allowed_adapter_ids: tuple[str, ...]
    allowed_claim_types: tuple[ClaimType, ...]
    allowed_oracle_ids: tuple[str, ...]
    allowed_driver_ids: tuple[str, ...]
    allowed_coldness: tuple[Coldness, ...]
    minimum_attestation: AttestationLevel
    driver_attestation_minimums: tuple[tuple[str, AttestationLevel], ...] = ()
    allow_dirty_source: bool = False
    require_live_freshness: bool = True
    require_complete_coverage: bool = True
    require_empty_acceptance_errors: bool = True
    schema_version: int = ACCEPTANCE_POLICY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _require_id(self.id, "policy id")
        if not isinstance(self.description, str) or not self.description.strip():
            raise ValidationError("acceptance policy description must not be empty")
        if (
            not isinstance(self.schema_version, int)
            or isinstance(self.schema_version, bool)
            or self.schema_version != ACCEPTANCE_POLICY_SCHEMA_VERSION
        ):
            raise ValidationError("unsupported acceptance policy schema version")
        if not self.require_live_freshness:
            raise ValidationError("acceptance policy must require live freshness")
        if not self.require_complete_coverage:
            raise ValidationError("acceptance policy must require complete coverage")
        if not self.require_empty_acceptance_errors:
            raise ValidationError("acceptance policy must reject acceptance errors")
        if not isinstance(self.allow_dirty_source, bool):
            raise ValidationError("allow_dirty_source must be boolean")
        if any(
            not isinstance(value, bool)
            for value in (
                self.require_live_freshness,
                self.require_complete_coverage,
                self.require_empty_acceptance_errors,
            )
        ):
            raise ValidationError("acceptance policy requirements must be boolean")
        if not isinstance(self.minimum_attestation, AttestationLevel):
            raise ValidationError("minimum_attestation must use the attestation vocabulary")
        if any(not isinstance(item, ClaimType) for item in self.allowed_claim_types):
            raise ValidationError("allowed_claim_types must use the claim vocabulary")
        if any(not isinstance(item, Coldness) for item in self.allowed_coldness):
            raise ValidationError("allowed_coldness must use the coldness vocabulary")
        if any(
            not isinstance(level, AttestationLevel)
            for _, level in self.driver_attestation_minimums
        ):
            raise ValidationError(
                "driver attestation minimums must use the attestation vocabulary"
            )
        _require_sorted_unique(self.allowed_adapter_ids, "allowed_adapter_ids")
        _require_sorted_unique(
            tuple(item.value for item in self.allowed_claim_types),
            "allowed_claim_types",
        )
        _require_sorted_unique(self.allowed_oracle_ids, "allowed_oracle_ids")
        _require_sorted_unique(self.allowed_driver_ids, "allowed_driver_ids")
        for label, values in (
            ("allowed_adapter_ids", self.allowed_adapter_ids),
            ("allowed_oracle_ids", self.allowed_oracle_ids),
            ("allowed_driver_ids", self.allowed_driver_ids),
        ):
            for value in values:
                _require_id(value, label)
        _require_sorted_unique(
            tuple(item.value for item in self.allowed_coldness),
            "allowed_coldness",
        )
        if not all(
            (
                self.allowed_adapter_ids,
                self.allowed_claim_types,
                self.allowed_oracle_ids,
                self.allowed_driver_ids,
                self.allowed_coldness,
            )
        ):
            raise ValidationError("acceptance policy allowlists must not be empty")
        driver_ids = tuple(item[0] for item in self.driver_attestation_minimums)
        _require_sorted_unique(driver_ids, "driver_attestation_minimums")
        for driver_id in driver_ids:
            _require_id(driver_id, "driver attestation driver ID")
        if any(driver_id not in self.allowed_driver_ids for driver_id in driver_ids):
            raise ValidationError(
                "driver attestation minimum references a driver outside the allowlist"
            )
        if self.minimum_attestation is AttestationLevel.UNKNOWN or any(
            level is AttestationLevel.UNKNOWN
            for _, level in self.driver_attestation_minimums
        ):
            raise ValidationError("acceptance attestation minimum cannot be unknown")

    @property
    def sha256(self) -> str:
        return canonical_sha256(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "allowed_adapter_ids": list(self.allowed_adapter_ids),
            "allowed_claim_types": [item.value for item in self.allowed_claim_types],
            "allowed_oracle_ids": list(self.allowed_oracle_ids),
            "allowed_driver_ids": list(self.allowed_driver_ids),
            "allowed_coldness": [item.value for item in self.allowed_coldness],
            "minimum_attestation": self.minimum_attestation.value,
            "driver_attestation_minimums": {
                driver_id: level.value
                for driver_id, level in self.driver_attestation_minimums
            },
            "allow_dirty_source": self.allow_dirty_source,
            "require_live_freshness": self.require_live_freshness,
            "require_complete_coverage": self.require_complete_coverage,
            "require_empty_acceptance_errors": self.require_empty_acceptance_errors,
            "schema_version": self.schema_version,
        }

    def violations(self, receipt: OracleReceipt) -> tuple[str, ...]:
        violations = []
        if receipt.result.verdict is not Verdict.PASS:
            violations.append("receipt-verdict-not-pass")
        if receipt.acceptance_errors:
            violations.append("receipt-acceptance-errors-present")
        if not receipt.result.coverage.complete:
            violations.append("receipt-coverage-incomplete")
        if receipt.repository_adapter_id not in self.allowed_adapter_ids:
            violations.append("adapter-not-allowed")
        if receipt.result.claim_type not in self.allowed_claim_types:
            violations.append("claim-type-not-allowed")
        if receipt.oracle_id not in self.allowed_oracle_ids:
            violations.append("oracle-not-allowed")
        if receipt.invocation.driver_id not in self.allowed_driver_ids:
            violations.append("driver-not-allowed")
        if receipt.invocation.coldness not in self.allowed_coldness:
            violations.append("coldness-not-allowed")
        if receipt.source_before.dirty and not self.allow_dirty_source:
            violations.append("dirty-source-not-allowed")
        minimums = dict(self.driver_attestation_minimums)
        minimum = minimums.get(
            receipt.invocation.driver_id,
            self.minimum_attestation,
        )
        if _ATTESTATION_RANK[receipt.toolchain.attestation] < _ATTESTATION_RANK[minimum]:
            violations.append("toolchain-attestation-below-policy")
        return tuple(sorted(set(violations)))


@dataclass(frozen=True, slots=True)
class AcceptanceEntry:
    candidate_path: str
    decision: AcceptanceDecision
    reasons: tuple[str, ...]
    candidate_sha256: str | None = None
    candidate_size: int | None = None
    receipt_id: str | None = None
    claim_id: str | None = None
    claim_type: str | None = None
    target_identity_id: str | None = None
    oracle_id: str | None = None
    oracle_version: str | None = None
    result_id: str | None = None
    verdict: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.decision, AcceptanceDecision):
            raise ValidationError("acceptance decision must use the decision vocabulary")
        candidate = PurePosixPath(self.candidate_path)
        if (
            not self.candidate_path
            or candidate.is_absolute()
            or ".." in candidate.parts
        ):
            raise ValidationError("acceptance candidate path must be relative")
        if (self.candidate_sha256 is None) != (self.candidate_size is None):
            raise ValidationError("candidate hash and size must be present together")
        if self.candidate_sha256 is not None and (
            not _SHA256.fullmatch(self.candidate_sha256)
            or self.candidate_size is None
            or not isinstance(self.candidate_size, int)
            or isinstance(self.candidate_size, bool)
            or self.candidate_size < 0
        ):
            raise ValidationError("candidate content identity is invalid")
        if tuple(sorted(set(self.reasons))) != self.reasons:
            raise ValidationError("acceptance reasons must be sorted and unique")
        if self.decision is AcceptanceDecision.ACCEPTED:
            if self.reasons or not all(
                (
                    self.receipt_id,
                    self.candidate_sha256,
                    self.claim_id,
                    self.claim_type,
                    self.target_identity_id,
                    self.oracle_id,
                    self.oracle_version,
                    self.result_id,
                    self.verdict,
                )
            ):
                raise ValidationError("accepted entry must be complete and reason-free")
            if self.verdict != Verdict.PASS.value:
                raise ValidationError("accepted entry must describe a passing result")
        elif not self.reasons:
            raise ValidationError("non-accepted entry must explain its decision")

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)


@dataclass(frozen=True, slots=True)
class AcceptanceRegistry:
    registry_id: str
    policy_id: str
    policy_sha256: str
    entries: tuple[AcceptanceEntry, ...]
    schema_version: int = ACCEPTANCE_REGISTRY_SCHEMA_VERSION
    _receipts: Mapping[str, OracleReceipt] = field(
        default_factory=dict,
        repr=False,
        compare=False,
    )
    _store: ArtifactStore | None = field(default=None, repr=False, compare=False)
    _repositories: Mapping[str, Path] = field(
        default_factory=dict,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        if not re.fullmatch(r"registry:[0-9a-f]{64}", self.registry_id):
            raise ValidationError("registry_id must be content-addressed")
        _require_id(self.policy_id, "registry policy id")
        if not _SHA256.fullmatch(self.policy_sha256):
            raise ValidationError("registry policy_sha256 must be a SHA-256 digest")
        if (
            not isinstance(self.schema_version, int)
            or isinstance(self.schema_version, bool)
            or self.schema_version != ACCEPTANCE_REGISTRY_SCHEMA_VERSION
        ):
            raise ValidationError("unsupported acceptance registry schema version")
        if tuple(sorted(self.entries, key=lambda item: item.candidate_path)) != self.entries:
            raise ValidationError("acceptance registry entries must be path-sorted")
        if len({entry.candidate_path for entry in self.entries}) != len(self.entries):
            raise ValidationError("acceptance registry candidate paths must be unique")
        accepted_ids = {
            entry.receipt_id
            for entry in self.entries
            if entry.decision is AcceptanceDecision.ACCEPTED
        }
        if accepted_ids != set(self._receipts):
            raise ValidationError("accepted receipt cache differs from registry entries")
        if accepted_ids and self._store is None:
            raise ValidationError("accepted registry requires its verified artifact store")
        accepted_targets = {
            receipt.target.identity_id for receipt in self._receipts.values()
        }
        if not accepted_targets.issubset(self._repositories):
            raise ValidationError("accepted registry requires live repository bindings")
        payload = self.to_dict()
        payload["registry_id"] = ""
        if self.registry_id != "registry:" + canonical_sha256(payload):
            raise ValidationError("registry_id differs from registry contents")

    @property
    def accepted_count(self) -> int:
        return sum(
            entry.decision is AcceptanceDecision.ACCEPTED for entry in self.entries
        )

    @property
    def rejected_count(self) -> int:
        return sum(
            entry.decision is AcceptanceDecision.REJECTED for entry in self.entries
        )

    @property
    def invalid_count(self) -> int:
        return sum(
            entry.decision is AcceptanceDecision.INVALID for entry in self.entries
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "registry_id": self.registry_id,
            "policy_id": self.policy_id,
            "policy_sha256": self.policy_sha256,
            "counts": {
                "candidates": len(self.entries),
                "accepted": self.accepted_count,
                "rejected": self.rejected_count,
                "invalid": self.invalid_count,
            },
            "entries": [entry.to_dict() for entry in self.entries],
            "schema_version": self.schema_version,
        }

    def accepted_facts(
        self,
        *,
        target_identity_id: str | None = None,
        claim_type: ClaimType | None = None,
        oracle_id: str | None = None,
    ) -> tuple[dict[str, Any], ...]:
        receipts = tuple(
            self._receipts[receipt_id]
            for receipt_id in sorted(self._receipts)
            if (
                target_identity_id is None
                or self._receipts[receipt_id].target.identity_id
                == target_identity_id
            )
            and (
                claim_type is None
                or self._receipts[receipt_id].result.claim_type is claim_type
            )
            and (
                oracle_id is None
                or self._receipts[receipt_id].oracle_id == oracle_id
            )
        )
        repositories = []
        for receipt in receipts:
            repository = self._repositories.get(receipt.target.identity_id)
            if repository is None:
                raise AcceptanceError(
                    f"accepted receipt lost repository binding: {receipt.receipt_id}"
                )
            repositories.append(repository)
        with ExitStack() as locks:
            for repository in sorted(set(repositories), key=str):
                locks.enter_context(repository_lock(repository, exclusive=False))
            facts = []
            freshness_observations = FreshnessObservationCache()
            for receipt in receipts:
                self._verify_artifacts(receipt)
                repository = self._repositories[receipt.target.identity_id]
                errors = verify_live_freshness(
                    receipt.to_dict(),
                    repository,
                    observations=freshness_observations,
                )
                if errors:
                    raise AcceptanceError(
                        f"accepted receipt became stale: {receipt.receipt_id}: "
                        + ", ".join(errors)
                    )
                facts.append(
                    {
                        "receipt_id": receipt.receipt_id,
                        "claim": to_primitive(receipt.claim),
                        "target_identity_id": receipt.target.identity_id,
                        "toolchain_identity_id": receipt.toolchain.identity_id,
                        "source_snapshot_sha256": receipt.source_after.snapshot_sha256,
                        "oracle_id": receipt.oracle_id,
                        "oracle_version": receipt.oracle_version,
                        "result": to_primitive(receipt.result),
                    }
                )
        return tuple(facts)

    def _materialize_snapshot(
        self,
        snapshot: RepositorySnapshot,
    ) -> RepositorySnapshot:
        """Replace untrusted imported results with registry-accepted results."""

        target_ids = {target.id for target in snapshot.targets}
        claims = {claim.id: claim for claim in snapshot.claims}
        subjects = {subject.id: subject for subject in snapshot.subjects}
        receipts = [
            receipt
            for receipt in self._receipts.values()
            if receipt.target.identity_id in target_ids
        ]
        for receipt in receipts:
            claim = claims.get(receipt.claim.claim_id)
            if claim is None:
                raise AcceptanceError(
                    f"accepted receipt references absent claim {receipt.claim.claim_id}"
                )
            subject = subjects.get(claim.subject_id)
            if subject is None:
                raise AcceptanceError(
                    f"accepted receipt references absent subject {claim.subject_id}"
                )
            if receipt.claim.claim_sha256 != canonical_sha256(to_primitive(claim)):
                raise AcceptanceError(
                    f"accepted receipt claim changed: {receipt.claim.claim_id}"
                )
            if receipt.claim.subject_sha256 != canonical_sha256(to_primitive(subject)):
                raise AcceptanceError(
                    f"accepted receipt subject changed: {receipt.claim.subject_id}"
                )
        results = tuple(sorted((item.result for item in receipts), key=lambda item: item.id))
        artifacts = _merge_artifacts(receipts)
        fingerprint = canonical_sha256(
            {
                "adapter_input_fingerprint_sha256": snapshot.input_fingerprint_sha256,
                "acceptance_policy_sha256": self.policy_sha256,
                "receipt_ids": sorted(item.receipt_id for item in receipts),
            }
        )
        return replace(
            snapshot,
            oracle_results=results,
            artifacts=artifacts,
            input_fingerprint_sha256=fingerprint,
        )

    def materialize_live_snapshot(
        self,
        repository: str | Path,
    ) -> RepositorySnapshot:
        root = Path(repository).expanduser().resolve(strict=True)
        with repository_lock(root, exclusive=False):
            snapshot = inspect_repository(root)
            freshness_observations = FreshnessObservationCache(
                snapshots={root: snapshot}
            )
            target_ids = {target.id for target in snapshot.targets}
            for receipt in self._receipts.values():
                if receipt.target.identity_id not in target_ids:
                    continue
                self._verify_artifacts(receipt)
                errors = verify_live_freshness(
                    receipt.to_dict(),
                    root,
                    observations=freshness_observations,
                )
                if errors:
                    raise AcceptanceError(
                        f"accepted receipt became stale: {receipt.receipt_id}: "
                        + ", ".join(errors)
                    )
            return self._materialize_snapshot(snapshot)

    def _verify_artifacts(self, receipt: OracleReceipt) -> None:
        if self._store is None:
            raise AcceptanceError("accepted registry lost its artifact store")
        try:
            self._store.verify_receipt_artifacts(receipt)
        except (FactoryError, OSError) as error:
            raise AcceptanceError(
                f"accepted receipt artifact became invalid: {receipt.receipt_id}"
            ) from error


def load_acceptance_policy(path: str | Path) -> AcceptancePolicy:
    policy_path = Path(path).expanduser().resolve(strict=True)
    try:
        document = json.loads(policy_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValidationError(f"cannot load acceptance policy {policy_path}: {error}") from error
    if not isinstance(document, dict):
        raise ValidationError("acceptance policy must be an object")
    required = {
        "id",
        "description",
        "allowed_adapter_ids",
        "allowed_claim_types",
        "allowed_oracle_ids",
        "allowed_driver_ids",
        "allowed_coldness",
        "minimum_attestation",
        "driver_attestation_minimums",
        "allow_dirty_source",
        "require_live_freshness",
        "require_complete_coverage",
        "require_empty_acceptance_errors",
        "schema_version",
    }
    if set(document) != required:
        raise ValidationError(
            "acceptance policy fields differ: "
            f"missing={sorted(required - set(document))} "
            f"extra={sorted(set(document) - required)}"
        )
    driver_minimums = document["driver_attestation_minimums"]
    if not isinstance(driver_minimums, dict):
        raise ValidationError("driver_attestation_minimums must be an object")
    try:
        return AcceptancePolicy(
            id=_string(document["id"], "policy id"),
            description=_string(document["description"], "policy description"),
            allowed_adapter_ids=_strings(
                document["allowed_adapter_ids"], "allowed_adapter_ids"
            ),
            allowed_claim_types=tuple(
                ClaimType(item)
                for item in _strings(
                    document["allowed_claim_types"], "allowed_claim_types"
                )
            ),
            allowed_oracle_ids=_strings(
                document["allowed_oracle_ids"], "allowed_oracle_ids"
            ),
            allowed_driver_ids=_strings(
                document["allowed_driver_ids"], "allowed_driver_ids"
            ),
            allowed_coldness=tuple(
                Coldness(item)
                for item in _strings(document["allowed_coldness"], "allowed_coldness")
            ),
            minimum_attestation=AttestationLevel(document["minimum_attestation"]),
            driver_attestation_minimums=tuple(
                sorted(
                    (
                        _string(driver_id, "driver attestation driver ID"),
                        AttestationLevel(level),
                    )
                    for driver_id, level in driver_minimums.items()
                )
            ),
            allow_dirty_source=_boolean(
                document["allow_dirty_source"], "allow_dirty_source"
            ),
            require_live_freshness=_boolean(
                document["require_live_freshness"], "require_live_freshness"
            ),
            require_complete_coverage=_boolean(
                document["require_complete_coverage"], "require_complete_coverage"
            ),
            require_empty_acceptance_errors=_boolean(
                document["require_empty_acceptance_errors"],
                "require_empty_acceptance_errors",
            ),
            schema_version=document["schema_version"],
        )
    except (TypeError, ValueError) as error:
        if isinstance(error, ValidationError):
            raise
        raise ValidationError(f"acceptance policy has an invalid enum: {error}") from error


def build_acceptance_registry(
    store: ArtifactStore,
    policy: AcceptancePolicy,
    repositories: Mapping[str, str | Path],
) -> AcceptanceRegistry:
    """Evaluate every receipt candidate without silently dropping failures."""

    repository_map = {
        target_id: Path(path).expanduser().resolve(strict=True)
        for target_id, path in repositories.items()
    }
    for target_id in repository_map:
        _require_id(target_id, "repository target identity")
    with ExitStack() as locks:
        for repository in sorted(set(repository_map.values()), key=str):
            locks.enter_context(repository_lock(repository, exclusive=False))
        return _build_acceptance_registry_locked(store, policy, repository_map)


def _build_acceptance_registry_locked(
    store: ArtifactStore,
    policy: AcceptancePolicy,
    repository_map: Mapping[str, Path],
) -> AcceptanceRegistry:
    entries = []
    accepted: dict[str, OracleReceipt] = {}
    freshness_observations = FreshnessObservationCache()
    candidates = sorted(store.receipts.glob("*.json"), key=lambda path: path.name)
    for path in candidates:
        candidate_path = path.relative_to(store.root).as_posix()
        if path.is_symlink() or not path.is_file():
            entries.append(
                AcceptanceEntry(
                    candidate_path,
                    AcceptanceDecision.INVALID,
                    ("receipt-candidate-not-regular-file",),
                )
            )
            continue
        try:
            candidate_payload = path.read_bytes()
        except OSError:
            entries.append(
                AcceptanceEntry(
                    candidate_path,
                    AcceptanceDecision.INVALID,
                    ("receipt-document-invalid",),
                )
            )
            continue
        candidate_sha256 = hashlib.sha256(candidate_payload).hexdigest()
        candidate_size = len(candidate_payload)
        try:
            document = json.loads(candidate_payload)
        except (UnicodeDecodeError, json.JSONDecodeError):
            entries.append(
                AcceptanceEntry(
                    candidate_path,
                    AcceptanceDecision.INVALID,
                    ("receipt-document-invalid",),
                    candidate_sha256=candidate_sha256,
                    candidate_size=candidate_size,
                )
            )
            continue
        if not isinstance(document, dict):
            entries.append(
                AcceptanceEntry(
                    candidate_path,
                    AcceptanceDecision.INVALID,
                    ("receipt-document-invalid",),
                    candidate_sha256=candidate_sha256,
                    candidate_size=candidate_size,
                )
            )
            continue
        receipt_id = document.get("receipt_id")
        safe_receipt_id = receipt_id if isinstance(receipt_id, str) else None
        try:
            verify_receipt_integrity(document)
        except (FactoryError, TypeError, ValueError):
            entries.append(
                AcceptanceEntry(
                    candidate_path,
                    AcceptanceDecision.INVALID,
                    ("receipt-content-integrity-failed",),
                    candidate_sha256=candidate_sha256,
                    candidate_size=candidate_size,
                    receipt_id=safe_receipt_id,
                )
            )
            continue
        try:
            receipt = oracle_receipt_from_dict(document)
        except (FactoryError, KeyError, TypeError, ValueError):
            entries.append(
                AcceptanceEntry(
                    candidate_path,
                    AcceptanceDecision.INVALID,
                    ("receipt-semantic-validation-failed",),
                    candidate_sha256=candidate_sha256,
                    candidate_size=candidate_size,
                    receipt_id=safe_receipt_id,
                )
            )
            continue
        expected_name = receipt.receipt_id.removeprefix("receipt:") + ".json"
        if path.name != expected_name:
            entries.append(
                _entry_for(
                    candidate_path,
                    receipt,
                    AcceptanceDecision.INVALID,
                    ("receipt-storage-key-mismatch",),
                    candidate_sha256,
                    candidate_size,
                )
            )
            continue
        try:
            store.verify_receipt_artifacts(receipt)
        except (FactoryError, OSError):
            entries.append(
                _entry_for(
                    candidate_path,
                    receipt,
                    AcceptanceDecision.INVALID,
                    ("receipt-artifact-integrity-failed",),
                    candidate_sha256,
                    candidate_size,
                )
            )
            continue
        reasons = list(policy.violations(receipt))
        repository = repository_map.get(receipt.target.identity_id)
        if repository is None:
            reasons.append("repository-binding-missing")
        else:
            try:
                reasons.extend(
                    f"freshness:{reason}"
                    for reason in verify_live_freshness(
                        document,
                        repository,
                        observations=freshness_observations,
                    )
                )
            except (FactoryError, OSError, TypeError, ValueError):
                reasons.append("freshness:evaluation-error")
        reasons_tuple = tuple(sorted(set(reasons)))
        decision = (
            AcceptanceDecision.ACCEPTED
            if not reasons_tuple
            else AcceptanceDecision.REJECTED
        )
        entry = _entry_for(
            candidate_path,
            receipt,
            decision,
            reasons_tuple,
            candidate_sha256,
            candidate_size,
        )
        entries.append(entry)
        if decision is AcceptanceDecision.ACCEPTED:
            if receipt.receipt_id in accepted:
                raise AcceptanceError(f"duplicate accepted receipt: {receipt.receipt_id}")
            accepted[receipt.receipt_id] = receipt
    ordered_entries = tuple(sorted(entries, key=lambda item: item.candidate_path))
    payload = {
        "registry_id": "",
        "policy_id": policy.id,
        "policy_sha256": policy.sha256,
        "counts": _counts(ordered_entries),
        "entries": [entry.to_dict() for entry in ordered_entries],
        "schema_version": ACCEPTANCE_REGISTRY_SCHEMA_VERSION,
    }
    return AcceptanceRegistry(
        registry_id="registry:" + canonical_sha256(payload),
        policy_id=policy.id,
        policy_sha256=policy.sha256,
        entries=ordered_entries,
        _receipts=accepted,
        _store=store,
        _repositories=repository_map,
    )


def _entry_for(
    candidate_path: str,
    receipt: OracleReceipt,
    decision: AcceptanceDecision,
    reasons: tuple[str, ...],
    candidate_sha256: str,
    candidate_size: int,
) -> AcceptanceEntry:
    return AcceptanceEntry(
        candidate_path=candidate_path,
        decision=decision,
        reasons=reasons,
        candidate_sha256=candidate_sha256,
        candidate_size=candidate_size,
        receipt_id=receipt.receipt_id,
        claim_id=receipt.claim.claim_id,
        claim_type=receipt.claim.claim_type,
        target_identity_id=receipt.target.identity_id,
        oracle_id=receipt.oracle_id,
        oracle_version=receipt.oracle_version,
        result_id=receipt.result.id,
        verdict=receipt.result.verdict.value,
    )


def _merge_artifacts(receipts: list[OracleReceipt]) -> tuple[ArtifactRef, ...]:
    candidates: dict[str, list[ArtifactRef]] = {}
    for receipt in receipts:
        for artifact in receipt.artifacts:
            candidates.setdefault(artifact.id, []).append(artifact)
    merged = []
    for artifact_id in sorted(candidates):
        values = candidates[artifact_id]
        identities = {(item.sha256, item.size) for item in values}
        if len(identities) != 1:
            raise AcceptanceError(f"artifact identity conflict: {artifact_id}")
        merged.append(
            min(values, key=lambda item: canonical_sha256(to_primitive(item)))
        )
    return tuple(merged)


def _counts(entries: tuple[AcceptanceEntry, ...]) -> dict[str, int]:
    return {
        "candidates": len(entries),
        "accepted": sum(
            entry.decision is AcceptanceDecision.ACCEPTED for entry in entries
        ),
        "rejected": sum(
            entry.decision is AcceptanceDecision.REJECTED for entry in entries
        ),
        "invalid": sum(
            entry.decision is AcceptanceDecision.INVALID for entry in entries
        ),
    }


def _require_id(value: str, label: str) -> None:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValidationError(f"{label} must be a normalized ID")


def _require_sorted_unique(values: tuple[str, ...], label: str) -> None:
    if any(not isinstance(value, str) or not value for value in values):
        raise ValidationError(f"{label} must contain non-empty strings")
    if tuple(sorted(set(values))) != values:
        raise ValidationError(f"{label} must be sorted and unique")


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValidationError(f"{label} must be a non-empty string")
    return value


def _strings(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValidationError(f"{label} must be an array")
    result = tuple(_string(item, label) for item in value)
    _require_sorted_unique(result, label)
    return result


def _boolean(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValidationError(f"{label} must be boolean")
    return value
