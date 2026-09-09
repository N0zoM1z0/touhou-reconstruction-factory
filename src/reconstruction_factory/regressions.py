"""Fail-closed evaluators for provenance-backed historical regressions.

Fixtures capture small, non-copyrightable facts from immutable repository
commits.  They are executable counterexamples to tempting but invalid
inferences, such as treating a decompiler boundary as complete or treating a
successful function replay as whole-program link closure.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Callable, Mapping

from .errors import RegressionFixtureError
from .ontology import Verdict, to_primitive


FIXTURE_SCHEMA_VERSION = 1
DEFAULT_FIXTURE_DIRECTORY = Path(__file__).with_name("historical_fixtures")
_MANIFEST_NAME = "manifest.json"
_FIXTURE_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_HEX = re.compile(r"^(?:[0-9a-f]{2})+$")
_ADDRESS = re.compile(r"^0x[0-9A-Fa-f]+$")
_FIXTURE_FILE = re.compile(r"^[a-z0-9][a-z0-9-]*\.json$")


class RegressionContract(str, Enum):
    BOUNDARY_COVERAGE = "boundary-coverage"
    RELOCATION_DESTINATION_CONTENT = "relocation-destination-content"
    WHOLE_BUILD_CLOSURE = "whole-build-closure"
    TARGET_BINDING = "target-binding"
    OWNED_EXTENT_EXACTNESS = "owned-extent-exactness"


@dataclass(frozen=True, slots=True)
class FixtureProvenance:
    repository: str
    commit: str
    paths: tuple[str, ...]
    observation: str


@dataclass(frozen=True, slots=True)
class HistoricalFixture:
    id: str
    title: str
    project: str
    contract: RegressionContract
    provenance: FixtureProvenance
    input: Mapping[str, Any]
    expected_verdict: Verdict
    expected_diagnostics: tuple[str, ...]
    schema_version: int = FIXTURE_SCHEMA_VERSION


@dataclass(frozen=True, slots=True)
class RegressionOutcome:
    verdict: Verdict
    diagnostics: tuple[str, ...]
    facts: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)


@dataclass(frozen=True, slots=True)
class FixtureEvaluation:
    fixture_id: str
    project: str
    contract: RegressionContract
    expected_verdict: Verdict
    expected_diagnostics: tuple[str, ...]
    outcome: RegressionOutcome

    @property
    def matched(self) -> bool:
        return (
            self.outcome.verdict is self.expected_verdict
            and self.outcome.diagnostics == self.expected_diagnostics
        )

    def to_dict(self) -> dict[str, Any]:
        result = to_primitive(self)
        result["matched"] = self.matched
        return result


@dataclass(frozen=True, slots=True)
class RegressionSuiteReport:
    evaluations: tuple[FixtureEvaluation, ...]

    @property
    def passed(self) -> bool:
        return all(item.matched for item in self.evaluations)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "fixture_count": len(self.evaluations),
            "evaluations": [item.to_dict() for item in self.evaluations],
        }


def _object(value: Any, context: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise RegressionFixtureError(f"{context} must be a JSON object")
    return value


def _exact_keys(
    value: Mapping[str, Any],
    *,
    required: set[str],
    optional: set[str] = frozenset(),
    context: str,
) -> None:
    missing = required - value.keys()
    extra = value.keys() - required - optional
    if missing:
        raise RegressionFixtureError(f"{context} is missing keys: {sorted(missing)}")
    if extra:
        raise RegressionFixtureError(f"{context} has unknown keys: {sorted(extra)}")


def _string(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RegressionFixtureError(f"{context} must be a non-empty string")
    return value


def _integer(value: Any, context: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise RegressionFixtureError(f"{context} must be an integer >= {minimum}")
    return value


def _boolean(value: Any, context: str) -> bool:
    if type(value) is not bool:
        raise RegressionFixtureError(f"{context} must be a boolean")
    return value


def _address(value: Any, context: str) -> str:
    text = _string(value, context)
    if not _ADDRESS.fullmatch(text):
        raise RegressionFixtureError(f"{context} must be a hexadecimal address")
    return text


def _data_hex(value: Any, context: str) -> str | None:
    if value is None:
        return None
    text = _string(value, context)
    if not _HEX.fullmatch(text):
        raise RegressionFixtureError(
            f"{context} must contain an even number of lowercase hexadecimal digits"
        )
    return text


def _sha256(value: Any, context: str) -> str:
    text = _string(value, context)
    if not _SHA256.fullmatch(text):
        raise RegressionFixtureError(f"{context} must be a lowercase SHA-256 digest")
    return text


def load_fixture(path: Path) -> HistoricalFixture:
    """Load one fixture with strict envelope and provenance validation."""

    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RegressionFixtureError(f"cannot load fixture {path}: {error}") from error
    root = _object(document, str(path))
    _exact_keys(
        root,
        required={
            "schema_version",
            "id",
            "title",
            "project",
            "contract",
            "provenance",
            "input",
            "expected",
        },
        optional={"$schema"},
        context=str(path),
    )
    if root["schema_version"] != FIXTURE_SCHEMA_VERSION:
        raise RegressionFixtureError(
            f"{path}: unsupported schema_version {root['schema_version']!r}"
        )
    fixture_id = _string(root["id"], f"{path}.id")
    if not _FIXTURE_ID.fullmatch(fixture_id):
        raise RegressionFixtureError(f"{path}.id is not canonical: {fixture_id!r}")
    if path.name != f"{fixture_id}.json":
        raise RegressionFixtureError(f"fixture id {fixture_id!r} does not match {path.name!r}")

    provenance = _object(root["provenance"], f"{fixture_id}.provenance")
    _exact_keys(
        provenance,
        required={"repository", "commit", "paths", "observation"},
        context=f"{fixture_id}.provenance",
    )
    commit = _string(provenance["commit"], f"{fixture_id}.provenance.commit")
    if not _COMMIT.fullmatch(commit):
        raise RegressionFixtureError(f"{fixture_id}: provenance commit must be a full Git hash")
    raw_paths = provenance["paths"]
    if not isinstance(raw_paths, list) or not raw_paths:
        raise RegressionFixtureError(f"{fixture_id}: provenance paths must be a non-empty list")
    paths: list[str] = []
    for index, raw_path in enumerate(raw_paths):
        source_path = _string(raw_path, f"{fixture_id}.provenance.paths[{index}]")
        parsed = Path(source_path)
        if parsed.is_absolute() or ".." in parsed.parts:
            raise RegressionFixtureError(f"{fixture_id}: provenance paths must be repository-relative")
        paths.append(source_path)

    expected = _object(root["expected"], f"{fixture_id}.expected")
    _exact_keys(
        expected,
        required={"verdict", "diagnostics"},
        context=f"{fixture_id}.expected",
    )
    raw_diagnostics = expected["diagnostics"]
    if not isinstance(raw_diagnostics, list):
        raise RegressionFixtureError(f"{fixture_id}: expected diagnostics must be a list")
    diagnostics = tuple(
        _string(item, f"{fixture_id}.expected.diagnostics") for item in raw_diagnostics
    )
    if len(set(diagnostics)) != len(diagnostics):
        raise RegressionFixtureError(f"{fixture_id}: expected diagnostics must be unique")
    try:
        contract = RegressionContract(root["contract"])
        verdict = Verdict(expected["verdict"])
    except (TypeError, ValueError) as error:
        raise RegressionFixtureError(f"{fixture_id}: unknown contract or verdict") from error

    return HistoricalFixture(
        id=fixture_id,
        title=_string(root["title"], f"{fixture_id}.title"),
        project=_string(root["project"], f"{fixture_id}.project"),
        contract=contract,
        provenance=FixtureProvenance(
            repository=_string(
                provenance["repository"], f"{fixture_id}.provenance.repository"
            ),
            commit=commit,
            paths=tuple(paths),
            observation=_string(
                provenance["observation"], f"{fixture_id}.provenance.observation"
            ),
        ),
        input=_object(root["input"], f"{fixture_id}.input"),
        expected_verdict=verdict,
        expected_diagnostics=diagnostics,
    )


def load_fixture_suite(directory: Path | None = None) -> tuple[HistoricalFixture, ...]:
    """Load the complete hash-pinned fixture set from a manifest."""

    fixture_directory = (directory or DEFAULT_FIXTURE_DIRECTORY).resolve()
    manifest_path = fixture_directory / _MANIFEST_NAME
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RegressionFixtureError(f"cannot load fixture manifest {manifest_path}: {error}") from error
    root = _object(manifest, str(manifest_path))
    _exact_keys(
        root,
        required={"schema_version", "fixtures"},
        context=str(manifest_path),
    )
    if root["schema_version"] != FIXTURE_SCHEMA_VERSION:
        raise RegressionFixtureError(f"unsupported fixture manifest schema version")
    raw_entries = root["fixtures"]
    if not isinstance(raw_entries, list) or not raw_entries:
        raise RegressionFixtureError("fixture manifest must contain at least one entry")

    paths: list[Path] = []
    seen: set[str] = set()
    for index, raw_entry in enumerate(raw_entries):
        entry = _object(raw_entry, f"manifest.fixtures[{index}]")
        _exact_keys(
            entry,
            required={"path", "sha256"},
            context=f"manifest.fixtures[{index}]",
        )
        name = _string(entry["path"], f"manifest.fixtures[{index}].path")
        if not _FIXTURE_FILE.fullmatch(name) or name == _MANIFEST_NAME:
            raise RegressionFixtureError(f"manifest fixture path is not a safe basename: {name!r}")
        if name in seen:
            raise RegressionFixtureError(f"duplicate fixture manifest path: {name}")
        seen.add(name)
        expected_hash = _sha256(entry["sha256"], f"manifest.fixtures[{index}].sha256")
        path = fixture_directory / name
        try:
            content = path.read_bytes()
        except OSError as error:
            raise RegressionFixtureError(f"cannot read fixture {path}: {error}") from error
        actual_hash = hashlib.sha256(content).hexdigest()
        if actual_hash != expected_hash:
            raise RegressionFixtureError(
                f"fixture digest mismatch for {name}: expected {expected_hash}, got {actual_hash}"
            )
        paths.append(path)

    present = {path.name for path in fixture_directory.glob("*.json")} - {_MANIFEST_NAME}
    if present != seen:
        raise RegressionFixtureError(
            f"fixture manifest coverage mismatch: manifest={sorted(seen)}, present={sorted(present)}"
        )
    fixtures = tuple(load_fixture(path) for path in paths)
    ids = [fixture.id for fixture in fixtures]
    if len(ids) != len(set(ids)):
        raise RegressionFixtureError("fixture ids must be unique across the suite")
    return fixtures


def _boundary_coverage(data: Mapping[str, Any]) -> RegressionOutcome:
    _exact_keys(
        data,
        required={"candidate_start", "candidate_size", "accepted_start", "accepted_size"},
        context="boundary-coverage input",
    )
    candidate_start = _address(data["candidate_start"], "candidate_start")
    accepted_start = _address(data["accepted_start"], "accepted_start")
    candidate_size = _integer(data["candidate_size"], "candidate_size", minimum=1)
    accepted_size = _integer(data["accepted_size"], "accepted_size", minimum=1)
    facts = {
        "candidate_size": candidate_size,
        "accepted_size": accepted_size,
        "uncovered_bytes": max(accepted_size - candidate_size, 0),
    }
    if int(candidate_start, 16) != int(accepted_start, 16):
        return RegressionOutcome(Verdict.FAIL, ("boundary-start-mismatch",), facts)
    if candidate_size < accepted_size:
        return RegressionOutcome(Verdict.INCOMPLETE, ("boundary-coverage-incomplete",), facts)
    if candidate_size > accepted_size:
        return RegressionOutcome(Verdict.FAIL, ("boundary-extent-overclaim",), facts)
    return RegressionOutcome(Verdict.PASS, (), facts)


def _relocation_destination_content(data: Mapping[str, Any]) -> RegressionOutcome:
    _exact_keys(
        data,
        required={
            "relocation_type",
            "required_relocation_type",
            "addend",
            "required_addend",
            "candidate_symbol",
            "candidate_destination",
            "target_destination",
            "candidate_data_hex",
            "target_data_hex",
        },
        context="relocation-destination-content input",
    )
    relocation_type = _string(data["relocation_type"], "relocation_type")
    required_type = _string(data["required_relocation_type"], "required_relocation_type")
    addend = _integer(data["addend"], "addend")
    required_addend = _integer(data["required_addend"], "required_addend")
    symbol = _string(data["candidate_symbol"], "candidate_symbol")
    candidate_destination = _address(data["candidate_destination"], "candidate_destination")
    target_destination = _address(data["target_destination"], "target_destination")
    candidate_bytes = _data_hex(data["candidate_data_hex"], "candidate_data_hex")
    target_bytes = _data_hex(data["target_data_hex"], "target_data_hex")
    facts = {
        "candidate_data_hex": candidate_bytes,
        "target_data_hex": target_bytes,
        "destination": target_destination,
    }
    if relocation_type != required_type:
        return RegressionOutcome(Verdict.FAIL, ("relocation-form-mismatch",), facts)
    if addend != required_addend:
        return RegressionOutcome(Verdict.FAIL, ("relocation-addend-mismatch",), facts)
    if int(candidate_destination, 16) != int(target_destination, 16):
        return RegressionOutcome(Verdict.FAIL, ("relocation-destination-mismatch",), facts)
    if candidate_bytes is None or target_bytes is None:
        return RegressionOutcome(
            Verdict.INCOMPLETE, ("relocation-destination-content-unknown",), facts
        )
    symbol_prefix = "__real@"
    encoded = symbol[len(symbol_prefix) :] if symbol.startswith(symbol_prefix) else ""
    if not _HEX.fullmatch(encoded):
        return RegressionOutcome(Verdict.FAIL, ("relocation-literal-symbol-invalid",), facts)
    symbol_bytes = bytes.fromhex(encoded)[::-1].hex()
    if symbol_bytes != candidate_bytes:
        return RegressionOutcome(Verdict.FAIL, ("relocation-symbol-content-mismatch",), facts)
    if candidate_bytes != target_bytes:
        return RegressionOutcome(
            Verdict.FAIL, ("relocation-destination-content-mismatch",), facts
        )
    return RegressionOutcome(Verdict.PASS, (), facts)


def _whole_build_closure(data: Mapping[str, Any]) -> RegressionOutcome:
    _exact_keys(
        data,
        required={
            "coverage_complete",
            "objects_expected",
            "objects_compiled",
            "source_profiles",
            "link_attempted",
            "link_succeeded",
            "unique_unresolved_symbols",
            "unresolved_diagnostics",
            "source_present_functions",
            "exact_functions",
        },
        context="whole-build-closure input",
    )
    coverage_complete = _boolean(data["coverage_complete"], "coverage_complete")
    objects_expected = _integer(data["objects_expected"], "objects_expected", minimum=1)
    objects_compiled = _integer(data["objects_compiled"], "objects_compiled")
    source_profiles = _integer(data["source_profiles"], "source_profiles", minimum=1)
    link_attempted = _boolean(data["link_attempted"], "link_attempted")
    link_succeeded = _boolean(data["link_succeeded"], "link_succeeded")
    unresolved = _integer(data["unique_unresolved_symbols"], "unique_unresolved_symbols")
    diagnostics = _integer(data["unresolved_diagnostics"], "unresolved_diagnostics")
    source_present = _integer(data["source_present_functions"], "source_present_functions")
    exact = _integer(data["exact_functions"], "exact_functions")
    facts = {
        "objects": f"{objects_compiled}/{objects_expected}",
        "source_profiles": source_profiles,
        "unique_unresolved_symbols": unresolved,
        "unresolved_diagnostics": diagnostics,
        "source_present_functions": source_present,
        "exact_functions": exact,
    }
    if not coverage_complete:
        return RegressionOutcome(Verdict.INCOMPLETE, ("whole-build-coverage-incomplete",), facts)
    if objects_compiled != objects_expected:
        return RegressionOutcome(Verdict.FAIL, ("translation-unit-build-not-closed",), facts)
    if not link_attempted:
        return RegressionOutcome(Verdict.INCOMPLETE, ("whole-build-link-not-attempted",), facts)
    if unresolved or diagnostics:
        return RegressionOutcome(Verdict.FAIL, ("whole-build-unresolved-symbols",), facts)
    if not link_succeeded:
        return RegressionOutcome(Verdict.FAIL, ("whole-build-link-failed",), facts)
    return RegressionOutcome(Verdict.PASS, (), facts)


def _target_binding(data: Mapping[str, Any]) -> RegressionOutcome:
    _exact_keys(
        data,
        required={
            "active_target_sha256",
            "evidence_target_sha256",
            "active_version",
            "evidence_version",
        },
        context="target-binding input",
    )
    active_hash = _sha256(data["active_target_sha256"], "active_target_sha256")
    evidence_hash = _sha256(data["evidence_target_sha256"], "evidence_target_sha256")
    active_version = _string(data["active_version"], "active_version")
    evidence_version = _string(data["evidence_version"], "evidence_version")
    facts = {
        "active_target_sha256": active_hash,
        "evidence_target_sha256": evidence_hash,
        "version_labels_equal": active_version == evidence_version,
    }
    if active_hash != evidence_hash:
        return RegressionOutcome(Verdict.FAIL, ("target-identity-mismatch",), facts)
    return RegressionOutcome(Verdict.PASS, (), facts)


def _extent_sizes(value: Any, context: str) -> list[int]:
    if not isinstance(value, list):
        raise RegressionFixtureError(f"{context} must be a list")
    result: list[int] = []
    for index, item in enumerate(value):
        extent = _object(item, f"{context}[{index}]")
        _exact_keys(extent, required={"start", "end", "size", "sha256"}, context=f"{context}[{index}]")
        _address(extent["start"], f"{context}[{index}].start")
        _address(extent["end"], f"{context}[{index}].end")
        result.append(_integer(extent["size"], f"{context}[{index}].size", minimum=1))
        _sha256(extent["sha256"], f"{context}[{index}].sha256")
    return result


def _owned_extent_exactness(data: Mapping[str, Any]) -> RegressionOutcome:
    _exact_keys(
        data,
        required={
            "main_size",
            "main_exclusions",
            "remote_chunks",
            "declared_main_excluded_bytes",
            "declared_remote_bytes",
            "declared_owned_bytes",
            "main_exact",
            "remote_exact",
            "declared_exact_bytes",
            "require_complete_exact",
        },
        context="owned-extent-exactness input",
    )
    main_size = _integer(data["main_size"], "main_size", minimum=1)
    exclusion_sizes = _extent_sizes(data["main_exclusions"], "main_exclusions")
    remote_sizes = _extent_sizes(data["remote_chunks"], "remote_chunks")
    declared_exclusions = _integer(
        data["declared_main_excluded_bytes"], "declared_main_excluded_bytes"
    )
    declared_remote = _integer(data["declared_remote_bytes"], "declared_remote_bytes")
    declared_owned = _integer(data["declared_owned_bytes"], "declared_owned_bytes")
    main_exact = _boolean(data["main_exact"], "main_exact")
    remote_exact = _boolean(data["remote_exact"], "remote_exact")
    declared_exact = _integer(data["declared_exact_bytes"], "declared_exact_bytes")
    require_complete = _boolean(data["require_complete_exact"], "require_complete_exact")
    calculated_exclusions = sum(exclusion_sizes)
    calculated_remote = sum(remote_sizes)
    calculated_owned = main_size - calculated_exclusions + calculated_remote
    calculated_exact = (main_size - calculated_exclusions if main_exact else 0) + (
        calculated_remote if remote_exact else 0
    )
    facts = {
        "calculated_main_excluded_bytes": calculated_exclusions,
        "calculated_remote_bytes": calculated_remote,
        "calculated_owned_bytes": calculated_owned,
        "calculated_exact_bytes": calculated_exact,
    }
    if main_size < calculated_exclusions or (
        declared_exclusions,
        declared_remote,
        declared_owned,
        declared_exact,
    ) != (
        calculated_exclusions,
        calculated_remote,
        calculated_owned,
        calculated_exact,
    ):
        return RegressionOutcome(Verdict.FAIL, ("extent-arithmetic-mismatch",), facts)
    if require_complete:
        missing: list[str] = []
        if not main_exact:
            missing.append("main-extent-exactness-unknown")
        if remote_sizes and not remote_exact:
            missing.append("remote-extent-exactness-unknown")
        if missing:
            return RegressionOutcome(Verdict.INCOMPLETE, tuple(missing), facts)
    return RegressionOutcome(Verdict.PASS, (), facts)


_EVALUATORS: Mapping[
    RegressionContract, Callable[[Mapping[str, Any]], RegressionOutcome]
] = {
    RegressionContract.BOUNDARY_COVERAGE: _boundary_coverage,
    RegressionContract.RELOCATION_DESTINATION_CONTENT: _relocation_destination_content,
    RegressionContract.WHOLE_BUILD_CLOSURE: _whole_build_closure,
    RegressionContract.TARGET_BINDING: _target_binding,
    RegressionContract.OWNED_EXTENT_EXACTNESS: _owned_extent_exactness,
}


def evaluate_fixture(fixture: HistoricalFixture) -> FixtureEvaluation:
    outcome = _EVALUATORS[fixture.contract](fixture.input)
    return FixtureEvaluation(
        fixture_id=fixture.id,
        project=fixture.project,
        contract=fixture.contract,
        expected_verdict=fixture.expected_verdict,
        expected_diagnostics=fixture.expected_diagnostics,
        outcome=outcome,
    )


def run_fixture_suite(directory: Path | None = None) -> RegressionSuiteReport:
    fixtures = load_fixture_suite(directory)
    return RegressionSuiteReport(tuple(evaluate_fixture(item) for item in fixtures))
