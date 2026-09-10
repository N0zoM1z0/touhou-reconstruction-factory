"""Read-only, cross-game routing for source-shaped semantic debt.

The scanner deliberately reports lexical candidates rather than semantic
facts.  Its output helps an agent choose a bounded owner, field, or protocol
family; it never measures semantic completion and carries no exactness credit.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .errors import RepositoryWorkError


SEMANTIC_DEBT_SCHEMA_VERSION = 1
SEMANTIC_DEBT_PROFILE = "c-cpp-layout-heuristics-v1"
SEMANTIC_DEBT_CATEGORIES = (
    "raw-member-access",
    "absolute-address",
    "anonymous-identifier",
    "opaque-storage",
)

_SOURCE_SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".inl"}
_EXCLUDED_DIRECTORY_NAMES = {
    ".analysis",
    ".git",
    ".tools",
    "build",
    "generated",
    "ghidra-project",
}
_MAX_FILES = 10_000
_MAX_FILE_BYTES = 8 * 1024 * 1024
_MAX_TOTAL_BYTES = 64 * 1024 * 1024

_RAW_MEMBER_ACCESS = re.compile(
    r"(?:reinterpret_cast\s*<\s*(?:u8|i8|char|unsigned\s+char|std::byte)\s*\*>"
    r"|\(\s*(?:u8|i8|char|unsigned\s+char)\s*\*\s*\))"
    r"[^\n;]*?\+\s*0x[0-9a-f]+",
    re.IGNORECASE,
)
_ABSOLUTE_CAST = re.compile(
    r"reinterpret_cast\s*<[^>\n]+\*>\s*\(\s*0x[0-9a-f]+",
    re.IGNORECASE,
)
_ABSOLUTE_MACRO = re.compile(r"\bABS_(?:I|U|F)\d+\s*\(", re.IGNORECASE)
_ANONYMOUS_IDENTIFIER = re.compile(
    r"\b(?:"
    r"unk(?:nown)?(?:_?0x|_)?|"
    r"field(?:_?0x|_)?|"
    r"unused(?:_?0x|_)?|"
    r"padding(?:_?0x|_)?"
    r")[0-9a-f]{2,}\b",
    re.IGNORECASE,
)
_OPAQUE_STORAGE = re.compile(r"\bunknown_fields\s*\(")


@dataclass(frozen=True, slots=True)
class SemanticDebtFinding:
    category: str
    path: str
    line: int
    match: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def scan_semantic_debt(
    repository: Path,
    *,
    relative_path: str,
    category: str,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    """Scan one repository-relative source scope and return a bounded page."""

    if category != "all" and category not in SEMANTIC_DEBT_CATEGORIES:
        raise RepositoryWorkError("unknown semantic-debt category")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
        raise RepositoryWorkError("limit must be an integer from 1 through 100")
    if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
        raise RepositoryWorkError("offset must be a non-negative integer")

    scope = _safe_scope(repository, relative_path)
    paths, skipped_paths = _source_paths(repository, scope)
    findings: list[SemanticDebtFinding] = []
    scanned_files = 0
    scanned_bytes = 0
    non_utf8_paths: list[str] = []

    for path in paths:
        size = path.stat().st_size
        if size > _MAX_FILE_BYTES:
            skipped_paths.append(path.relative_to(repository).as_posix())
            continue
        if scanned_bytes + size > _MAX_TOTAL_BYTES:
            raise RepositoryWorkError(
                "semantic-debt scope exceeds the 64 MiB source scan limit"
            )
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            non_utf8_paths.append(path.relative_to(repository).as_posix())
            continue
        scanned_files += 1
        scanned_bytes += size
        for line_number, line in enumerate(lines, start=1):
            findings.extend(_line_findings(repository, path, line_number, line))

    findings.sort(key=lambda item: (item.path, item.line, item.category, item.match))
    all_counts = Counter(item.category for item in findings)
    selected = (
        findings if category == "all" else [item for item in findings if item.category == category]
    )
    file_counts = Counter(item.path for item in selected)
    page = selected[offset : offset + limit]
    report_identity = {
        "profile": SEMANTIC_DEBT_PROFILE,
        "scope": scope.relative_to(repository).as_posix(),
        "category": category,
        "findings": [item.to_dict() for item in selected],
    }
    return {
        "schema_version": SEMANTIC_DEBT_SCHEMA_VERSION,
        "scan_profile": SEMANTIC_DEBT_PROFILE,
        "scope": report_identity["scope"],
        "scope_complete": not skipped_paths and not non_utf8_paths,
        "files_scanned": scanned_files,
        "bytes_scanned": scanned_bytes,
        "skipped_paths": sorted(set(skipped_paths + non_utf8_paths)),
        "category": category,
        "category_counts": {
            name: all_counts.get(name, 0) for name in SEMANTIC_DEBT_CATEGORIES
        },
        "file_counts": dict(
            sorted(file_counts.items(), key=lambda item: (-item[1], item[0]))
        ),
        "routing_only": True,
        "completion_metric": False,
        "exactness_credit": "none",
        "semantic_evidence_credit": "none",
        "report_sha256": hashlib.sha256(
            json.dumps(report_identity, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "findings": {
            "total": len(selected),
            "offset": offset,
            "limit": limit,
            "next_offset": offset + len(page) if offset + len(page) < len(selected) else None,
            "items": [item.to_dict() for item in page],
        },
        "limitations": [
            "Lexical candidates include legitimate serialization, ABI, and opaque-storage code.",
            "The scanner does not find every numeric protocol, ownership, lifetime, or naming issue.",
            "Zero candidates means only zero matches under this profile and scope, not semantic completion.",
        ],
    }


def _safe_scope(repository: Path, relative_path: str) -> Path:
    if not isinstance(relative_path, str) or not relative_path or "\0" in relative_path:
        raise RepositoryWorkError("relative_path must be non-empty UTF-8 text")
    raw = Path(relative_path)
    if raw.is_absolute():
        raise RepositoryWorkError("relative_path must be repository-relative")
    try:
        scope = (repository / raw).resolve(strict=True)
    except OSError as error:
        raise RepositoryWorkError("semantic-debt scope does not exist") from error
    if not scope.is_relative_to(repository):
        raise RepositoryWorkError("semantic-debt scope must remain inside the repository")
    if not scope.is_file() and not scope.is_dir():
        raise RepositoryWorkError("semantic-debt scope must be a regular file or directory")
    return scope


def _source_paths(repository: Path, scope: Path) -> tuple[list[Path], list[str]]:
    discovered = [scope] if scope.is_file() else scope.rglob("*")
    paths: list[Path] = []
    skipped: list[str] = []
    for candidate in discovered:
        if not candidate.is_file() or candidate.suffix.lower() not in _SOURCE_SUFFIXES:
            continue
        try:
            path = candidate.resolve(strict=True)
        except OSError:
            skipped.append(candidate.relative_to(repository).as_posix())
            continue
        if not path.is_relative_to(repository):
            skipped.append(candidate.relative_to(repository).as_posix())
            continue
        relative = path.relative_to(repository)
        if any(part in _EXCLUDED_DIRECTORY_NAMES for part in relative.parts):
            continue
        paths.append(path)
        if len(paths) > _MAX_FILES:
            raise RepositoryWorkError(
                "semantic-debt scope exceeds the 10000-source-file scan limit"
            )
    return sorted(set(paths)), skipped


def _line_findings(
    repository: Path, path: Path, line_number: int, line: str
) -> list[SemanticDebtFinding]:
    relative = path.relative_to(repository).as_posix()
    findings: list[SemanticDebtFinding] = []
    patterns = (
        ("raw-member-access", _RAW_MEMBER_ACCESS),
        ("absolute-address", _ABSOLUTE_CAST),
        ("anonymous-identifier", _ANONYMOUS_IDENTIFIER),
        ("opaque-storage", _OPAQUE_STORAGE),
    )
    for category, pattern in patterns:
        for match in pattern.finditer(line):
            findings.append(
                SemanticDebtFinding(
                    category=category,
                    path=relative,
                    line=line_number,
                    match=match.group(0).strip(),
                )
            )
    if not line.lstrip().startswith("#define"):
        for match in _ABSOLUTE_MACRO.finditer(line):
            findings.append(
                SemanticDebtFinding(
                    category="absolute-address",
                    path=relative,
                    line=line_number,
                    match=match.group(0).strip(),
                )
            )
    return findings
