"""Built-in provider descriptors derived from the reviewed repositories."""

from __future__ import annotations

from dataclasses import dataclass

from ..errors import CompatibilityError
from ..ontology import TargetIdentity
from .base import Capability, PlatformProvider, ProviderRegistry, ToolchainProvider


def _require_format(target: TargetIdentity, accepted: frozenset[str], provider_id: str) -> None:
    if target.format.lower() not in accepted:
        expected = ", ".join(sorted(accepted))
        raise CompatibilityError(
            f"provider {provider_id} requires target format in {{{expected}}}; "
            f"{target.id} declares {target.format!r}"
        )


@dataclass(frozen=True, slots=True)
class Pc98MzOmfPlatform(PlatformProvider):
    id: str = "pc98-mz-omf"
    display_name: str = "PC-98 DOS MZ/OMF"
    capabilities: frozenset[Capability] = frozenset(
        {
            Capability.TARGET_MZ,
            Capability.TARGET_COM,
            Capability.OBJECT_OMF,
            Capability.ADDRESS_SEGMENT_OFFSET,
            Capability.MULTI_PRODUCT,
            Capability.MZ_RELOCATIONS,
            Capability.OMF_FIXUPS,
        }
    )
    compatible_toolchain_ids: frozenset[str] = frozenset({"borland16"})

    def validate_target(self, target: TargetIdentity) -> tuple[str, ...]:
        _require_format(target, frozenset({"mz", "com"}), self.id)
        return (f"{target.id}: segmented PC-98 address model required",)

    def oracle_contracts(self) -> tuple[str, ...]:
        return (
            "target.identity",
            "pc98.mz.container",
            "pc98.mz.relocations",
            "pc98.omf.records-fixups",
            "pc98.segment-layout",
        )


@dataclass(frozen=True, slots=True)
class WindowsPeCoffPlatform(PlatformProvider):
    id: str = "windows-pe-coff"
    display_name: str = "Windows PE/COFF"
    capabilities: frozenset[Capability] = frozenset(
        {
            Capability.TARGET_PE,
            Capability.OBJECT_COFF,
            Capability.ADDRESS_LINEAR_VA,
            Capability.PE_COMDAT,
            Capability.PE_IMPORTS_RESOURCES,
        }
    )
    compatible_toolchain_ids: frozenset[str] = frozenset(
        {"msvc7", "msvc71", "msvc8-ltcg"}
    )

    def validate_target(self, target: TargetIdentity) -> tuple[str, ...]:
        _require_format(target, frozenset({"pe"}), self.id)
        machine = str(target.metadata.get("machine", ""))
        if machine and machine.lower() != "i386":
            raise CompatibilityError(
                f"provider {self.id} currently supports i386 targets; {target.id} declares {machine}"
            )
        return (f"{target.id}: linear PE virtual-address model required",)

    def oracle_contracts(self) -> tuple[str, ...]:
        return (
            "target.identity",
            "windows.pe.container",
            "windows.pe.import-resource-layout",
            "windows.pe.whole-image",
        )


@dataclass(frozen=True, slots=True)
class Borland16Toolchain(ToolchainProvider):
    id: str = "borland16"
    display_name: str = "Borland 16-bit C++ / TASM / TLINK"
    capabilities: frozenset[Capability] = frozenset(
        {
            Capability.OBJECT_OMF,
            Capability.NEAR_FAR_MEMORY_MODEL,
            Capability.ADDRESS_SEGMENT_OFFSET,
            Capability.OMF_FIXUPS,
        }
    )
    compatible_platform_ids: frozenset[str] = frozenset({"pc98-mz-omf"})

    def validate_target(self, target: TargetIdentity) -> tuple[str, ...]:
        return (f"{target.id}: memory model and near/far semantics must be explicit",)

    def oracle_contracts(self) -> tuple[str, ...]:
        return (
            "borland16.codegen",
            "borland16.memory-model",
            "borland16.omf-layout",
        )


@dataclass(frozen=True, slots=True)
class MsvcNonLtcgToolchain(ToolchainProvider):
    id: str
    display_name: str
    compiler_marker: str
    capabilities: frozenset[Capability] = frozenset(
        {
            Capability.OBJECT_COFF,
            Capability.ADDRESS_LINEAR_VA,
            Capability.STANDALONE_COFF_MATCH,
            Capability.PE_COMDAT,
        }
    )
    compatible_platform_ids: frozenset[str] = frozenset({"windows-pe-coff"})

    def validate_target(self, target: TargetIdentity) -> tuple[str, ...]:
        family = str(target.metadata.get("toolchain_family", ""))
        if family and self.compiler_marker.lower() not in family.lower():
            raise CompatibilityError(
                f"provider {self.id} expected toolchain marker {self.compiler_marker!r}; "
                f"{target.id} declares {family!r}"
            )
        return (f"{target.id}: focused COFF proves codegen, not final ownership",)

    def oracle_contracts(self) -> tuple[str, ...]:
        return (
            f"{self.id}.coff-codegen",
            f"{self.id}.relocation-attestation",
            f"{self.id}.link-ownership",
        )


@dataclass(frozen=True, slots=True)
class Msvc8LtcgToolchain(ToolchainProvider):
    id: str = "msvc8-ltcg"
    display_name: str = "Microsoft Visual C++ 2005 LTCG"
    capabilities: frozenset[Capability] = frozenset(
        {
            Capability.OBJECT_COFF,
            Capability.ADDRESS_LINEAR_VA,
            Capability.LTCG_PHYSICAL_OWNERSHIP,
            Capability.NONCONTIGUOUS_EXTENTS,
            Capability.PE_COMDAT,
        }
    )
    compatible_platform_ids: frozenset[str] = frozenset({"windows-pe-coff"})

    def validate_target(self, target: TargetIdentity) -> tuple[str, ...]:
        family = str(target.metadata.get("toolchain_family", ""))
        if family and "VC8" not in family and "2005" not in family:
            raise CompatibilityError(
                f"provider {self.id} requires VC8/2005 evidence; {target.id} declares {family!r}"
            )
        ltcg_records = target.metadata.get("ltcg_cpp_records")
        if ltcg_records is not None and int(ltcg_records) <= 0:
            raise CompatibilityError(
                f"provider {self.id} requires positive LTCG evidence for {target.id}"
            )
        return (f"{target.id}: semantic, object, and physical owners must remain separate",)

    def oracle_contracts(self) -> tuple[str, ...]:
        return (
            "msvc8-ltcg.codegen",
            "msvc8-ltcg.physical-extent-graph",
            "msvc8-ltcg.link-ownership",
        )


def builtin_registry() -> ProviderRegistry:
    registry = ProviderRegistry()
    registry.register_platform(Pc98MzOmfPlatform())
    registry.register_platform(WindowsPeCoffPlatform())
    registry.register_toolchain(Borland16Toolchain())
    registry.register_toolchain(
        MsvcNonLtcgToolchain(
            id="msvc7",
            display_name="Microsoft Visual C++ .NET 2002",
            compiler_marker="VC7",
        )
    )
    registry.register_toolchain(
        MsvcNonLtcgToolchain(
            id="msvc71",
            display_name="Microsoft Visual C++ .NET 2003",
            compiler_marker="VC7.1",
        )
    )
    registry.register_toolchain(Msvc8LtcgToolchain())
    return registry

