"""Trusted operator configuration for durable jobs and MCP access."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import tomllib
from typing import Any, Mapping
from urllib.parse import urlsplit

from .acceptance import AcceptancePolicy, load_acceptance_policy
from .errors import ServiceConfigError
from .oracle_receipts import canonical_sha256


SERVICE_CONFIG_SCHEMA_VERSION = 1
_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]*$")
_ANALYSIS_BACKENDS = {"attested-ida-proxy-v1", "attested-ghidra-proxy-v1"}


@dataclass(frozen=True, slots=True)
class AnalysisProviderRegistration:
    """One operator-selected, loopback-only semantic analysis bridge."""

    id: str
    repository_id: str
    target_identity_id: str
    backend: str
    endpoint: str
    upstream_tool: str
    timeout_seconds: int

    def __post_init__(self) -> None:
        for label, value in (
            ("analysis provider id", self.id),
            ("analysis repository id", self.repository_id),
            ("analysis target identity id", self.target_identity_id),
        ):
            _require_id(value, label)
        if self.backend not in _ANALYSIS_BACKENDS:
            raise ServiceConfigError("unsupported analysis provider backend")
        expected_tool = {
            "attested-ida-proxy-v1": "ida_call",
            "attested-ghidra-proxy-v1": "ghidra_call",
        }[self.backend]
        if self.upstream_tool != expected_tool:
            raise ServiceConfigError(
                f"analysis backend {self.backend} requires upstream tool {expected_tool}"
            )
        if (
            not isinstance(self.timeout_seconds, int)
            or isinstance(self.timeout_seconds, bool)
            or not 1 <= self.timeout_seconds <= 3600
        ):
            raise ServiceConfigError(
                "analysis provider timeout_seconds must be from 1 through 3600"
            )
        parsed = urlsplit(self.endpoint)
        try:
            port = parsed.port
        except ValueError as error:
            raise ServiceConfigError(
                "analysis endpoint contains an invalid port"
            ) from error
        if (
            parsed.scheme != "http"
            or parsed.hostname not in {"127.0.0.1", "::1"}
            or port is None
            or parsed.username is not None
            or parsed.password is not None
            or not parsed.path.startswith("/")
            or parsed.path == "/"
            or parsed.path.endswith("/")
            or "//" in parsed.path
            or any(
                not character.isascii()
                or not (character.isalnum() or character in "/._~-")
                for character in parsed.path
            )
            or any(segment in {".", ".."} for segment in parsed.path.split("/"))
            or parsed.query
            or parsed.fragment
        ):
            raise ServiceConfigError(
                "analysis endpoint must be an exact loopback HTTP URL with a non-root path"
            )

    def public_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "repository_id": self.repository_id,
            "target_identity_id": self.target_identity_id,
            "backend": self.backend,
            "read_only": True,
            "authority": "provisional-semantic-analysis",
        }

    def identity_dict(self) -> dict[str, Any]:
        return {
            **self.public_dict(),
            "endpoint": self.endpoint,
            "upstream_tool": self.upstream_tool,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(frozen=True, slots=True)
class WorkspacePolicy:
    """Fail-closed limits for disposable source-only workspaces."""

    enabled: bool
    root: Path
    ttl_seconds: int
    max_active: int
    max_snapshot_files: int
    max_snapshot_bytes: int
    max_file_bytes: int
    command_timeout_seconds: int
    max_command_output_bytes: int
    max_patch_bytes: int

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise ServiceConfigError("workspace.enabled must be a boolean")
        for label, value in (
            ("ttl_seconds", self.ttl_seconds),
            ("max_active", self.max_active),
            ("max_snapshot_files", self.max_snapshot_files),
            ("max_snapshot_bytes", self.max_snapshot_bytes),
            ("max_file_bytes", self.max_file_bytes),
            ("command_timeout_seconds", self.command_timeout_seconds),
            ("max_command_output_bytes", self.max_command_output_bytes),
            ("max_patch_bytes", self.max_patch_bytes),
        ):
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ServiceConfigError(
                    f"workspace.{label} must be a positive integer"
                )
        if self.max_file_bytes > self.max_snapshot_bytes:
            raise ServiceConfigError(
                "workspace.max_file_bytes must not exceed max_snapshot_bytes"
            )

    def public_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "isolation": "bubblewrap-source-only-v1",
            "source_mode": "committed-head",
            "ttl_seconds": self.ttl_seconds,
            "max_active": self.max_active,
            "max_snapshot_files": self.max_snapshot_files,
            "max_snapshot_bytes": self.max_snapshot_bytes,
            "max_file_bytes": self.max_file_bytes,
            "command_timeout_seconds": self.command_timeout_seconds,
            "max_command_output_bytes": self.max_command_output_bytes,
            "max_patch_bytes": self.max_patch_bytes,
        }

    def identity_dict(self) -> dict[str, Any]:
        return {**self.public_dict(), "root": str(self.root)}


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
    analysis_providers: tuple[AnalysisProviderRegistration, ...]
    replay_timeout_seconds: int
    worker_lease_seconds: int
    worker_poll_seconds: float
    workspace: WorkspacePolicy
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
        provider_ids = tuple(item.id for item in self.analysis_providers)
        if tuple(sorted(set(provider_ids))) != provider_ids:
            raise ServiceConfigError(
                "analysis provider registrations must be sorted and unique"
            )
        for provider in self.analysis_providers:
            repository = self.repository(provider.repository_id)
            if provider.target_identity_id not in repository.target_identity_ids:
                raise ServiceConfigError(
                    "analysis provider target is outside its repository registration"
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
        if (
            self.workspace.root == self.state_directory
            or not self.workspace.root.is_relative_to(self.state_directory)
        ):
            raise ServiceConfigError(
                "workspace.root must be a strict child of state_directory"
            )

    @property
    def sha256(self) -> str:
        return canonical_sha256(self.identity_dict())

    @property
    def replay_sha256(self) -> str:
        """Identity of settings that can affect submitted replay execution."""

        return canonical_sha256(self.replay_identity_dict())

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

    def analysis_provider(self, provider_id: str) -> AnalysisProviderRegistration:
        for registration in self.analysis_providers:
            if registration.id == provider_id:
                return registration
        raise ServiceConfigError(
            f"unknown analysis_provider_id {provider_id!r}; "
            "call factory_list_analysis_providers first"
        )

    def public_dict(self) -> dict[str, Any]:
        return {
            "configuration_sha256": self.sha256,
            "replay_configuration_sha256": self.replay_sha256,
            "policy_id": self.policy.id,
            "policy_sha256": self.policy.sha256,
            "repositories": [item.public_dict() for item in self.repositories],
            "analysis_providers": [
                item.public_dict() for item in self.analysis_providers
            ],
            "replay_timeout_seconds": self.replay_timeout_seconds,
            "workspace": self.workspace.public_dict(),
            "schema_version": self.schema_version,
        }

    def identity_dict(self) -> dict[str, Any]:
        return {
            **self.replay_identity_dict(),
            "workspace": self.workspace.identity_dict(),
            "analysis_providers": [
                item.identity_dict() for item in self.analysis_providers
            ],
        }

    def replay_identity_dict(self) -> dict[str, Any]:
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
    root = _strict_object_optional(
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
        {"workspace", "analysis_providers"},
        "service configuration",
    )
    base = config_path.parent
    state_directory = _resolve_path(base, root["state_directory"], "state_directory")
    raw_workspace = root.get("workspace")
    if raw_workspace is None:
        workspace = WorkspacePolicy(
            enabled=False,
            root=state_directory / "workspaces",
            ttl_seconds=86400,
            max_active=4,
            max_snapshot_files=20000,
            max_snapshot_bytes=268435456,
            max_file_bytes=67108864,
            command_timeout_seconds=120,
            max_command_output_bytes=1048576,
            max_patch_bytes=4194304,
        )
    else:
        raw_workspace = _strict_object(
            raw_workspace,
            {
                "enabled",
                "root",
                "ttl_seconds",
                "max_active",
                "max_snapshot_files",
                "max_snapshot_bytes",
                "max_file_bytes",
                "command_timeout_seconds",
                "max_command_output_bytes",
                "max_patch_bytes",
            },
            "workspace",
        )
        workspace = WorkspacePolicy(
            enabled=_boolean(raw_workspace["enabled"], "workspace.enabled"),
            root=_resolve_path(base, raw_workspace["root"], "workspace.root"),
            ttl_seconds=_positive_integer(
                raw_workspace["ttl_seconds"], "workspace.ttl_seconds"
            ),
            max_active=_positive_integer(
                raw_workspace["max_active"], "workspace.max_active"
            ),
            max_snapshot_files=_positive_integer(
                raw_workspace["max_snapshot_files"],
                "workspace.max_snapshot_files",
            ),
            max_snapshot_bytes=_positive_integer(
                raw_workspace["max_snapshot_bytes"],
                "workspace.max_snapshot_bytes",
            ),
            max_file_bytes=_positive_integer(
                raw_workspace["max_file_bytes"], "workspace.max_file_bytes"
            ),
            command_timeout_seconds=_positive_integer(
                raw_workspace["command_timeout_seconds"],
                "workspace.command_timeout_seconds",
            ),
            max_command_output_bytes=_positive_integer(
                raw_workspace["max_command_output_bytes"],
                "workspace.max_command_output_bytes",
            ),
            max_patch_bytes=_positive_integer(
                raw_workspace["max_patch_bytes"], "workspace.max_patch_bytes"
            ),
        )
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
    analysis_registrations = []
    raw_analysis = root.get("analysis_providers", [])
    if not isinstance(raw_analysis, list):
        raise ServiceConfigError("analysis_providers must be an array of tables")
    for index, raw in enumerate(raw_analysis):
        item = _strict_object(
            raw,
            {
                "id",
                "repository_id",
                "target_identity_id",
                "backend",
                "endpoint",
                "upstream_tool",
                "timeout_seconds",
            },
            f"analysis_providers[{index}]",
        )
        analysis_registrations.append(
            AnalysisProviderRegistration(
                id=_string(item["id"], f"analysis_providers[{index}].id"),
                repository_id=_string(
                    item["repository_id"],
                    f"analysis_providers[{index}].repository_id",
                ),
                target_identity_id=_string(
                    item["target_identity_id"],
                    f"analysis_providers[{index}].target_identity_id",
                ),
                backend=_string(
                    item["backend"], f"analysis_providers[{index}].backend"
                ),
                endpoint=_string(
                    item["endpoint"], f"analysis_providers[{index}].endpoint"
                ),
                upstream_tool=_string(
                    item["upstream_tool"],
                    f"analysis_providers[{index}].upstream_tool",
                ),
                timeout_seconds=_positive_integer(
                    item["timeout_seconds"],
                    f"analysis_providers[{index}].timeout_seconds",
                ),
            )
        )
    try:
        config = ServiceConfig(
            path=config_path,
            state_directory=state_directory,
            evidence_store=_resolve_path(
                base, root["evidence_store"], "evidence_store"
            ),
            policy_path=policy_path,
            policy=load_acceptance_policy(policy_path),
            repositories=tuple(sorted(registrations, key=lambda item: item.id)),
            analysis_providers=tuple(
                sorted(analysis_registrations, key=lambda item: item.id)
            ),
            replay_timeout_seconds=_positive_integer(
                root["replay_timeout_seconds"], "replay_timeout_seconds"
            ),
            worker_lease_seconds=_positive_integer(
                root["worker_lease_seconds"], "worker_lease_seconds"
            ),
            worker_poll_seconds=_positive_number(
                root["worker_poll_seconds"], "worker_poll_seconds"
            ),
            workspace=workspace,
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


def _strict_object_optional(
    value: Any,
    required: set[str],
    optional: set[str],
    label: str,
) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ServiceConfigError(f"{label} must be an object")
    missing = required - set(value)
    extra = set(value) - required - optional
    if missing or extra:
        raise ServiceConfigError(
            f"{label} fields differ: missing={sorted(missing)} extra={sorted(extra)}"
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


def _boolean(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise ServiceConfigError(f"{label} must be a boolean")
    return value


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
