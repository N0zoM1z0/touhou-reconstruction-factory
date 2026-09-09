"""Read-only adapter for the TH04 multi-product PC-98 repository."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from ..errors import AdapterError
from ..ontology import (
    Claim,
    ClaimType,
    Diagnostic,
    EvidenceClass,
    Extent,
    Metric,
    Product,
    Project,
    RepositorySnapshot,
    Severity,
    Subject,
    SubjectKind,
    TargetIdentity,
    ToolchainIdentity,
)
from .base import RepositoryAdapter, require_repository_root
from .common import (
    RepositoryReader,
    canonical_digest,
    normalize_evidence_class,
    normalize_origin,
    parse_int,
)


class Th04RepositoryAdapter(RepositoryAdapter):
    id = "th04-pc98-v1"

    _required = (
        "config/targets.toml",
        "config/toolchain.toml",
        "config/th04_function_boundaries.csv",
        "config/th04_main_authored_functions.csv",
        "config/units.csv",
    )

    def detect(self, root: Path) -> bool:
        reader = RepositoryReader(root)
        return all(reader.exists(path) for path in self._required)

    def inspect(self, root: Path) -> RepositorySnapshot:
        root = require_repository_root(root)
        reader = RepositoryReader(root)
        for path in self._required:
            reader.path(path)

        target_manifest = reader.toml("config/targets.toml")
        toolchain_manifest = reader.toml("config/toolchain.toml")
        boundary_rows = reader.csv_dicts("config/th04_function_boundaries.csv")
        authored_rows = reader.csv_dicts("config/th04_main_authored_functions.csv")
        unit_rows = reader.csv_dicts("config/units.csv")

        project = Project(id="th04", name="Touhou 4 reconstruction")
        source = target_manifest.get("source", {})
        artifacts = [
            item
            for item in target_manifest.get("artifacts", [])
            if item.get("game") == "th04"
        ]
        if not artifacts:
            raise AdapterError("config/targets.toml contains no TH04 artifacts")

        products: list[Product] = []
        targets: list[TargetIdentity] = []
        target_ids: dict[str, str] = {}
        for item in artifacts:
            product_id = str(item["id"])
            target_id = f"target:{product_id}"
            target_ids[product_id] = target_id
            products.append(
                Product(
                    id=product_id,
                    project_id=project.id,
                    role=str(item.get("role", "unknown")),
                    target_identity_id=target_id,
                    required=bool(item.get("required", True)),
                )
            )
            targets.append(
                TargetIdentity(
                    id=target_id,
                    project_id=project.id,
                    product_id=product_id,
                    game="th04",
                    version="unknown",
                    region="japanese-local-attested",
                    format=str(item["format"]).lower(),
                    size=int(item["size"]),
                    sha256=str(item["sha256"]),
                    md5=str(item["md5"]) if item.get("md5") else None,
                    canonicality=str(source.get("canonicality", "unknown")),
                    metadata={
                        "dos_path": item.get("dos_path", ""),
                        "source_kind": source.get("kind", ""),
                        "source_hdi_sha256": source.get("hdi_sha256", ""),
                    },
                )
            )

        exact_toolchain = toolchain_manifest.get("exact", {})
        surfaces = [
            {
                "id": item.get("id"),
                "sha256": item.get("sha256"),
                "required": bool(item.get("required", False)),
            }
            for item in toolchain_manifest.get("surfaces", [])
            if item.get("required", False)
        ]
        toolchain = ToolchainIdentity(
            id="toolchain:th04-borland16",
            project_id=project.id,
            provider_id="borland16",
            family=str(exact_toolchain.get("family", "unknown Borland toolchain")),
            fingerprint_sha256=canonical_digest(
                {"family": exact_toolchain.get("family"), "surfaces": surfaces}
            ),
            metadata={
                "compiler": exact_toolchain.get("compiler", ""),
                "assembler": exact_toolchain.get("assembler", ""),
                "linker": exact_toolchain.get("linker", ""),
                "status": exact_toolchain.get("status", "unknown"),
                "required_surfaces": len(surfaces),
            },
        )

        subjects: list[Subject] = []
        claims: list[Claim] = []
        diagnostics: list[Diagnostic] = [
            Diagnostic(
                code="target-version-unrecorded",
                severity=Severity.WARNING,
                message=(
                    "TH04 target artifacts are hash-attested but the target manifest "
                    "has no explicit game version field."
                ),
                source="config/targets.toml",
            ),
            Diagnostic(
                code="target-content-unattested",
                severity=Severity.WARNING,
                message=(
                    "The adapter imported target hashes from the native manifest but did "
                    "not read or rehash private target content."
                ),
                source="config/targets.toml",
            ),
        ]
        zero_extent_count = 0
        for row in boundary_rows:
            artifact = row["artifact"]
            if artifact not in target_ids:
                continue
            size = parse_int(row["body_size"], "body_size")
            extents = ()
            if size > 0:
                extents = (
                    Extent(
                        address_space="mz-segment-offset",
                        start=f"{row['segment_identity']}:{row['segment_offset']}",
                        size=size,
                        metadata={
                            "analysis_linear": row["analysis_linear"],
                            "payload_offset": row["payload_offset"],
                            "body_span": row["body_span"],
                        },
                    ),
                )
            else:
                zero_extent_count += 1
            subject_id = row["id"]
            subjects.append(
                Subject(
                    id=subject_id,
                    target_identity_id=target_ids[artifact],
                    kind=SubjectKind.FUNCTION,
                    name=row["name"] or subject_id,
                    extents=extents,
                    metadata={
                        "artifact": artifact,
                        "work_queue": row["work_queue"],
                        "accepted_state": row["accepted_state"],
                        "native_boundary_state": row["boundary_state"],
                    },
                )
            )
            claims.append(
                Claim(
                    id=f"claim:{subject_id}:boundary",
                    subject_id=subject_id,
                    type=ClaimType.BOUNDARY_EXTENT,
                    target_identity_id=target_ids[artifact],
                    value={
                        "state": row["boundary_state"],
                        "size": size,
                        "accepted_state": row["accepted_state"],
                    },
                    evidence_class=normalize_evidence_class(row["boundary_state"]),
                    evidence_refs=tuple(
                        value
                        for value in row.get("evidence_basis", "").split("+")
                        if value
                    ),
                    metadata={"observation": row.get("observation", "")},
                )
            )
            origin = normalize_origin(row["origin"])
            if origin is None:
                diagnostics.append(
                    Diagnostic(
                        code="origin-vocabulary-unmapped",
                        severity=Severity.ERROR,
                        message=f"Unmapped TH04 origin {row['origin']!r} for {subject_id}.",
                        source="config/th04_function_boundaries.csv",
                    )
                )
            else:
                claims.append(
                    Claim(
                        id=f"claim:{subject_id}:origin",
                        subject_id=subject_id,
                        type=ClaimType.ORIGIN_CLASSIFIED,
                        target_identity_id=target_ids[artifact],
                        value={
                            "origin": origin.value,
                            "native_origin": row["origin"],
                            "disposition": row["work_queue"],
                        },
                        evidence_class=normalize_evidence_class(row["boundary_state"]),
                        evidence_refs=tuple(
                            value
                            for value in row.get("evidence_basis", "").split("+")
                            if value
                        ),
                    )
                )

        for row in unit_rows:
            artifact = row["artifact"]
            if artifact not in target_ids:
                continue
            size = parse_int(row["compare_size"] or row["size"], "compare_size")
            if size <= 0:
                continue
            subject_id = f"unit:{row['id']}"
            if row["file_offset"]:
                address_space = "mz-file-offset"
                start = row["file_offset"]
            else:
                address_space = "mz-segment-offset"
                start = f"{row['segment']}:{row['offset']}"
            subjects.append(
                Subject(
                    id=subject_id,
                    target_identity_id=target_ids[artifact],
                    kind=SubjectKind.EXTENT,
                    name=row["name"] or row["id"],
                    extents=(
                        Extent(
                            address_space=address_space,
                            start=start,
                            size=size,
                            metadata={"segment": row["segment"], "offset": row["offset"]},
                        ),
                    ),
                    metadata={
                        "native_kind": row["kind"],
                        "source": row["source"],
                        "native_state": row["state"],
                    },
                )
            )
            if row["state"] == "exact":
                claims.append(
                    Claim(
                        id=f"claim:{subject_id}:owned-extent-exact",
                        subject_id=subject_id,
                        type=ClaimType.OWNED_EXTENT_EXACT,
                        target_identity_id=target_ids[artifact],
                        toolchain_identity_id=toolchain.id,
                        value={"exact": True, "compare_size": size},
                        evidence_class=EvidenceClass.CORROBORATED,
                        evidence_refs=tuple(
                            value
                            for value in row.get("evidence_ids", "").split(";")
                            if value
                        ),
                        metadata={"replay_command": row.get("replay_command", "")},
                    )
                )

        diagnostics.extend(
            [
                Diagnostic(
                    code="provisional-boundaries-without-extents",
                    severity=Severity.WARNING,
                    message=(
                        f"Imported {zero_extent_count} boundary observations with zero "
                        "body size; they remain extent-incomplete."
                    ),
                    source="config/th04_function_boundaries.csv",
                ),
                Diagnostic(
                    code="imported-exact-claims-unreplayed",
                    severity=Severity.INFO,
                    message=(
                        "Imported exact unit claims retain native evidence IDs but have no "
                        "factory OracleResult until replayed through a factory oracle envelope."
                    ),
                    source="config/units.csv",
                ),
            ]
        )

        return RepositorySnapshot(
            project=project,
            products=tuple(products),
            targets=tuple(targets),
            toolchains=(toolchain,),
            subjects=tuple(subjects),
            claims=tuple(claims),
            metrics=tuple(
                _th04_metrics(artifacts, boundary_rows, authored_rows, unit_rows)
            ),
            diagnostics=tuple(diagnostics),
            adapter_id=self.id,
            input_fingerprint_sha256=reader.fingerprint(self._required),
        )


def _th04_metrics(
    artifacts: list[dict[str, Any]],
    boundary_rows: list[dict[str, str]],
    authored_rows: list[dict[str, str]],
    unit_rows: list[dict[str, str]],
) -> list[Metric]:
    by_artifact: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in boundary_rows:
        by_artifact[row["artifact"]].append(row)
    authored_by_artifact: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in authored_rows:
        authored_by_artifact[row["artifact"]].append(row)
    units_by_artifact: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in unit_rows:
        units_by_artifact[row["artifact"]].append(row)

    metrics: list[Metric] = []
    aggregate: defaultdict[str, int] = defaultdict(int)
    caveat = (
        "Counts use explicit boundary work queues; exact byte totals use the "
        "reviewed authored-function ledger."
    )
    for artifact in artifacts:
        artifact_id = str(artifact["id"])
        rows = by_artifact[artifact_id]
        reconstruct = [row for row in rows if row["work_queue"] == "reconstruct"]
        exact = [
            row for row in authored_by_artifact[artifact_id] if row["state"] == "exact"
        ]
        blocked = [
            row for row in authored_by_artifact[artifact_id] if row["state"] == "blocked"
        ]
        reviewed_authored_units = [
            row
            for row in units_by_artifact[artifact_id]
            if row["origin"] == "authored"
            and row["boundary_state"] in {"reviewed", "shared"}
        ]
        exact_authored_units = [
            row for row in reviewed_authored_units if row["state"] == "exact"
        ]
        values = {
            "inventory.boundary-observations": len(rows),
            "inventory.authored-candidates": len(reconstruct),
            "inventory.authored-unreviewed": sum(
                row["accepted_state"] == "unreviewed" for row in reconstruct
            ),
            "inventory.authored-blocked": sum(
                row["accepted_state"] == "blocked" for row in reconstruct
            ),
            "exact.authored-functions": len(exact),
            "exact.authored-bytes": sum(
                parse_int(row["size"], "size") for row in exact_authored_units
            ),
            "reviewed.authored-functions": len(exact) + len(blocked),
            "reviewed.authored-bytes": sum(
                parse_int(row["size"], "size") for row in reviewed_authored_units
            ),
            "target.bytes": int(artifact["size"]),
        }
        for name, value in values.items():
            aggregate[name] += value
            total = (
                len(reconstruct)
                if name in {"exact.authored-functions", "reviewed.authored-functions"}
                else None
            )
            metrics.append(
                Metric(
                    name=name,
                    value=value,
                    total=total,
                    scope_id=artifact_id,
                    caveat=caveat,
                )
            )
    for name, value in sorted(aggregate.items()):
        metrics.append(Metric(name=name, value=value, scope_id="th04", caveat=caveat))
    return metrics
