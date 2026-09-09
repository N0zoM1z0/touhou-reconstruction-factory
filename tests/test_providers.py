from __future__ import annotations

import unittest

from reconstruction_factory.errors import CompatibilityError
from reconstruction_factory.ontology import TargetIdentity
from reconstruction_factory.providers import (
    Capability,
    ProjectSpec,
    ReconstructionFactory,
    builtin_registry,
)


def target(
    *,
    project_id: str = "test",
    product_id: str = "test-main",
    format: str = "pe",
    family: str = "Microsoft Visual C++ 2005 (VC8)",
    extra: dict[str, object] | None = None,
) -> TargetIdentity:
    metadata = {"machine": "i386", "toolchain_family": family}
    metadata.update(extra or {})
    return TargetIdentity(
        id=f"target:{product_id}",
        project_id=project_id,
        product_id=product_id,
        game=project_id,
        version="1.00",
        region="test",
        format=format,
        size=4096,
        sha256="2" * 64,
        metadata=metadata,
    )


class ProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.factory = ReconstructionFactory(builtin_registry())

    def test_pc98_borland_family_supports_segmented_multi_product(self) -> None:
        first = target(product_id="test-main", format="mz", family="Borland")
        second = target(product_id="test-op", format="com", family="Borland")
        kit = self.factory.create(
            ProjectSpec(
                project_id="test",
                platform_provider_id="pc98-mz-omf",
                toolchain_provider_id="borland16",
                targets=(first, second),
                required_capabilities=frozenset(
                    {Capability.MULTI_PRODUCT, Capability.ADDRESS_SEGMENT_OFFSET}
                ),
            )
        )
        self.assertTrue(kit.supports(Capability.OBJECT_OMF))
        self.assertIn("pc98.mz.relocations", kit.oracle_contracts)

    def test_windows_vc71_family_supports_standalone_coff(self) -> None:
        value = target(family="Microsoft Visual C++ .NET 2003 (VC7.1)")
        kit = self.factory.create(
            ProjectSpec(
                project_id="test",
                platform_provider_id="windows-pe-coff",
                toolchain_provider_id="msvc71",
                targets=(value,),
                required_capabilities=frozenset({Capability.STANDALONE_COFF_MATCH}),
            )
        )
        self.assertTrue(kit.supports(Capability.OBJECT_COFF))

    def test_vc8_ltcg_rejects_standalone_coff_requirement(self) -> None:
        value = target(extra={"ltcg_cpp_records": 42})
        with self.assertRaisesRegex(CompatibilityError, "lacks required capabilities"):
            self.factory.create(
                ProjectSpec(
                    project_id="test",
                    platform_provider_id="windows-pe-coff",
                    toolchain_provider_id="msvc8-ltcg",
                    targets=(value,),
                    required_capabilities=frozenset(
                        {Capability.STANDALONE_COFF_MATCH}
                    ),
                )
            )

    def test_cross_platform_toolchain_is_rejected(self) -> None:
        value = target(format="mz", family="Borland")
        with self.assertRaisesRegex(CompatibilityError, "not compatible"):
            self.factory.create(
                ProjectSpec(
                    project_id="test",
                    platform_provider_id="pc98-mz-omf",
                    toolchain_provider_id="msvc7",
                    targets=(value,),
                )
            )

    def test_platform_rejects_wrong_target_format(self) -> None:
        value = target(format="mz", family="Microsoft Visual C++ .NET 2003 (VC7.1)")
        with self.assertRaisesRegex(CompatibilityError, "requires target format"):
            self.factory.create(
                ProjectSpec(
                    project_id="test",
                    platform_provider_id="windows-pe-coff",
                    toolchain_provider_id="msvc71",
                    targets=(value,),
                )
            )

    def test_ltcg_provider_requires_positive_explicit_evidence(self) -> None:
        value = target(extra={"ltcg_cpp_records": 0})
        with self.assertRaisesRegex(CompatibilityError, "positive LTCG evidence"):
            self.factory.create(
                ProjectSpec(
                    project_id="test",
                    platform_provider_id="windows-pe-coff",
                    toolchain_provider_id="msvc8-ltcg",
                    targets=(value,),
                )
            )


if __name__ == "__main__":
    unittest.main()
