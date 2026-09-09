"""Trusted operator configuration for durable jobs and MCP access."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import tomllib
from typing import Any, Mapping

from .acceptance import AcceptancePolicy, load_acceptance_policy
from .errors import ServiceConfigError
from .oracle_receipts import canonical_sha256


SERVICE_CONFIG_SCHEMA_VERSION = 1
_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]*$")


@dataclass(frozen=True, slots=True)
class RepositoryRegistration:
    """One repository that remote tools may address by opaque stable ID."""

    id: str
    path: Path
    adapter_id: str
    target_identity_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_id(self.id, "repository registration id")
        _require_id(self.adapter_id, "repository adapter id")
        if not self.path.is_absolute() or not self.path.is_dir():
            raise ServiceConfigError(
                "registered repository path must be an existing absolute directory"
            )
        _require_sorted_ids(self.target_identity_ids, "target_identity_ids")
        if not self.target_identity_ids:
            raise ServiceConfigError(
                "registered repository must declare at least one target identity"
            )

    def public_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "adapter_id": self.adapter_id,
            "target_identity_ids": list(self.target_identity_ids),
        }

    def identity_dict(self) -> dict[str, Any]:
        return {**self.public_dict(), "path": str(self.path)}


@dataclass(frozen=True, slots=True)
class ServiceConfig:
    """Complete local authority boundary for the job service."""

    path: Path
    state_directory: Path
    evidence_store: Path
    policy_path: Path
    policy: AcceptancePolicy
    repositories: tuple[RepositoryRegistration, ...]
    replay_timeout_seconds: int
    worker_lease_seconds: int
    worker_poll_seconds: float
    schema_version: int = SERVICE_CONFIG_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if (
            not isinstance(self.schema_version, int)
            or isinstance(self.schema_version, bool)
            or self.schema_version != SERVICE_CONFIG_SCHEMA_VERSION
        ):
            raise ServiceConfigError("unsupported service configuration schema version")
        for label, value in (
            ("replay_timeout_seconds", self.replay_timeout_seconds),
            ("worker_lease_seconds", self.worker_lease_seconds),
        ):
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ServiceConfigError(f"{label} must be a positive integer")
        if (
            not isinstance(self.worker_poll_seconds, (int, float))
            or isinstance(self.worker_poll_seconds, bool)
            or self.worker_poll_seconds <= 0
        ):
            raise ServiceConfigError("worker_poll_seconds must be positive")
        if self.worker_lease_seconds < 3:
            raise ServiceConfigError(
                "worker_lease_seconds must be at least three seconds"
            )
        if self.worker_poll_seconds > self.worker_lease_seconds / 3:
            raise ServiceConfigError(
                "worker polling must be shorter than one third of the lease"
            )
        ids = tuple(item.id for item in self.repositories)
        if tuple(sorted(set(ids))) != ids or not ids:
            raise ServiceConfigError(
                "repository registrations must be non-empty, sorted, and unique"
            )
        repository_paths = tuple(item.path for item in self.repositories)
        if len(set(repository_paths)) != len(repository_paths):
            raise ServiceConfigError(
                "each canonical repository path must have exactly one registration"
            )
        targets = [
            target_id
            for repository in self.repositories
            for target_id in repository.target_identity_ids
        ]
        if len(set(targets)) != len(targets):
            raise ServiceConfigError(
                "target identities must belong to exactly one registration"
            )
        if self.state_directory.is_relative_to(
            self.evidence_store
        ) or self.evidence_store.is_relative_to(self.state_directory):
            raise ServiceConfigError(
                "state_directory and evidence_store must not overlap"
            )
        for index, repository_path in enumerate(repository_paths):
            for other in repository_paths[index + 1 :]:
                if repository_path.is_relative_to(other) or other.is_relative_to(
                    repository_path
                ):
                    raise ServiceConfigError(
                        "registered repository paths must not overlap"
                    )
        for registration in self.repositories:
            for label, service_path in (
                ("state_directory", self.state_directory),
                ("evidence_store", self.evidence_store),
            ):
                if service_path.is_relative_to(
                    registration.path
                ) or registration.path.is_relative_to(service_path):
                    raise ServiceConfigError(
                        f"{label} must not overlap a registered repository"
                    )

    @property
    def sha256(self) -> str:
        return canonical_sha256(self.identity_dict())

    @property
    def database_path(self) -> Path:
        return self.state_directory / "jobs.sqlite3"

    def repository(self, repository_id: str) -> RepositoryRegistration:
        for registration in self.repositories:
            if registration.id == repository_id:
                return registration
        raise ServiceConfigError(
            f"unknown repository_id {repository_id!r}; call factory_list_repositories first"
        )

    def repository_map(self) -> dict[str, Path]:
        return {
            target_id: registration.path
            for registration in self.repositories
            for target_id in registration.target_identity_ids
        }

    def public_dict(self) -> dict[str, Any]:
        return {
            "configuration_sha256": self.sha256,
            "policy_id": self.policy.id,
            "policy_sha256": self.policy.sha256,
            "repositories": [item.public_dict() for item in self.repositories],
            "replay_timeout_seconds": self.replay_timeout_seconds,
            "schema_version": self.schema_version,
        }

    def identity_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "state_directory": str(self.state_directory),
            "evidence_store": str(self.evidence_store),
            "policy_path": str(self.policy_path),
            "policy_id": self.policy.id,
            "policy_sha256": self.policy.sha256,
            "repositories": [item.identity_dict() for item in self.repositories],
            "replay_timeout_seconds": self.replay_timeout_seconds,
            "worker_lease_seconds": self.worker_lease_seconds,
            "worker_poll_seconds": self.worker_poll_seconds,
        }


def load_service_config(path: str | Path) -> ServiceConfig:
    """Load one exact, closed-world operator configuration."""

    config_path = Path(path).expanduser().resolve(strict=True)
    try:
        document = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise ServiceConfigError(
            f"cannot load service configuration: {error}"
        ) from error
    root = _strict_object(
        document,
        {
            "schema_version",
            "state_directory",
            "evidence_store",
            "policy",
            "replay_timeout_seconds",
            "worker_lease_seconds",
            "worker_poll_seconds",
            "repositories",
        },
        "service configuration",
    )
    base = config_path.parent
    policy_path = _resolve_path(base, root["policy"], "policy", must_exist=True)
    registrations = []
    raw_repositories = root["repositories"]
    if not isinstance(raw_repositories, list):
        raise ServiceConfigError("repositories must be an array of tables")
    for index, raw in enumerate(raw_repositories):
        item = _strict_object(
            raw,
            {"id", "path", "adapter_id", "target_identity_ids"},
            f"repositories[{index}]",
        )
        registrations.append(
            RepositoryRegistration(
                id=_string(item["id"], f"repositories[{index}].id"),
                path=_resolve_path(
                    base,
                    item["path"],
                    f"repositories[{index}].path",
                    must_exist=True,
                ),
                adapter_id=_string(
                    item["adapter_id"], f"repositories[{index}].adapter_id"
                ),
                target_identity_ids=_strings(
                    item["target_identity_ids"],
                    f"repositories[{index}].target_identity_ids",
                ),
            )
        )
    try:
        config = ServiceConfig(
            path=config_path,
            state_directory=_resolve_path(
                base, root["state_directory"], "state_directory"
            ),
            evidence_store=_resolve_path(
                base, root["evidence_store"], "evidence_store"
            ),
            policy_path=policy_path,
            policy=load_acceptance_policy(policy_path),
            repositories=tuple(sorted(registrations, key=lambda item: item.id)),
            replay_timeout_seconds=_positive_integer(
                root["replay_timeout_seconds"], "replay_timeout_seconds"
            ),
            worker_lease_seconds=_positive_integer(
                root["worker_lease_seconds"], "worker_lease_seconds"
            ),
            worker_poll_seconds=_positive_number(
                root["worker_poll_seconds"], "worker_poll_seconds"
            ),
            schema_version=_integer(root["schema_version"], "schema_version"),
        )
    except OSError as error:
        raise ServiceConfigError(
            f"cannot resolve service configuration path: {error}"
        ) from error
    return config


def _strict_object(
    value: Any,
    expected: set[str],
    label: str,
) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ServiceConfigError(f"{label} must be an object")
    if set(value) != expected:
        raise ServiceConfigError(
            f"{label} fields differ: missing={sorted(expected - set(value))} "
            f"extra={sorted(set(value) - expected)}"
        )
    return value


def _resolve_path(
    base: Path,
    value: Any,
    label: str,
    *,
    must_exist: bool = False,
) -> Path:
    raw = _string(value, label)
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = base / candidate
    try:
        return candidate.resolve(strict=must_exist)
    except OSError as error:
        raise ServiceConfigError(f"{label} cannot be resolved: {error}") from error


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ServiceConfigError(f"{label} must be a non-empty string")
    return value.strip()


def _strings(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ServiceConfigError(f"{label} must be an array")
    values = tuple(_string(item, label) for item in value)
    _require_sorted_ids(values, label)
    return values


def _require_id(value: str, label: str) -> None:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ServiceConfigError(f"{label} must be a normalized ID")


def _require_sorted_ids(values: tuple[str, ...], label: str) -> None:
    for value in values:
        _require_id(value, label)
    if tuple(sorted(set(values))) != values:
        raise ServiceConfigError(f"{label} must be sorted and unique")


def _integer(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ServiceConfigError(f"{label} must be an integer")
    return value


def _positive_integer(value: Any, label: str) -> int:
    result = _integer(value, label)
    if result <= 0:
        raise ServiceConfigError(f"{label} must be positive")
    return result


def _positive_number(value: Any, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
        raise ServiceConfigError(f"{label} must be positive")
    return float(value)
