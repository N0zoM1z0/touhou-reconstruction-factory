"""Helpers that compose provider kits for normalized repository snapshots."""

from __future__ import annotations

from .errors import CompatibilityError
from .ontology import RepositorySnapshot
from .providers import ProjectSpec, ReconstructionFactory, ReconstructionKit, builtin_registry


def kit_for_snapshot(snapshot: RepositorySnapshot) -> ReconstructionKit:
    formats = {target.format for target in snapshot.targets}
    if formats <= {"mz", "com"}:
        platform_id = "pc98-mz-omf"
    elif formats == {"pe"}:
        platform_id = "windows-pe-coff"
    else:
        raise CompatibilityError(
            f"no built-in platform provider covers target formats: {sorted(formats)}"
        )
    toolchain_ids = {toolchain.provider_id for toolchain in snapshot.toolchains}
    if len(toolchain_ids) != 1:
        raise CompatibilityError(
            "v0 snapshot composition requires exactly one toolchain provider family"
        )
    spec = ProjectSpec(
        project_id=snapshot.project.id,
        platform_provider_id=platform_id,
        toolchain_provider_id=next(iter(toolchain_ids)),
        targets=snapshot.targets,
    )
    return ReconstructionFactory(builtin_registry()).create(spec)

