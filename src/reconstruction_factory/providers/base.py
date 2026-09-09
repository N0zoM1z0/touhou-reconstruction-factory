"""Composable provider interfaces and Abstract Factory implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from ..errors import CompatibilityError, ValidationError
from ..ontology import TargetIdentity


class Capability(str, Enum):
    """Structural capabilities understood by a provider family.

    These values describe data and oracle-contract semantics. They do not claim
    that a complete binary oracle has already been implemented in this repo.
    """

    TARGET_MZ = "target.mz"
    TARGET_COM = "target.com"
    TARGET_PE = "target.pe"
    OBJECT_OMF = "object.omf"
    OBJECT_COFF = "object.coff"
    ADDRESS_SEGMENT_OFFSET = "address.segment-offset"
    ADDRESS_LINEAR_VA = "address.linear-va"
    MULTI_PRODUCT = "project.multi-product"
    NEAR_FAR_MEMORY_MODEL = "compiler.near-far-memory-model"
    STANDALONE_COFF_MATCH = "compiler.standalone-coff-match"
    LTCG_PHYSICAL_OWNERSHIP = "compiler.ltcg-physical-ownership"
    NONCONTIGUOUS_EXTENTS = "ownership.noncontiguous-extents"
    PE_COMDAT = "link.pe-comdat"
    PE_IMPORTS_RESOURCES = "link.pe-imports-resources"
    MZ_RELOCATIONS = "link.mz-relocations"
    OMF_FIXUPS = "link.omf-fixups"


@dataclass(frozen=True, slots=True)
class ProjectSpec:
    project_id: str
    platform_provider_id: str
    toolchain_provider_id: str
    targets: tuple[TargetIdentity, ...]
    required_capabilities: frozenset[Capability] = frozenset()

    def __post_init__(self) -> None:
        if not self.project_id:
            raise ValidationError("project_id is required")
        if not self.targets:
            raise ValidationError("at least one target is required")
        for target in self.targets:
            if target.project_id != self.project_id:
                raise ValidationError(
                    f"target {target.id} does not belong to project {self.project_id}"
                )


class PlatformProvider(ABC):
    """Platform/container side of a reconstruction provider family."""

    id: str
    display_name: str
    capabilities: frozenset[Capability]
    compatible_toolchain_ids: frozenset[str]

    @abstractmethod
    def validate_target(self, target: TargetIdentity) -> tuple[str, ...]:
        """Return validation notes or raise for an incompatible target."""

    @abstractmethod
    def oracle_contracts(self) -> tuple[str, ...]:
        """Return semantic oracle contract IDs required by this platform."""


class ToolchainProvider(ABC):
    """Compiler/object/link behavior side of a provider family."""

    id: str
    display_name: str
    capabilities: frozenset[Capability]
    compatible_platform_ids: frozenset[str]

    @abstractmethod
    def validate_target(self, target: TargetIdentity) -> tuple[str, ...]:
        """Validate target metadata needed to select this toolchain family."""

    @abstractmethod
    def oracle_contracts(self) -> tuple[str, ...]:
        """Return semantic oracle contract IDs required by this toolchain."""


@dataclass(frozen=True, slots=True)
class ReconstructionKit:
    """A coherent provider family created from one project specification."""

    spec: ProjectSpec
    platform: PlatformProvider
    toolchain: ToolchainProvider
    capabilities: frozenset[Capability]
    oracle_contracts: tuple[str, ...]
    validation_notes: tuple[str, ...]

    def supports(self, capability: Capability) -> bool:
        return capability in self.capabilities


class ProviderRegistry:
    """Registry with duplicate protection and explicit provider namespaces."""

    def __init__(self) -> None:
        self._platforms: dict[str, PlatformProvider] = {}
        self._toolchains: dict[str, ToolchainProvider] = {}

    def register_platform(self, provider: PlatformProvider) -> None:
        self._register(self._platforms, provider.id, provider, "platform")

    def register_toolchain(self, provider: ToolchainProvider) -> None:
        self._register(self._toolchains, provider.id, provider, "toolchain")

    @staticmethod
    def _register(registry: dict[str, object], provider_id: str, provider: object, noun: str) -> None:
        if provider_id in registry:
            raise CompatibilityError(f"duplicate {noun} provider id: {provider_id}")
        registry[provider_id] = provider

    def platform(self, provider_id: str) -> PlatformProvider:
        try:
            return self._platforms[provider_id]
        except KeyError as error:
            raise CompatibilityError(f"unknown platform provider: {provider_id}") from error

    def toolchain(self, provider_id: str) -> ToolchainProvider:
        try:
            return self._toolchains[provider_id]
        except KeyError as error:
            raise CompatibilityError(f"unknown toolchain provider: {provider_id}") from error

    def platform_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._platforms))

    def toolchain_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._toolchains))


class ReconstructionFactory:
    """Create compatible provider families and reject illegal combinations."""

    def __init__(self, registry: ProviderRegistry) -> None:
        self._registry = registry

    def create(self, spec: ProjectSpec) -> ReconstructionKit:
        platform = self._registry.platform(spec.platform_provider_id)
        toolchain = self._registry.toolchain(spec.toolchain_provider_id)

        if toolchain.id not in platform.compatible_toolchain_ids:
            raise CompatibilityError(
                f"platform {platform.id} is not compatible with toolchain {toolchain.id}"
            )
        if platform.id not in toolchain.compatible_platform_ids:
            raise CompatibilityError(
                f"toolchain {toolchain.id} is not compatible with platform {platform.id}"
            )

        notes: list[str] = []
        for target in spec.targets:
            notes.extend(platform.validate_target(target))
            notes.extend(toolchain.validate_target(target))

        capabilities = platform.capabilities | toolchain.capabilities
        missing = spec.required_capabilities - capabilities
        if missing:
            names = ", ".join(sorted(item.value for item in missing))
            raise CompatibilityError(
                f"provider family {platform.id}+{toolchain.id} lacks required capabilities: {names}"
            )

        contracts = _stable_unique(
            (*platform.oracle_contracts(), *toolchain.oracle_contracts())
        )
        return ReconstructionKit(
            spec=spec,
            platform=platform,
            toolchain=toolchain,
            capabilities=capabilities,
            oracle_contracts=contracts,
            validation_notes=tuple(notes),
        )


def _stable_unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))

