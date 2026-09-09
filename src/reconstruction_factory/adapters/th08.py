"""Read-only adapter for the established TH08 VC7 ledgers.

TH08 predates the TH095/TH105 inventory schema.  It therefore has a dedicated
adapter instead of being coerced into the newer Windows ledger shape.
"""

from __future__ import annotations

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
    address_component,
    canonical_address,
    canonical_digest,
    parse_int,
    safe_component,
)


class Th08RepositoryAdapter(RepositoryAdapter):
    id = "th08-vc7-ledgers-v1"

    _required = (
        "config/target.toml",
        "config/mapping.csv",
        "config/reccmp-functions.csv",
        "config/implemented.csv",
        "config/matches.csv",
        "config/match-units.toml",
        "config/library-matches.csv",
        "config/library-match-units.toml",
        "config/library-provenance.toml",
    )

    def detect(self, root: Path) -> bool:
        reader = RepositoryReader(root)
        return all(reader.exists(path) for path in self._required)

    def inspect(self, root: Path) -> RepositorySnapshot:
        root = require_repository_root(root)
        reader = RepositoryReader(root)
        for path in self._required:
            reader.path(path)

        target_manifest = reader.toml("config/target.toml")
        target_data = target_manifest.get("target", {})
        pe_data = target_manifest.get("pe", {})
        toolchain_data = target_manifest.get("toolchain", {})
        filename = str(target_data.get("filename", ""))
        family = str(toolchain_data.get("family", ""))
        if not filename.lower().endswith(".exe") or not pe_data:
            raise AdapterError("TH08 adapter requires an EXE target with a [pe] table")
        if "vc7" not in family.lower() and "2002" not in family.lower():
            raise AdapterError(f"TH08 adapter requires VC7/2002 evidence, got {family!r}")

        project_id = safe_component(Path(filename).stem)
        if project_id != "th08":
            raise AdapterError(f"TH08 adapter refuses unexpected target stem {project_id!r}")
        product_id = "th08-main"
        target_id = f"target:{product_id}"
        project = Project(id=project_id, name=str(target_data.get("title", project_id)))
        product = Product(
            id=product_id,
            project_id=project_id,
            role="gameplay",
            target_identity_id=target_id,
        )
        target = TargetIdentity(
            id=target_id,
            project_id=project_id,
            product_id=product_id,
            game=project_id,
            version=str(target_data["version"]),
            region=str(target_data["region"]),
            format="pe",
            size=int(target_data["size"]),
            sha256=str(target_data["sha256"]),
            md5=str(target_data["md5"]) if target_data.get("md5") else None,
            canonicality="manifest-declared",
            metadata={
                "machine": pe_data.get("machine", ""),
                "image_base": pe_data.get("image_base", ""),
                "entry_point": pe_data.get("entry_point", ""),
                "text_start": pe_data.get("text_start", ""),
                "text_end": pe_data.get("text_end", ""),
                "toolchain_family": family,
            },
        )
        library_provenance = reader.toml("config/library-provenance.toml")
        toolchain = ToolchainIdentity(
            id="toolchain:th08-msvc7",
            project_id=project_id,
            provider_id="msvc7",
            family=family,
            fingerprint_sha256=canonical_digest(
                {
                    "target_toolchain": toolchain_data,
                    "library_provenance": library_provenance,
                }
            ),
            metadata={key: value for key, value in toolchain_data.items() if key != "evidence"},
        )

        mappings = _load_mapping(reader)
        inventory_rows = reader.csv_dicts("config/reccmp-functions.csv")
        inventory = _index_rows(inventory_rows, "reccmp-functions.csv")
        implemented = _load_unique_column(reader, "config/implemented.csv")
        match_rows = _matching_rows(reader, "config/matches.csv")
        matches = _index_rows(match_rows, "matches.csv")
        library_match_rows = _matching_rows(reader, "config/library-matches.csv")
        library_matches = _index_rows(library_match_rows, "library-matches.csv")
        match_units = _load_units(reader, "config/match-units.toml")
        library_units = _load_units(reader, "config/library-match-units.toml")

        authored_addresses = {
            address for address, row in inventory.items() if row.get("type") == "function"
        }
        library_addresses = {
            address for address, row in inventory.items() if row.get("type") == "library"
        }
        if authored_addresses | library_addresses != set(inventory):
            unknown = sorted(
                {str(row.get("type", "")) for row in inventory.values()}
                - {"function", "library"}
            )
            raise AdapterError(f"TH08 inventory contains unknown types: {unknown}")
        if not authored_addresses.issubset(mappings):
            raise AdapterError("TH08 authored inventory contains addresses absent from mapping.csv")
        if not set(matches).issubset(authored_addresses):
            raise AdapterError("TH08 exact matches contain non-authored or unknown addresses")
        if not set(library_matches).issubset(library_addresses):
            raise AdapterError("TH08 library matches contain non-library or unknown addresses")

        unknown_implemented = implemented - {
            str(inventory[address]["name"]) for address in authored_addresses
        }
        if unknown_implemented:
            raise AdapterError(
                f"implemented.csv contains {len(unknown_implemented)} unknown authored names"
            )
        _validate_match_units(matches, match_units, "authored")
        _validate_match_units(library_matches, library_units, "library")

        subjects: list[Subject] = []
        claims: list[Claim] = []
        authored_bytes = 0
        source_present_count = 0
        source_present_bytes = 0
        exact_bytes = 0
        library_known_bytes = 0

        for address, row in sorted(inventory.items()):
            category = str(row["type"])
            mapping = mappings.get(address)
            size = mapping["size"] if mapping is not None else None
            name = str(mapping["name"] if mapping is not None else row["name"])
            subject_id = f"{product_id}:function:{address_component(address)}"
            extents = (Extent("pe-va", address, size),) if size is not None else ()
            subjects.append(
                Subject(
                    id=subject_id,
                    target_identity_id=target_id,
                    kind=SubjectKind.FUNCTION,
                    name=name,
                    extents=extents,
                    metadata={
                        "inventory_name": row["name"],
                        "native_category": category,
                    },
                )
            )
            claims.append(
                Claim(
                    id=f"claim:{subject_id}:origin",
                    subject_id=subject_id,
                    type=ClaimType.ORIGIN_CLASSIFIED,
                    target_identity_id=target_id,
                    value={
                        "origin": "authored_game" if category == "function" else "library",
                        "native_origin": category,
                    },
                    evidence_class=EvidenceClass.OBSERVED,
                    metadata={"source": "config/reccmp-functions.csv"},
                )
            )
            if size is not None:
                claims.append(
                    Claim(
                        id=f"claim:{subject_id}:boundary",
                        subject_id=subject_id,
                        type=ClaimType.BOUNDARY_EXTENT,
                        target_identity_id=target_id,
                        value={"start": address, "size": size, "state": "repository-declared"},
                        evidence_class=EvidenceClass.OBSERVED,
                        metadata={"source": "config/mapping.csv"},
                    )
                )

            inventory_name = str(row["name"])
            if category == "function":
                if size is None:
                    raise AdapterError(f"authored function {address} has no known size")
                authored_bytes += size
                if inventory_name in implemented:
                    source_present_count += 1
                    source_present_bytes += size
                    claims.append(
                        Claim(
                            id=f"claim:{subject_id}:source-present",
                            subject_id=subject_id,
                            type=ClaimType.SOURCE_PRESENT,
                            target_identity_id=target_id,
                            value={"source_present": True, "mapping_name": inventory_name},
                            evidence_class=EvidenceClass.OBSERVED,
                            metadata={"source": "config/implemented.csv"},
                        )
                    )
                match = matches.get(address)
                if match is not None:
                    match_size = parse_int(match["size"], "TH08 match size")
                    if match_size != size:
                        raise AdapterError(f"TH08 exact match size disagrees at {address}")
                    exact_bytes += size
                    claims.append(_exact_claim(subject_id, target_id, toolchain.id, match))
            elif size is not None:
                library_known_bytes += size
                match = library_matches.get(address)
                if match is not None:
                    match_size = parse_int(match["size"], "TH08 library match size")
                    if match_size != size:
                        raise AdapterError(f"TH08 library match size disagrees at {address}")
                    claims.append(_exact_claim(subject_id, target_id, toolchain.id, match))

        metrics = (
            Metric("inventory.authored", len(authored_addresses), project_id),
            Metric("inventory.authored-bytes", authored_bytes, project_id, unit="bytes"),
            Metric(
                "source.present-functions",
                source_present_count,
                project_id,
                total=len(authored_addresses),
            ),
            Metric(
                "source.present-bytes",
                source_present_bytes,
                project_id,
                unit="bytes",
                total=authored_bytes,
            ),
            Metric("exact.functions", len(matches), project_id, total=len(authored_addresses)),
            Metric("exact.bytes", exact_bytes, project_id, unit="bytes", total=authored_bytes),
            Metric("build.configured-units", len(match_units), project_id),
            Metric("inventory.library", len(library_addresses), project_id),
            Metric(
                "inventory.library-sized",
                sum(mappings.get(address) is not None for address in library_addresses),
                project_id,
            ),
            Metric(
                "inventory.library-known-bytes",
                library_known_bytes,
                project_id,
                unit="bytes",
            ),
            Metric("library.configured-units", len(library_units), project_id),
            Metric("library.exact-functions", len(library_matches), project_id),
        )
        diagnostics = (
            Diagnostic(
                code="target-content-unattested",
                severity=Severity.WARNING,
                message=(
                    "The adapter imported target hashes from config/target.toml but did "
                    "not read or rehash the private executable."
                ),
                source="config/target.toml",
            ),
            Diagnostic(
                code="toolchain-content-unattested",
                severity=Severity.WARNING,
                message=(
                    "The adapter fingerprinted declared VC7 library provenance but did "
                    "not read or rehash the compiler or library archives."
                ),
                source="config/library-provenance.toml",
            ),
            Diagnostic(
                code="imported-exact-claims-unreplayed",
                severity=Severity.INFO,
                message=(
                    "Imported authored and library matches have no factory OracleResult "
                    "until cold replayed through a factory oracle envelope."
                ),
                source="config/matches.csv",
            ),
            Diagnostic(
                code="whole-build-state-unattested",
                severity=Severity.WARNING,
                message=(
                    "The adapter does not infer whole-build or runtime closure from the "
                    "function and library ledgers."
                ),
                source="config",
            ),
        )
        return RepositorySnapshot(
            project=project,
            products=(product,),
            targets=(target,),
            toolchains=(toolchain,),
            subjects=tuple(subjects),
            claims=tuple(claims),
            metrics=metrics,
            diagnostics=diagnostics,
            adapter_id=self.id,
            input_fingerprint_sha256=reader.fingerprint(self._required),
        )


def _load_mapping(reader: RepositoryReader) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for line, row in enumerate(reader.csv_rows("config/mapping.csv"), start=1):
        if len(row) < 3:
            raise AdapterError(f"mapping.csv:{line}: expected at least three columns")
        address = canonical_address(row[1])
        if address in result:
            raise AdapterError(f"mapping.csv:{line}: duplicate address {address}")
        size = parse_int(row[2], f"mapping.csv:{line} size")
        if size <= 0:
            raise AdapterError(f"mapping.csv:{line}: size must be positive")
        result[address] = {"name": row[0], "size": size}
    return result


def _index_rows(rows: list[dict[str, str]], source: str) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for line, row in enumerate(rows, start=2):
        if not row.get("address"):
            raise AdapterError(f"{source}:{line}: missing address")
        address = canonical_address(row["address"])
        if address in result:
            raise AdapterError(f"{source}:{line}: duplicate address {address}")
        result[address] = row
    return result


def _load_unique_column(reader: RepositoryReader, path: str) -> set[str]:
    values = reader.csv_column(path)
    if not values or any(not item for item in values):
        raise AdapterError(f"{path} must contain non-empty values")
    if len(values) != len(set(values)):
        raise AdapterError(f"{path} contains duplicate values")
    return set(values)


def _matching_rows(reader: RepositoryReader, path: str) -> list[dict[str, str]]:
    rows = reader.csv_dicts(path)
    rejected = [row for row in rows if row.get("status") != "matching"]
    if rejected:
        raise AdapterError(f"{path} contains non-accepted rows; refusing exact import")
    return rows


def _load_units(reader: RepositoryReader, path: str) -> dict[str, dict[str, Any]]:
    raw_units = reader.toml(path).get("units", [])
    if not isinstance(raw_units, list):
        raise AdapterError(f"{path} must contain an array of units")
    result: dict[str, dict[str, Any]] = {}
    for index, unit in enumerate(raw_units, start=1):
        if not isinstance(unit, dict) or not str(unit.get("name", "")):
            raise AdapterError(f"{path} units[{index}] is malformed")
        name = str(unit["name"])
        if name in result:
            raise AdapterError(f"{path} contains duplicate unit {name!r}")
        result[name] = unit
    return result


def _validate_match_units(
    matches: dict[str, dict[str, str]],
    units: dict[str, dict[str, Any]],
    category: str,
) -> None:
    for address, match in matches.items():
        unit_name = str(match.get("unit", ""))
        unit = units.get(unit_name)
        if unit is None:
            raise AdapterError(f"TH08 {category} match {address} has no configured unit")
        unit_address = canonical_address(str(unit.get("target_address", "")))
        if unit_address != address:
            raise AdapterError(
                f"TH08 {category} match {address} disagrees with unit {unit_name!r}"
            )


def _exact_claim(
    subject_id: str,
    target_id: str,
    toolchain_id: str,
    match: dict[str, str],
) -> Claim:
    return Claim(
        id=f"claim:{subject_id}:codegen-exact",
        subject_id=subject_id,
        type=ClaimType.CODEGEN_EXACT,
        target_identity_id=target_id,
        toolchain_identity_id=toolchain_id,
        value={
            "exact": True,
            "size": parse_int(match["size"], "TH08 exact match size"),
            "match_percent": match.get("match_percent", "100.00"),
            "unit": match.get("unit", ""),
        },
        evidence_class=EvidenceClass.CORROBORATED,
        metadata={"native_evidence": match.get("evidence", "")},
    )
