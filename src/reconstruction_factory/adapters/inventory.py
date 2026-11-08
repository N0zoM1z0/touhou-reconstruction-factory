"""Conservative imports for repositories with different native ledger contracts.

These adapters expose native target and provisional inventory information only.
Native acceptance files are deliberately not interpreted as Factory receipts.
"""

from pathlib import Path

from ..errors import AdapterError
from ..ontology import (
    Claim, ClaimType, Diagnostic, EvidenceClass, Extent, Product, Project,
    RepositorySnapshot, Severity, Subject, SubjectKind, TargetIdentity,
    ToolchainIdentity,
)
from .base import RepositoryAdapter, require_repository_root
from .common import RepositoryReader, canonical_address, canonical_digest, parse_int


class PeInventoryRepositoryAdapter(RepositoryAdapter):
    """Import PE inventory without guessing incompatible acceptance semantics."""

    id = "windows-pe-inventory-v1"
    games = {"th06", "th07", "th11", "th16", "th20", "efz"}
    _required = ("config/target.toml", "config/functions.csv", "config/tools.lock.toml")

    def detect(self, root: Path) -> bool:
        reader = RepositoryReader(root)
        if not all(reader.exists(path) for path in self._required):
            return False
        target = reader.toml("config/target.toml").get("target", {})
        return Path(str(target.get("filename", ""))).stem.lower() in self.games

    def inspect(self, root: Path) -> RepositorySnapshot:
        root = require_repository_root(root)
        reader = RepositoryReader(root)
        if not self.detect(root):
            raise AdapterError("unsupported PE inventory repository")
        manifest = reader.toml("config/target.toml")
        data, pe = manifest["target"], manifest["pe"]
        game = Path(data["filename"]).stem.lower()
        project = Project(id=game, name=data.get("title", game))
        target = TargetIdentity(
            id=f"target:{game}-main", project_id=game, product_id=f"{game}-main",
            game=game, version=data.get("version", "unknown"),
            region=data.get("region", "unknown"), format="pe",
            size=data["size"], sha256=data["sha256"], md5=data.get("md5"),
            canonicality="manifest-declared", metadata={
                **pe, "native_target": dict(data),
                "native_provenance": manifest.get("provenance", {}),
            },
        )
        toolchain_data = manifest.get("toolchain", {})
        toolchain = ToolchainIdentity(
            id=f"toolchain:{game}-native-candidate", project_id=game,
            provider_id="pe-inventory-only", family=toolchain_data.get("family", "unknown"),
            fingerprint_sha256=canonical_digest({
                "toolchain": toolchain_data, "tools": reader.toml("config/tools.lock.toml"),
            }), metadata={"execution_support": "not-established-by-inventory-import"},
        )
        subjects, claims, addresses = [], [], set()
        for row in reader.csv_dicts("config/functions.csv"):
            address = canonical_address(row["address"])
            if address in addresses:
                raise AdapterError("functions.csv contains duplicate addresses")
            addresses.add(address)
            size = parse_int(row["size"], "function size")
            if size < 0:
                raise AdapterError("function size cannot be negative")
            subject_id = f"{game}-main:function:{address[2:].lower()}"
            subjects.append(Subject(
                id=subject_id, target_identity_id=target.id, kind=SubjectKind.FUNCTION,
                name=row.get("proposed_name") or row.get("name") or row.get("current_name") or address,
                extents=(Extent(address_space="virtual-address", start=address, size=size),)
                if size else (), metadata={"native_row": dict(row)},
            ))
            claims.append(Claim(
                id=f"claim:{subject_id}:boundary", subject_id=subject_id,
                type=ClaimType.BOUNDARY_EXTENT, target_identity_id=target.id,
                value={"start": address, "size": size, "state": "provisional-import"},
                evidence_class=EvidenceClass.INFERRED,
            ))
        return RepositorySnapshot(
            project=project,
            products=(Product(id=target.product_id, project_id=game, role="gameplay",
                              target_identity_id=target.id),),
            targets=(target,), toolchains=(toolchain,), subjects=tuple(subjects),
            claims=tuple(claims), metrics=(), diagnostics=_diagnostics("config/functions.csv"),
            adapter_id=self.id, input_fingerprint_sha256=reader.fingerprint(self._required),
        )


class Th05ManifestRepositoryAdapter(RepositoryAdapter):
    """Expose TH05's four original targets without inventing function ledgers."""

    id = "th05-pc98-manifest-v1"
    _required = ("config/targets.toml", "config/toolchain.toml")

    def detect(self, root: Path) -> bool:
        reader = RepositoryReader(root)
        return all(reader.exists(p) for p in self._required) and any(
            a.get("game") == "th05" and a.get("role") == "reconstruction"
            for a in reader.toml("config/targets.toml").get("artifacts", [])
        )

    def inspect(self, root: Path) -> RepositorySnapshot:
        reader = RepositoryReader(require_repository_root(root))
        if not self.detect(root):
            raise AdapterError("unsupported TH05 target manifest")
        manifest = reader.toml("config/targets.toml")
        products, targets = [], []
        for item in manifest["artifacts"]:
            if item.get("game") != "th05":
                continue
            target_id = f"target:{item['id']}"
            products.append(Product(
                id=item["id"], project_id="th05", role=item.get("role", "unknown"),
                target_identity_id=target_id, required=item.get("required", True),
            ))
            targets.append(TargetIdentity(
                id=target_id, project_id="th05", product_id=item["id"], game="th05",
                version="unknown", region="japanese-local-attested", format=item["format"],
                size=item["size"], sha256=item["sha256"], md5=item.get("md5"),
                canonicality=manifest.get("source", {}).get("canonicality", "unknown"),
                metadata={"dos_path": item.get("dos_path", "")},
            ))
        exact = reader.toml("config/toolchain.toml").get("exact", {})
        toolchain = ToolchainIdentity(
            id="toolchain:th05-borland16", project_id="th05", provider_id="borland16",
            family=exact.get("family", "unknown"),
            fingerprint_sha256=canonical_digest(reader.toml("config/toolchain.toml")),
            metadata={"execution_support": "not-established-by-manifest-import"},
        )
        return RepositorySnapshot(
            project=Project(id="th05", name="Touhou 5 reconstruction"),
            products=tuple(products), targets=tuple(targets), toolchains=(toolchain,), subjects=(),
            claims=(), metrics=(), diagnostics=_diagnostics("config/targets.toml"),
            adapter_id=self.id, input_fingerprint_sha256=reader.fingerprint(self._required),
        )


def _diagnostics(source: str) -> tuple[Diagnostic, ...]:
    return (Diagnostic(
        code="inventory-import-only", severity=Severity.WARNING, source=source,
        message="Native acceptance, origins and source ledgers have not been imported; "
                "exactness and production closure remain unknown. Private target bytes "
                "are independently attested by the analysis provider, not this adapter.",
    ),)
