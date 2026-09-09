"""Machine-readable, scope-aware cross-game reconstruction knowledge."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
import re
from typing import Any

from .errors import RegressionFixtureError
from .regressions import HistoricalFixture, load_fixture_suite
from .ontology import to_primitive


KNOWLEDGE_SCHEMA_VERSION = 1
DEFAULT_KNOWLEDGE_CATALOG = Path(__file__).with_name("knowledge") / "catalog.json"
_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class KnowledgeStatus(str, Enum):
    VERIFIED = "verified"
    PROVISIONAL = "provisional"
    UNKNOWN = "unknown"
    SUPERSEDED = "superseded"


@dataclass(frozen=True, slots=True)
class KnowledgeEntry:
    id: str
    title: str
    status: KnowledgeStatus
    statement: str
    scopes: tuple[str, ...]
    evidence_fixture_ids: tuple[str, ...]
    consequences: tuple[str, ...]
    limitations: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)


@dataclass(frozen=True, slots=True)
class KnowledgeCatalog:
    entries: tuple[KnowledgeEntry, ...]
    schema_version: int = KNOWLEDGE_SCHEMA_VERSION

    def by_id(self, entry_id: str) -> KnowledgeEntry:
        for entry in self.entries:
            if entry.id == entry_id:
                return entry
        raise RegressionFixtureError(f"unknown knowledge entry: {entry_id}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "entry_count": len(self.entries),
            "status_counts": {
                status.value: sum(entry.status is status for entry in self.entries)
                for status in KnowledgeStatus
            },
            "entries": [entry.to_dict() for entry in self.entries],
        }


def _object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RegressionFixtureError(f"{context} must be a JSON object")
    return value


def _exact_keys(value: dict[str, Any], required: set[str], context: str) -> None:
    missing = required - value.keys()
    extra = value.keys() - required
    if missing:
        raise RegressionFixtureError(f"{context} is missing keys: {sorted(missing)}")
    if extra:
        raise RegressionFixtureError(f"{context} has unknown keys: {sorted(extra)}")


def _string(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RegressionFixtureError(f"{context} must be a non-empty string")
    return value


def _unique_strings(value: Any, context: str, *, nonempty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list) or (nonempty and not value):
        qualifier = "non-empty " if nonempty else ""
        raise RegressionFixtureError(f"{context} must be a {qualifier}list")
    result = tuple(_string(item, context) for item in value)
    if len(result) != len(set(result)):
        raise RegressionFixtureError(f"{context} must not contain duplicates")
    return result


def load_knowledge_catalog(
    path: Path | None = None,
    *,
    fixtures: tuple[HistoricalFixture, ...] | None = None,
) -> KnowledgeCatalog:
    """Load the catalog and verify every evidence edge against the fixture suite."""

    catalog_path = (path or DEFAULT_KNOWLEDGE_CATALOG).resolve()
    try:
        document = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RegressionFixtureError(f"cannot load knowledge catalog {catalog_path}: {error}") from error
    root = _object(document, str(catalog_path))
    _exact_keys(root, {"schema_version", "entries"}, str(catalog_path))
    if root["schema_version"] != KNOWLEDGE_SCHEMA_VERSION:
        raise RegressionFixtureError("unsupported knowledge catalog schema version")
    raw_entries = root["entries"]
    if not isinstance(raw_entries, list) or not raw_entries:
        raise RegressionFixtureError("knowledge catalog must contain entries")
    fixture_ids = {fixture.id for fixture in (fixtures or load_fixture_suite())}
    entries: list[KnowledgeEntry] = []
    seen: set[str] = set()
    required = {
        "id",
        "title",
        "status",
        "statement",
        "scopes",
        "evidence_fixture_ids",
        "consequences",
        "limitations",
    }
    for index, raw_entry in enumerate(raw_entries):
        context = f"knowledge.entries[{index}]"
        item = _object(raw_entry, context)
        _exact_keys(item, required, context)
        entry_id = _string(item["id"], f"{context}.id")
        if not _ID.fullmatch(entry_id) or entry_id in seen:
            raise RegressionFixtureError(f"invalid or duplicate knowledge id: {entry_id!r}")
        seen.add(entry_id)
        try:
            status = KnowledgeStatus(item["status"])
        except (TypeError, ValueError) as error:
            raise RegressionFixtureError(f"{context} has an unknown status") from error
        scopes = _unique_strings(item["scopes"], f"{context}.scopes", nonempty=True)
        if any(not _ID.fullmatch(scope) for scope in scopes):
            raise RegressionFixtureError(f"{context} has a non-canonical scope")
        evidence = _unique_strings(
            item["evidence_fixture_ids"], f"{context}.evidence_fixture_ids"
        )
        missing_evidence = set(evidence) - fixture_ids
        if missing_evidence:
            raise RegressionFixtureError(
                f"{context} references unknown fixtures: {sorted(missing_evidence)}"
            )
        consequences = _unique_strings(item["consequences"], f"{context}.consequences")
        limitations = _unique_strings(
            item["limitations"], f"{context}.limitations", nonempty=True
        )
        if status is KnowledgeStatus.VERIFIED and not evidence:
            raise RegressionFixtureError(f"verified entry {entry_id!r} requires fixture evidence")
        if status is KnowledgeStatus.UNKNOWN and consequences:
            raise RegressionFixtureError(
                f"unknown entry {entry_id!r} cannot impose verified consequences"
            )
        entries.append(
            KnowledgeEntry(
                id=entry_id,
                title=_string(item["title"], f"{context}.title"),
                status=status,
                statement=_string(item["statement"], f"{context}.statement"),
                scopes=scopes,
                evidence_fixture_ids=evidence,
                consequences=consequences,
                limitations=limitations,
            )
        )
    return KnowledgeCatalog(tuple(entries))
