"""Safe readers and normalization helpers shared by repository adapters."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path
import re
import tomllib
from typing import Any, Iterable

from ..errors import AdapterError
from ..ontology import EvidenceClass, OriginKind


_SAFE_COMPONENT = re.compile(r"[^a-z0-9._:-]+")


class RepositoryReader:
    """Read files beneath one real repository root and reject symlink escapes."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve(strict=True)

    def path(self, relative: str) -> Path:
        candidate = Path(relative)
        if candidate.is_absolute():
            raise AdapterError(f"adapter path must be relative: {relative}")
        try:
            resolved = (self.root / candidate).resolve(strict=True)
        except FileNotFoundError as error:
            raise AdapterError(f"required adapter input is missing: {relative}") from error
        if not resolved.is_relative_to(self.root):
            raise AdapterError(f"adapter input escapes repository root: {relative}")
        if not resolved.is_file():
            raise AdapterError(f"adapter input is not a file: {relative}")
        return resolved

    def exists(self, relative: str) -> bool:
        candidate = self.root / relative
        try:
            resolved = candidate.resolve(strict=True)
        except FileNotFoundError:
            return False
        return resolved.is_relative_to(self.root) and resolved.is_file()

    def bytes(self, relative: str) -> bytes:
        return self.path(relative).read_bytes()

    def toml(self, relative: str) -> dict[str, Any]:
        try:
            return tomllib.loads(self.bytes(relative).decode("utf-8"))
        except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
            raise AdapterError(f"invalid TOML input {relative}: {error}") from error

    def csv_dicts(self, relative: str) -> list[dict[str, str]]:
        try:
            text = self.bytes(relative).decode("utf-8-sig")
            return list(csv.DictReader(io.StringIO(text, newline="")))
        except (UnicodeDecodeError, csv.Error) as error:
            raise AdapterError(f"invalid CSV input {relative}: {error}") from error

    def csv_column(self, relative: str) -> list[str]:
        try:
            text = self.bytes(relative).decode("utf-8-sig")
            return [row[0] for row in csv.reader(io.StringIO(text, newline="")) if row]
        except (UnicodeDecodeError, csv.Error, IndexError) as error:
            raise AdapterError(f"invalid one-column CSV input {relative}: {error}") from error

    def fingerprint(self, relatives: Iterable[str]) -> str:
        digest = hashlib.sha256()
        for relative in sorted(set(relatives)):
            payload = self.bytes(relative)
            digest.update(relative.encode("utf-8"))
            digest.update(b"\0")
            digest.update(len(payload).to_bytes(8, "big"))
            digest.update(payload)
        return digest.hexdigest()


def canonical_digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def canonical_address(raw: str) -> str:
    try:
        return f"0x{int(raw, 0):08X}"
    except ValueError as error:
        raise AdapterError(f"invalid address: {raw!r}") from error


def address_component(raw: str) -> str:
    return canonical_address(raw)[2:].lower()


def safe_component(raw: str) -> str:
    value = _SAFE_COMPONENT.sub("-", raw.strip().lower()).strip("-")
    if not value:
        raise AdapterError(f"cannot derive a stable identifier from {raw!r}")
    return value


def parse_int(raw: object, field_name: str) -> int:
    try:
        return int(str(raw), 0)
    except ValueError as error:
        raise AdapterError(f"invalid integer for {field_name}: {raw!r}") from error


def normalize_origin(raw: str) -> OriginKind | None:
    return {
        "authored": OriginKind.AUTHORED_GAME,
        "authored_game": OriginKind.AUTHORED_GAME,
        "compiler": OriginKind.COMPILER_GENERATED,
        "compiler_generated": OriginKind.COMPILER_GENERATED,
        "library": OriginKind.LIBRARY,
        "vc8_runtime": OriginKind.LIBRARY,
        "third_party": OriginKind.THIRD_PARTY,
        "import_thunk": OriginKind.IMPORT_THUNK,
        "original-asm": OriginKind.ORIGINAL_ASSEMBLY,
        "data": OriginKind.DATA,
        "padding": OriginKind.PADDING,
        "unknown": OriginKind.UNKNOWN,
        "": OriginKind.UNKNOWN,
    }.get(raw)


def normalize_evidence_class(raw: str) -> EvidenceClass:
    return {
        "observed": EvidenceClass.OBSERVED,
        "corroborated": EvidenceClass.CORROBORATED,
        "exact": EvidenceClass.CORROBORATED,
        "high": EvidenceClass.CORROBORATED,
        "inferred": EvidenceClass.INFERRED,
        "provisional": EvidenceClass.INFERRED,
        "unknown": EvidenceClass.UNKNOWN,
        "": EvidenceClass.UNKNOWN,
    }.get(raw, EvidenceClass.UNKNOWN)
