"""Read-only adapter for TH095/TH105-style Windows PE reconstruction ledgers."""

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
    ExtentRole,
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
    normalize_evidence_class,
    normalize_origin,
    parse_int,
    safe_component,
)


class WindowsPeRepositoryAdapter(RepositoryAdapter):
    id = "windows-pe-ledgers-v1"

    _required = (
        "config/target.toml",
        "config/functions.csv",
        "config/function-origins.csv",
        "config/reccmp-functions.csv",
        "config/implemented.csv",
        "config/matches.csv",
        "config/match-units.toml",
        "config/tools.lock.toml",
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
        if not filename.lower().endswith(".exe") or "pe" not in target_manifest:
            raise AdapterError("Windows PE adapter requires an EXE target with a [pe] table")
        project_id = safe_component(Path(filename).stem)
        product_id = f"{project_id}-main"
        target_id = f"target:{product_id}"
        provider_id = _toolchain_provider_id(toolchain_data)

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
                "toolchain_family": toolchain_data.get("family", ""),
                "ltcg_cpp_records": toolchain_data.get("rich_utc1400_ltcg_cpp"),
            },
        )
        tool_lock = reader.toml("config/tools.lock.toml")
        toolchain = ToolchainIdentity(
            id=f"toolchain:{project_id}-{provider_id}",
            project_id=project_id,
            provider_id=provider_id,
            family=str(toolchain_data.get("family", provider_id)),
            fingerprint_sha256=canonical_digest(
                {"target_toolchain": toolchain_data, "tools_lock": tool_lock}
            ),
            metadata={
                key: value for key, value in toolchain_data.items() if key != "evidence"
            },
        )

        function_rows = reader.csv_dicts("config/functions.csv")
        origin_rows = reader.csv_dicts("config/function-origins.csv")
        mapping_rows = reader.csv_dicts("config/reccmp-functions.csv")
        implemented = set(reader.csv_column("config/implemented.csv"))
        match_rows = reader.csv_dicts("config/matches.csv")
        match_units = reader.toml("config/match-units.toml").get("units", {})

        functions = {_address(row["address"]): row for row in function_rows}
        if len(functions) != len(function_rows):
            raise AdapterError("functions.csv contains duplicate addresses")
        origins = {_address(row["address"]): row for row in origin_rows}
        mappings = {_address(row["address"]): row for row in mapping_rows}
        matches = {_address(row["address"]): row for row in match_rows}
        if set(origins) != set(functions):
            missing = sorted(set(functions) - set(origins))
            extra = sorted(set(origins) - set(functions))
            raise AdapterError(
                "function-origins.csv address coverage mismatch: "
                f"missing={len(missing)} extra={len(extra)}"
            )
        if not set(mappings).issubset(functions) or not set(matches).issubset(functions):
            raise AdapterError("mapping or match ledger references an unknown function address")

        ownership_path = "config/function-byte-ownership.toml"
        ownership = (
            _load_ownership(reader.toml(ownership_path), target, functions)
            if reader.exists(ownership_path)
            else {}
        )
        imported_paths = list(self._required)
        if reader.exists(ownership_path):
            imported_paths.append(ownership_path)

        subjects: list[Subject] = []
        claims: list[Claim] = []
        diagnostics: list[Diagnostic] = []
        diagnostics.append(
            Diagnostic(
                code="target-content-unattested",
                severity=Severity.WARNING,
                message=(
                    "The adapter imported target hashes from config/target.toml but did "
                    "not read or rehash the private executable."
                ),
                source="config/target.toml",
            )
        )
        exact_bytes = 0
        authored_bytes = 0
        remote_authored_bytes = 0
        category_counts = {"authored": 0, "excluded": 0, "review": 0}

        for address, row in sorted(functions.items()):
            origin_row = origins[address]
            disposition = origin_row["disposition"]
            category = (
                "authored"
                if disposition == "authored"
                else "excluded"
                if disposition == "exclude"
                else "review"
            )
            category_counts[category] += 1
            native_origin = origin_row["origin"]
            origin = normalize_origin(native_origin)
            if origin is None:
                diagnostics.append(
                    Diagnostic(
                        code="origin-vocabulary-unmapped",
                        severity=Severity.ERROR,
                        message=f"Unmapped origin {native_origin!r} at {address}.",
                        source="config/function-origins.csv",
                    )
                )
            size = parse_int(row["size"], "size")
            subject_id = f"{product_id}:function:{address_component(address)}"
            extents = [Extent("pe-va", address, size)]
            owner = ownership.get(address)
            if owner:
                extents.extend(owner["extents"])
            mapping = mappings.get(address)
            display_name = (
                str(mapping["name"])
                if mapping is not None
                else row.get("proposed_name")
                or row.get("current_name")
                or address
            )
            subjects.append(
                Subject(
                    id=subject_id,
                    target_identity_id=target_id,
                    kind=SubjectKind.FUNCTION,
                    name=display_name,
                    extents=tuple(extents),
                    metadata={
                        "native_status": row.get("status", ""),
                        "module": row.get("module", ""),
                        "source_file": row.get("source_file", ""),
                        "current_name": row.get("current_name", ""),
                        "proposed_name": row.get("proposed_name", ""),
                    },
                )
            )
            claims.append(
                Claim(
                    id=f"claim:{subject_id}:boundary",
                    subject_id=subject_id,
                    type=ClaimType.BOUNDARY_EXTENT,
                    target_identity_id=target_id,
                    value={
                        "start": address,
                        "size": size,
                        "span_end": row.get("span_end", ""),
                        "state": "provisional-import",
                    },
                    evidence_class=EvidenceClass.INFERRED,
                    metadata={"native_evidence": row.get("evidence", "")},
                )
            )
            if origin is not None:
                claims.append(
                    Claim(
                        id=f"claim:{subject_id}:origin",
                        subject_id=subject_id,
                        type=ClaimType.ORIGIN_CLASSIFIED,
                        target_identity_id=target_id,
                        value={
                            "origin": origin.value,
                            "native_origin": native_origin,
                            "disposition": disposition,
                        },
                        evidence_class=normalize_evidence_class(origin_row["confidence"]),
                        evidence_refs=(origin_row["evidence_id"],)
                        if origin_row.get("evidence_id")
                        else (),
                    )
                )
            if mapping and display_name in implemented:
                claims.append(
                    Claim(
                        id=f"claim:{subject_id}:source-present",
                        subject_id=subject_id,
                        type=ClaimType.SOURCE_PRESENT,
                        target_identity_id=target_id,
                        value={"source_present": True, "mapping_name": display_name},
                        evidence_class=EvidenceClass.OBSERVED,
                        metadata={"mapping_type": mapping.get("type", "")},
                    )
                )
            if address in matches:
                match = matches[address]
                claims.append(
                    Claim(
                        id=f"claim:{subject_id}:codegen-exact",
                        subject_id=subject_id,
                        type=ClaimType.CODEGEN_EXACT,
                        target_identity_id=target_id,
                        toolchain_identity_id=toolchain.id,
                        value={
                            "exact": True,
                            "size": parse_int(match["size"], "match size"),
                            "match_percent": match.get("match_percent", ""),
                            "unit": match.get("unit", ""),
                        },
                        evidence_class=EvidenceClass.CORROBORATED,
                        metadata={"native_evidence": match.get("evidence", "")},
                    )
                )
                exact_bytes += _exact_owned_size(size, owner)
            if owner:
                claims.append(
                    Claim(
                        id=f"claim:{subject_id}:physical-ownership",
                        subject_id=subject_id,
                        type=ClaimType.PHYSICAL_OWNERSHIP,
                        target_identity_id=target_id,
                        value={
                            "owned_bytes": owner["owned_bytes"],
                            "main_excluded_bytes": owner["main_excluded_bytes"],
                            "remote_bytes": owner["remote_bytes"],
                            "remote_exact": owner["remote_exact"],
                        },
                        evidence_class=EvidenceClass.OBSERVED,
                        metadata={"native_evidence": owner["evidence"]},
                    )
                )
            if category == "authored":
                authored_bytes += owner["owned_bytes"] if owner else size
                remote_authored_bytes += owner["remote_bytes"] if owner else 0

        mapped_source_names = {
            str(row["name"])
            for row in mappings.values()
            if str(row["name"]) in implemented
        }
        unmapped_implemented = implemented - mapped_source_names
        if unmapped_implemented:
            raise AdapterError(
                f"implemented.csv contains {len(unmapped_implemented)} names "
                "absent from mapped functions"
            )

        metrics = [
            Metric("inventory.candidates", len(functions), project_id),
            Metric(
                "inventory.candidate-bytes",
                sum(parse_int(row["size"], "size") for row in functions.values()),
                project_id,
                unit="bytes",
            ),
            Metric("inventory.review", category_counts["review"], project_id),
            Metric("inventory.authored", category_counts["authored"], project_id),
            Metric("inventory.excluded", category_counts["excluded"], project_id),
            Metric("mapping.functions", len(mappings), project_id),
            Metric(
                "source.present-functions",
                len(mapped_source_names),
                project_id,
                total=category_counts["authored"],
            ),
            Metric(
                "exact.functions",
                len(matches),
                project_id,
                total=category_counts["authored"],
            ),
            Metric("exact.bytes", exact_bytes, project_id, unit="bytes"),
            Metric("build.configured-units", len(match_units), project_id),
        ]
        if ownership:
            metrics.extend(
                [
                    Metric(
                        "inventory.authored-bytes",
                        authored_bytes,
                        project_id,
                        unit="bytes",
                    ),
                    Metric(
                        "inventory.remote-authored-bytes",
                        remote_authored_bytes,
                        project_id,
                        unit="bytes",
                    ),
                    Metric(
                        "ownership.noncontiguous-functions",
                        len(ownership),
                        project_id,
                    ),
                ]
            )
        diagnostics.extend(
            [
                Diagnostic(
                    code="imported-exact-claims-unreplayed",
                    severity=Severity.INFO,
                    message=(
                        "Imported matches retain native evidence text but have no factory "
                        "OracleResult until cold replayed through a factory oracle envelope."
                    ),
                    source="config/matches.csv",
                ),
                Diagnostic(
                    code="whole-build-state-unattested",
                    severity=Severity.WARNING,
                    message=(
                        "No structured whole-build receipt exists in the imported ledgers; "
                        "the adapter does not infer closure from function exactness."
                    ),
                    source="config",
                ),
            ]
        )

        return RepositorySnapshot(
            project=project,
            products=(product,),
            targets=(target,),
            toolchains=(toolchain,),
            subjects=tuple(subjects),
            claims=tuple(claims),
            metrics=tuple(metrics),
            diagnostics=tuple(diagnostics),
            adapter_id=self.id,
            input_fingerprint_sha256=reader.fingerprint(imported_paths),
        )


def _address(raw: str) -> str:
    return canonical_address(raw)


def _toolchain_provider_id(data: dict[str, Any]) -> str:
    family = str(data.get("family", ""))
    lowered = family.lower()
    if "vc7.1" in lowered or "2003" in lowered:
        return "msvc71"
    if "vc7" in lowered or "2002" in lowered:
        return "msvc7"
    if "vc8" in lowered or "2005" in lowered:
        ltcg = data.get("rich_utc1400_ltcg_cpp")
        if ltcg is None or int(ltcg) <= 0:
            raise AdapterError(
                "VC8 target lacks positive LTCG evidence required by the reviewed profile"
            )
        return "msvc8-ltcg"
    raise AdapterError(f"unsupported Windows toolchain family: {family!r}")


def _load_ownership(
    manifest: dict[str, Any],
    target: TargetIdentity,
    functions: dict[str, dict[str, str]],
) -> dict[str, dict[str, Any]]:
    if manifest.get("schema_version") != 1:
        raise AdapterError(
            "function-byte-ownership.toml has an unsupported schema version"
        )
    if manifest.get("target_sha256") != target.sha256:
        raise AdapterError("function-byte-ownership.toml target SHA-256 mismatch")
    result: dict[str, dict[str, Any]] = {}
    numeric_starts = {int(address, 0) for address in functions}
    for index, row in enumerate(manifest.get("functions", []), start=1):
        context = f"function-byte-ownership.toml functions[{index}]"
        address = _address(str(row.get("address", "")))
        if address in result:
            raise AdapterError(f"{context}: duplicate function address")
        function = functions.get(address)
        if function is None:
            raise AdapterError(f"{context}: address is absent from functions.csv")
        main_size = int(row.get("main_size", 0))
        main_start = int(address, 0)
        main_end = int(str(row.get("main_end", "0")), 0)
        if main_size <= 0 or main_end != main_start + main_size - 1:
            raise AdapterError(f"{context}: inconsistent main extent")
        if parse_int(function["size"], "function size") != main_size:
            raise AdapterError(f"{context}: main size disagrees with functions.csv")

        extents: list[Extent] = []
        excluded = 0
        previous_exclusion_end = main_start - 1
        for raw in row.get("main_exclusions", []):
            start = int(str(raw["start"]), 0)
            end = int(str(raw["end"]), 0)
            size = int(raw["size"])
            if (
                start < main_start
                or end > main_end
                or start <= previous_exclusion_end
                or size != end - start + 1
            ):
                raise AdapterError(f"{context}: invalid or overlapping main exclusion")
            extents.append(
                Extent(
                    "pe-va",
                    canonical_address(str(raw["start"])),
                    size,
                    role=ExtentRole.EXCLUSION,
                    sha256=str(raw["sha256"]),
                )
            )
            excluded += size
            previous_exclusion_end = end
        if excluded != int(row.get("main_excluded_bytes", -1)):
            raise AdapterError(f"{context}: main excluded byte count mismatch")

        remote = 0
        previous_chunk_end = main_end
        chunks = row.get("chunks", [])
        for raw in chunks:
            start = int(str(raw["start"]), 0)
            end = int(str(raw["end"]), 0)
            size = int(raw["size"])
            if start <= previous_chunk_end or end < start or size != end - start + 1:
                raise AdapterError(f"{context}: invalid or overlapping remote chunk")
            intruders = sorted(
                value
                for value in numeric_starts
                if value != main_start and start <= value <= end
            )
            if intruders:
                raise AdapterError(
                    f"{context}: remote chunk overlaps another candidate start"
                )
            extents.append(
                Extent(
                    "pe-va",
                    canonical_address(str(raw["start"])),
                    size,
                    role=ExtentRole.OWNED_CHUNK,
                    sha256=str(raw["sha256"]),
                )
            )
            remote += size
            previous_chunk_end = end
        if not chunks or int(str(row.get("extent_end", "0")), 0) != previous_chunk_end:
            raise AdapterError(
                f"{context}: extent_end does not match the last remote chunk"
            )
        if remote != int(row.get("remote_bytes", -1)):
            raise AdapterError(f"{context}: remote byte count mismatch")
        owned = main_size - excluded + remote
        if owned != int(row.get("owned_bytes", -1)):
            raise AdapterError(f"{context}: owned byte count mismatch")
        remote_exact = bool(row.get("remote_exact", False))
        if remote_exact and not str(row.get("exact_evidence", "")).strip():
            raise AdapterError(f"{context}: remote_exact requires exact_evidence")
        result[address] = {
            "main_excluded_bytes": excluded,
            "remote_bytes": remote,
            "owned_bytes": owned,
            "remote_exact": remote_exact,
            "evidence": str(row.get("evidence", "")),
            "extents": tuple(extents),
        }
    return result


def _exact_owned_size(main_size: int, ownership: dict[str, Any] | None) -> int:
    if ownership is None:
        return main_size
    result = main_size - int(ownership["main_excluded_bytes"])
    if ownership["remote_exact"]:
        result += int(ownership["remote_bytes"])
    return result
