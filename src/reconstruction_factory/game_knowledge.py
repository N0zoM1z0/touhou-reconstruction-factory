"""Fail-closed input contract for knowledge owned by one game repository."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any

from .errors import GameKnowledgeError
from .ontology import to_primitive


GAME_KNOWLEDGE_SCHEMA_VERSION = 1
GAME_KNOWLEDGE_DOCUMENT_TYPE = "game-knowledge-input"
GAME_KNOWLEDGE_AUTHORITY = "game-local"
GAME_KNOWLEDGE_FACTORY_PUBLICATION = "none"
GAME_KNOWLEDGE_SCHEMA_URI = (
    "https://github.com/N0zoM1z0/touhou-reconstruction-factory/"
    "schemas/v1/game-knowledge-input.schema.json"
)
DEFAULT_GAME_KNOWLEDGE_PATH = Path(".reconstruction/game-knowledge.json")

_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_SCOPE = re.compile(r"^(game|target|subsystem):[a-z0-9][a-z0-9:._-]*$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_RECEIPT = re.compile(r"^receipt:[0-9a-f]{64}$")


class GameKnowledgeKind(str, Enum):
    SCOPED_FACT = "scoped-fact"
    RECIPE = "recipe"
    PITFALL = "pitfall"
    DECISION = "decision"
    UNKNOWN = "unknown"


class GameKnowledgeStatus(str, Enum):
    OBSERVED = "observed"
    REPRODUCED = "reproduced"
    UNKNOWN = "unknown"
    SUPERSEDED = "superseded"


class GameEvidenceKind(str, Enum):
    REPOSITORY_PATH = "repository-path"
    COMMIT = "commit"
    ANALYSIS_OBSERVATION = "analysis-observation"
    ACCEPTED_RECEIPT = "accepted-receipt"
    EXTERNAL_REFERENCE = "external-reference"


class GameValidationResult(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class GameEvidence:
    kind: GameEvidenceKind
    reference: str
    note: str


@dataclass(frozen=True, slots=True)
class GameValidation:
    method: str
    result: GameValidationResult
    note: str


@dataclass(frozen=True, slots=True)
class GameKnowledgeEntry:
    id: str
    kind: GameKnowledgeKind
    status: GameKnowledgeStatus
    statement: str
    scopes: tuple[str, ...]
    evidence: tuple[GameEvidence, ...]
    validations: tuple[GameValidation, ...]
    limitations: tuple[str, ...]
    superseded_by: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GameKnowledgeInput:
    repository_id: str
    entries: tuple[GameKnowledgeEntry, ...]
    schema_version: int = GAME_KNOWLEDGE_SCHEMA_VERSION
    document_type: str = GAME_KNOWLEDGE_DOCUMENT_TYPE
    authority: str = GAME_KNOWLEDGE_AUTHORITY
    factory_publication: str = GAME_KNOWLEDGE_FACTORY_PUBLICATION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "document_type": self.document_type,
            "authority": self.authority,
            "factory_publication": self.factory_publication,
            "repository_id": self.repository_id,
            "entry_count": len(self.entries),
            "status_counts": {
                status.value: sum(entry.status is status for entry in self.entries)
                for status in GameKnowledgeStatus
            },
            "entries": [to_primitive(entry) for entry in self.entries],
        }


def _object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise GameKnowledgeError(f"{context} must be a JSON object")
    return value


def _exact_keys(
    value: dict[str, Any],
    required: set[str],
    context: str,
    *,
    optional: set[str] | None = None,
) -> None:
    optional = optional or set()
    missing = required - value.keys()
    extra = value.keys() - required - optional
    if missing:
        raise GameKnowledgeError(f"{context} is missing keys: {sorted(missing)}")
    if extra:
        raise GameKnowledgeError(f"{context} has unknown keys: {sorted(extra)}")


def _string(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise GameKnowledgeError(f"{context} must be a trimmed non-empty string")
    return value


def _identifier(value: Any, context: str) -> str:
    result = _string(value, context)
    if not _ID.fullmatch(result):
        raise GameKnowledgeError(f"{context} must be a normalized identifier")
    return result


def _unique_strings(
    value: Any, context: str, *, nonempty: bool = False, sorted_values: bool = False
) -> tuple[str, ...]:
    if not isinstance(value, list) or (nonempty and not value):
        qualifier = "non-empty " if nonempty else ""
        raise GameKnowledgeError(f"{context} must be a {qualifier}list")
    result = tuple(_string(item, context) for item in value)
    if len(result) != len(set(result)):
        raise GameKnowledgeError(f"{context} must not contain duplicates")
    if sorted_values and result != tuple(sorted(result)):
        raise GameKnowledgeError(f"{context} must be sorted")
    return result


def _contained_path(reference: str, context: str) -> PurePosixPath:
    if "\\" in reference:
        raise GameKnowledgeError(f"{context} must use POSIX separators")
    path = PurePosixPath(reference)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise GameKnowledgeError(f"{context} must be a contained repository-relative path")
    return path


def _load_evidence(
    value: Any,
    context: str,
    repository_root: Path | None,
) -> tuple[GameEvidence, ...]:
    if not isinstance(value, list):
        raise GameKnowledgeError(f"{context} must be a list")
    result: list[GameEvidence] = []
    seen: set[tuple[GameEvidenceKind, str]] = set()
    for index, raw in enumerate(value):
        item_context = f"{context}[{index}]"
        item = _object(raw, item_context)
        _exact_keys(item, {"kind", "reference", "note"}, item_context)
        try:
            kind = GameEvidenceKind(item["kind"])
        except (TypeError, ValueError) as error:
            raise GameKnowledgeError(f"{item_context}.kind is unsupported") from error
        reference = _string(item["reference"], f"{item_context}.reference")
        if kind is GameEvidenceKind.REPOSITORY_PATH:
            relative = _contained_path(reference, f"{item_context}.reference")
            if repository_root is not None:
                try:
                    candidate = (repository_root / Path(*relative.parts)).resolve(strict=True)
                except FileNotFoundError as error:
                    raise GameKnowledgeError(
                        f"{item_context}.reference does not exist in the repository"
                    ) from error
                if not candidate.is_relative_to(repository_root) or not candidate.is_file():
                    raise GameKnowledgeError(
                        f"{item_context}.reference is not a contained regular file"
                    )
        elif kind is GameEvidenceKind.COMMIT and not _COMMIT.fullmatch(reference):
            raise GameKnowledgeError(f"{item_context}.reference must be a full Git commit")
        elif kind is GameEvidenceKind.ACCEPTED_RECEIPT and not _RECEIPT.fullmatch(reference):
            raise GameKnowledgeError(
                f"{item_context}.reference must be a canonical receipt ID"
            )
        elif kind is GameEvidenceKind.EXTERNAL_REFERENCE and not reference.startswith(
            ("https://", "http://")
        ):
            raise GameKnowledgeError(f"{item_context}.reference must be an HTTP(S) URL")
        key = (kind, reference)
        if key in seen:
            raise GameKnowledgeError(f"{context} must not contain duplicate evidence")
        seen.add(key)
        result.append(
            GameEvidence(
                kind=kind,
                reference=reference,
                note=_string(item["note"], f"{item_context}.note"),
            )
        )
    return tuple(result)


def _load_validations(value: Any, context: str) -> tuple[GameValidation, ...]:
    if not isinstance(value, list):
        raise GameKnowledgeError(f"{context} must be a list")
    result: list[GameValidation] = []
    seen: set[tuple[str, GameValidationResult, str]] = set()
    for index, raw in enumerate(value):
        item_context = f"{context}[{index}]"
        item = _object(raw, item_context)
        _exact_keys(item, {"method", "result", "note"}, item_context)
        try:
            validation_result = GameValidationResult(item["result"])
        except (TypeError, ValueError) as error:
            raise GameKnowledgeError(f"{item_context}.result is unsupported") from error
        validation = GameValidation(
            method=_string(item["method"], f"{item_context}.method"),
            result=validation_result,
            note=_string(item["note"], f"{item_context}.note"),
        )
        key = (validation.method, validation.result, validation.note)
        if key in seen:
            raise GameKnowledgeError(f"{context} must not contain duplicate validations")
        seen.add(key)
        result.append(validation)
    return tuple(result)


def _check_supersession(entries: tuple[GameKnowledgeEntry, ...]) -> None:
    by_id = {entry.id: entry for entry in entries}
    for entry in entries:
        missing = set(entry.superseded_by) - by_id.keys()
        if missing:
            raise GameKnowledgeError(
                f"entry {entry.id!r} references unknown superseding entries: {sorted(missing)}"
            )
        if entry.id in entry.superseded_by:
            raise GameKnowledgeError(f"entry {entry.id!r} cannot supersede itself")

    def visit(entry_id: str, active: set[str], complete: set[str]) -> None:
        if entry_id in active:
            raise GameKnowledgeError("game knowledge supersession graph contains a cycle")
        if entry_id in complete:
            return
        active.add(entry_id)
        for successor in by_id[entry_id].superseded_by:
            visit(successor, active, complete)
        active.remove(entry_id)
        complete.add(entry_id)

    complete: set[str] = set()
    for entry in entries:
        visit(entry.id, set(), complete)


def load_game_knowledge(
    path: Path,
    *,
    repository_root: Path | None = None,
    expected_repository_id: str | None = None,
) -> GameKnowledgeInput:
    """Load one game-local input without granting Factory publication authority."""

    document_path = path.expanduser().resolve(strict=True)
    root_path = repository_root.expanduser().resolve(strict=True) if repository_root else None
    if root_path is not None and not root_path.is_dir():
        raise GameKnowledgeError("repository_root must be a directory")
    try:
        document = json.loads(document_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise GameKnowledgeError(f"cannot load game knowledge {document_path}: {error}") from error
    root = _object(document, str(document_path))
    required = {
        "schema_version",
        "document_type",
        "authority",
        "factory_publication",
        "repository_id",
        "entries",
    }
    _exact_keys(root, required, str(document_path), optional={"$schema"})
    if "$schema" in root and root["$schema"] != GAME_KNOWLEDGE_SCHEMA_URI:
        raise GameKnowledgeError("game knowledge $schema URI is unsupported")
    if (
        not isinstance(root["schema_version"], int)
        or isinstance(root["schema_version"], bool)
        or root["schema_version"] != GAME_KNOWLEDGE_SCHEMA_VERSION
    ):
        raise GameKnowledgeError("unsupported game knowledge schema version")
    if root["document_type"] != GAME_KNOWLEDGE_DOCUMENT_TYPE:
        raise GameKnowledgeError("document_type must identify game-local knowledge input")
    if root["authority"] != GAME_KNOWLEDGE_AUTHORITY:
        raise GameKnowledgeError("game knowledge authority must remain game-local")
    if root["factory_publication"] != GAME_KNOWLEDGE_FACTORY_PUBLICATION:
        raise GameKnowledgeError("game knowledge cannot request Factory publication")
    repository_id = _identifier(root["repository_id"], "repository_id")
    expected_id = (
        _identifier(expected_repository_id, "expected_repository_id")
        if expected_repository_id is not None
        else None
    )
    if expected_id is not None and repository_id != expected_id:
        raise GameKnowledgeError(
            f"repository_id mismatch: expected {expected_id!r}, observed {repository_id!r}"
        )
    raw_entries = root["entries"]
    if not isinstance(raw_entries, list):
        raise GameKnowledgeError("entries must be a list")
    entries: list[GameKnowledgeEntry] = []
    seen: set[str] = set()
    required_entry_keys = {
        "id",
        "kind",
        "status",
        "statement",
        "scopes",
        "evidence",
        "validations",
        "limitations",
        "superseded_by",
    }
    for index, raw_entry in enumerate(raw_entries):
        context = f"entries[{index}]"
        item = _object(raw_entry, context)
        _exact_keys(item, required_entry_keys, context)
        entry_id = _identifier(item["id"], f"{context}.id")
        if entry_id in seen:
            raise GameKnowledgeError(f"duplicate game knowledge entry: {entry_id}")
        seen.add(entry_id)
        try:
            kind = GameKnowledgeKind(item["kind"])
            status = GameKnowledgeStatus(item["status"])
        except (TypeError, ValueError) as error:
            raise GameKnowledgeError(f"{context} has an unsupported kind or status") from error
        if status is GameKnowledgeStatus.UNKNOWN and kind is not GameKnowledgeKind.UNKNOWN:
            raise GameKnowledgeError(
                f"{context} unknown status requires unknown kind"
            )
        if kind is GameKnowledgeKind.UNKNOWN and status not in {
            GameKnowledgeStatus.UNKNOWN,
            GameKnowledgeStatus.SUPERSEDED,
        }:
            raise GameKnowledgeError(
                f"{context} unknown kind must remain unknown or superseded"
            )
        scopes = _unique_strings(
            item["scopes"], f"{context}.scopes", nonempty=True, sorted_values=True
        )
        if any(not _SCOPE.fullmatch(scope) for scope in scopes):
            raise GameKnowledgeError(
                f"{context}.scopes may contain only normalized game, target, or subsystem scopes"
            )
        game_scopes = tuple(scope for scope in scopes if scope.startswith("game:"))
        if game_scopes != (f"game:{repository_id}",):
            raise GameKnowledgeError(
                f"{context}.scopes must contain exactly game:{repository_id} as its game scope"
            )
        evidence = _load_evidence(item["evidence"], f"{context}.evidence", root_path)
        validations = _load_validations(item["validations"], f"{context}.validations")
        limitations = _unique_strings(
            item["limitations"], f"{context}.limitations", nonempty=True
        )
        superseded_by = _unique_strings(
            item["superseded_by"], f"{context}.superseded_by", sorted_values=True
        )
        if status is GameKnowledgeStatus.SUPERSEDED and not superseded_by:
            raise GameKnowledgeError(f"{context} requires superseded_by")
        if status is not GameKnowledgeStatus.SUPERSEDED and superseded_by:
            raise GameKnowledgeError(f"{context} cannot be superseded_by while active")
        if status not in {GameKnowledgeStatus.UNKNOWN, GameKnowledgeStatus.SUPERSEDED} and not evidence:
            raise GameKnowledgeError(f"{context} requires evidence")
        if status is GameKnowledgeStatus.REPRODUCED and not any(
            check.result is GameValidationResult.PASSED for check in validations
        ):
            raise GameKnowledgeError(f"{context} reproduced status requires a passing validation")
        entries.append(
            GameKnowledgeEntry(
                id=entry_id,
                kind=kind,
                status=status,
                statement=_string(item["statement"], f"{context}.statement"),
                scopes=scopes,
                evidence=evidence,
                validations=validations,
                limitations=limitations,
                superseded_by=superseded_by,
            )
        )
    if tuple(entry.id for entry in entries) != tuple(sorted(entry.id for entry in entries)):
        raise GameKnowledgeError("entries must be sorted by id")
    result = GameKnowledgeInput(repository_id=repository_id, entries=tuple(entries))
    _check_supersession(result.entries)
    return result
