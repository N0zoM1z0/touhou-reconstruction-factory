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
import subprocess
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
    SOURCE_PRESENCE_CARDINALITY = "source-presence-cardinality"
    TOOLCHAIN_SURFACE_COVERAGE = "toolchain-surface-coverage"
    CODEGEN_CONTEXT_COMPARISON = "codegen-context-comparison"
    EXACT_PROMOTION_EVIDENCE = "exact-promotion-evidence"
    WORKSPACE_ISOLATION = "workspace-isolation"


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


@dataclass(frozen=True, slots=True)
class ProvenanceCheck:
    fixture_id: str
    project: str
    repository: str
    commit: str
    verified_paths: tuple[str, ...]
    diagnostics: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.diagnostics

    def to_dict(self) -> dict[str, Any]:
        result = to_primitive(self)
        result["passed"] = self.passed
        return result


@dataclass(frozen=True, slots=True)
class ProvenanceReport:
    checks: tuple[ProvenanceCheck, ...]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "fixture_count": len(self.checks),
            "checks": [check.to_dict() for check in self.checks],
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
        raise RegressionFixtureError("unsupported fixture manifest schema version")
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


def _source_presence_cardinality(data: Mapping[str, Any]) -> RegressionOutcome:
    _exact_keys(
        data,
        required={
            "coverage_complete",
            "implemented_name_count",
            "declared_source_present_functions",
            "alias_groups",
        },
        context="source-presence-cardinality input",
    )
    coverage_complete = _boolean(data["coverage_complete"], "coverage_complete")
    name_count = _integer(data["implemented_name_count"], "implemented_name_count")
    declared_functions = _integer(
        data["declared_source_present_functions"], "declared_source_present_functions"
    )
    raw_groups = data["alias_groups"]
    if not isinstance(raw_groups, list):
        raise RegressionFixtureError("alias_groups must be a list")
    names: set[str] = set()
    addresses: set[int] = set()
    alias_expansion = 0
    for index, raw_group in enumerate(raw_groups):
        group = _object(raw_group, f"alias_groups[{index}]")
        _exact_keys(
            group,
            required={"name", "addresses"},
            context=f"alias_groups[{index}]",
        )
        name = _string(group["name"], f"alias_groups[{index}].name")
        if name in names:
            raise RegressionFixtureError(f"duplicate alias group name: {name!r}")
        names.add(name)
        raw_addresses = group["addresses"]
        if not isinstance(raw_addresses, list) or len(raw_addresses) < 2:
            raise RegressionFixtureError("each alias group requires at least two addresses")
        group_addresses: set[int] = set()
        for item in raw_addresses:
            address = int(_address(item, f"alias_groups[{index}].addresses"), 16)
            if address in addresses or address in group_addresses:
                raise RegressionFixtureError("alias group addresses must be globally unique")
            group_addresses.add(address)
        addresses.update(group_addresses)
        alias_expansion += len(group_addresses) - 1
    calculated_functions = name_count + alias_expansion
    facts = {
        "implemented_name_count": name_count,
        "alias_group_count": len(raw_groups),
        "alias_expansion": alias_expansion,
        "calculated_source_present_functions": calculated_functions,
    }
    if not coverage_complete:
        return RegressionOutcome(
            Verdict.INCOMPLETE, ("source-presence-coverage-incomplete",), facts
        )
    if calculated_functions != declared_functions:
        return RegressionOutcome(
            Verdict.FAIL, ("source-presence-cardinality-mismatch",), facts
        )
    return RegressionOutcome(Verdict.PASS, (), facts)


def _string_set(value: Any, context: str) -> set[str]:
    if not isinstance(value, list):
        raise RegressionFixtureError(f"{context} must be a list")
    result = {_string(item, context) for item in value}
    if len(result) != len(value):
        raise RegressionFixtureError(f"{context} must not contain duplicates")
    return result


def _toolchain_surface_coverage(data: Mapping[str, Any]) -> RegressionOutcome:
    _exact_keys(
        data,
        required={"required_surfaces", "fingerprinted_surfaces"},
        context="toolchain-surface-coverage input",
    )
    required = _string_set(data["required_surfaces"], "required_surfaces")
    fingerprinted = _string_set(data["fingerprinted_surfaces"], "fingerprinted_surfaces")
    if not required:
        raise RegressionFixtureError("required_surfaces must not be empty")
    missing = sorted(required - fingerprinted)
    facts = {
        "required_surface_count": len(required),
        "fingerprinted_surface_count": len(fingerprinted),
        "missing_surfaces": missing,
    }
    if missing:
        return RegressionOutcome(
            Verdict.INCOMPLETE, ("toolchain-surface-coverage-incomplete",), facts
        )
    return RegressionOutcome(Verdict.PASS, (), facts)


def _codegen_context_comparison(data: Mapping[str, Any]) -> RegressionOutcome:
    _exact_keys(
        data,
        required={
            "coverage_complete",
            "target_codegen_context",
            "candidate_codegen_context",
            "differing_bytes",
        },
        context="codegen-context-comparison input",
    )
    coverage_complete = _boolean(data["coverage_complete"], "coverage_complete")
    target_context = _string(data["target_codegen_context"], "target_codegen_context")
    candidate_context = _string(
        data["candidate_codegen_context"], "candidate_codegen_context"
    )
    differing_bytes = _integer(data["differing_bytes"], "differing_bytes")
    facts = {
        "target_codegen_context": target_context,
        "candidate_codegen_context": candidate_context,
        "contexts_equal": target_context == candidate_context,
        "differing_bytes": differing_bytes,
    }
    if not coverage_complete:
        return RegressionOutcome(
            Verdict.INCOMPLETE, ("codegen-comparison-coverage-incomplete",), facts
        )
    if differing_bytes:
        diagnostics = ["codegen-content-mismatch"]
        if target_context != candidate_context:
            diagnostics.append("codegen-context-not-equivalent")
        return RegressionOutcome(Verdict.FAIL, tuple(diagnostics), facts)
    return RegressionOutcome(Verdict.PASS, (), facts)


def _scope(value: Any, context: str) -> dict[str, Any]:
    result = _object(value, context)
    _exact_keys(
        result,
        required={"artifact", "unit_id", "extent_start", "extent_size"},
        context=context,
    )
    return {
        "artifact": _string(result["artifact"], f"{context}.artifact"),
        "unit_id": _string(result["unit_id"], f"{context}.unit_id"),
        "extent_start": _integer(result["extent_start"], f"{context}.extent_start"),
        "extent_size": _integer(
            result["extent_size"], f"{context}.extent_size", minimum=1
        ),
    }


def _exact_promotion_evidence(data: Mapping[str, Any]) -> RegressionOutcome:
    _exact_keys(
        data,
        required={
            "claim_scope",
            "evidence_scope",
            "required_oracles",
            "passed_oracles",
            "boundary_reviewed",
            "extent_within_artifact",
            "source_checked_in",
            "replay_metadata_complete",
            "replay_driver_checked_in",
            "replay_command_shell_free",
            "hashes_valid",
            "raw_hashes_equal",
        },
        context="exact-promotion-evidence input",
    )
    claim_scope = _scope(data["claim_scope"], "claim_scope")
    evidence_scope = _scope(data["evidence_scope"], "evidence_scope")
    required = _string_set(data["required_oracles"], "required_oracles")
    passed = _string_set(data["passed_oracles"], "passed_oracles")
    if not required:
        raise RegressionFixtureError("required_oracles must not be empty")
    checks = {
        name: _boolean(data[name], name)
        for name in (
            "boundary_reviewed",
            "extent_within_artifact",
            "source_checked_in",
            "replay_metadata_complete",
            "replay_driver_checked_in",
            "replay_command_shell_free",
            "hashes_valid",
            "raw_hashes_equal",
        )
    }
    facts = {
        "claim_scope": claim_scope,
        "evidence_scope": evidence_scope,
        "missing_oracles": sorted(required - passed),
    }
    if claim_scope != evidence_scope:
        return RegressionOutcome(Verdict.FAIL, ("exact-evidence-scope-mismatch",), facts)
    if not checks["extent_within_artifact"]:
        return RegressionOutcome(Verdict.FAIL, ("exact-extent-outside-artifact",), facts)
    if not checks["hashes_valid"]:
        return RegressionOutcome(Verdict.FAIL, ("exact-evidence-hash-invalid",), facts)
    if not checks["raw_hashes_equal"]:
        return RegressionOutcome(Verdict.FAIL, ("exact-raw-content-mismatch",), facts)
    if not checks["replay_driver_checked_in"] or not checks["replay_command_shell_free"]:
        return RegressionOutcome(Verdict.FAIL, ("exact-replay-driver-invalid",), facts)
    incomplete = []
    if not checks["boundary_reviewed"]:
        incomplete.append("exact-boundary-coverage-incomplete")
    if not checks["source_checked_in"]:
        incomplete.append("exact-source-coverage-incomplete")
    if not checks["replay_metadata_complete"]:
        incomplete.append("exact-replay-metadata-incomplete")
    if required - passed:
        incomplete.append("exact-required-oracles-incomplete")
    if incomplete:
        return RegressionOutcome(Verdict.INCOMPLETE, tuple(incomplete), facts)
    return RegressionOutcome(Verdict.PASS, (), facts)


def _workspace_isolation(data: Mapping[str, Any]) -> RegressionOutcome:
    _exact_keys(
        data,
        required={
            "concurrent_invocation_ids",
            "workspace_names",
            "case_insensitive_namespace",
            "max_component_length",
            "mutable_outputs",
        },
        context="workspace-isolation input",
    )
    raw_ids = data["concurrent_invocation_ids"]
    raw_names = data["workspace_names"]
    if not isinstance(raw_ids, list) or len(raw_ids) < 2:
        raise RegressionFixtureError("concurrent_invocation_ids requires at least two entries")
    if not isinstance(raw_names, list):
        raise RegressionFixtureError("workspace_names must be a list")
    invocation_ids = [
        _integer(item, "concurrent_invocation_ids", minimum=1) for item in raw_ids
    ]
    if len(invocation_ids) != len(set(invocation_ids)):
        raise RegressionFixtureError("concurrent_invocation_ids must be unique")
    names = [_string(item, "workspace_names") for item in raw_names]
    case_insensitive = _boolean(
        data["case_insensitive_namespace"], "case_insensitive_namespace"
    )
    max_length = _integer(data["max_component_length"], "max_component_length", minimum=1)
    mutable_outputs = _boolean(data["mutable_outputs"], "mutable_outputs")
    normalized = [name.casefold() if case_insensitive else name for name in names]
    facts = {
        "invocation_count": len(invocation_ids),
        "workspace_count": len(names),
        "unique_workspace_count": len(set(normalized)),
    }
    if len(names) != len(invocation_ids):
        return RegressionOutcome(
            Verdict.INCOMPLETE, ("workspace-assignment-incomplete",), facts
        )
    if any(len(name) > max_length or not re.fullmatch(r"[A-Z0-9]+", name) for name in names):
        return RegressionOutcome(Verdict.FAIL, ("workspace-name-invalid",), facts)
    if mutable_outputs and len(set(normalized)) != len(names):
        return RegressionOutcome(Verdict.FAIL, ("workspace-collision",), facts)
    return RegressionOutcome(Verdict.PASS, (), facts)


_EVALUATORS: Mapping[
    RegressionContract, Callable[[Mapping[str, Any]], RegressionOutcome]
] = {
    RegressionContract.BOUNDARY_COVERAGE: _boundary_coverage,
    RegressionContract.RELOCATION_DESTINATION_CONTENT: _relocation_destination_content,
    RegressionContract.WHOLE_BUILD_CLOSURE: _whole_build_closure,
    RegressionContract.TARGET_BINDING: _target_binding,
    RegressionContract.OWNED_EXTENT_EXACTNESS: _owned_extent_exactness,
    RegressionContract.SOURCE_PRESENCE_CARDINALITY: _source_presence_cardinality,
    RegressionContract.TOOLCHAIN_SURFACE_COVERAGE: _toolchain_surface_coverage,
    RegressionContract.CODEGEN_CONTEXT_COMPARISON: _codegen_context_comparison,
    RegressionContract.EXACT_PROMOTION_EVIDENCE: _exact_promotion_evidence,
    RegressionContract.WORKSPACE_ISOLATION: _workspace_isolation,
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


def verify_fixture_provenance(
    repository_roots: Mapping[str, Path],
    *,
    directory: Path | None = None,
    fixtures: tuple[HistoricalFixture, ...] | None = None,
) -> ProvenanceReport:
    """Verify fixture commits and blobs against explicitly selected local clones."""

    selected = fixtures if fixtures is not None else load_fixture_suite(directory)
    checks: list[ProvenanceCheck] = []
    repository_cache: dict[tuple[str, str], tuple[Path | None, tuple[str, ...]]] = {}
    for fixture in selected:
        repository_key = (fixture.project, fixture.provenance.repository)
        cached = repository_cache.get(repository_key)
        if cached is None:
            configured = repository_roots.get(fixture.project)
            diagnostics: list[str] = []
            root: Path | None = None
            if configured is None:
                diagnostics.append("repository-root-missing")
            else:
                try:
                    root = Path(configured).resolve(strict=True)
                except OSError:
                    diagnostics.append("repository-root-unreadable")
                if root is not None:
                    top = _git(root, "rev-parse", "--show-toplevel")
                    if top is None or Path(top).resolve() != root:
                        diagnostics.append("repository-root-invalid")
                    remote = _git(root, "remote", "get-url", "origin")
                    if remote is None:
                        diagnostics.append("repository-origin-missing")
                    elif _remote_repository_id(remote) != fixture.provenance.repository.lower():
                        diagnostics.append("repository-origin-mismatch")
            cached = (root, tuple(diagnostics))
            repository_cache[repository_key] = cached
        root, repository_diagnostics = cached
        diagnostics = list(repository_diagnostics)
        verified_paths: list[str] = []
        if root is not None and not repository_diagnostics:
            commit_spec = f"{fixture.provenance.commit}^{{commit}}"
            if _git(root, "cat-file", "-e", commit_spec, capture=False) is None:
                diagnostics.append("provenance-commit-missing")
            else:
                for source_path in fixture.provenance.paths:
                    object_type = _git(
                        root,
                        "cat-file",
                        "-t",
                        f"{fixture.provenance.commit}:{source_path}",
                    )
                    if object_type != "blob":
                        diagnostics.append(f"provenance-path-missing:{source_path}")
                    else:
                        verified_paths.append(source_path)
        checks.append(
            ProvenanceCheck(
                fixture_id=fixture.id,
                project=fixture.project,
                repository=fixture.provenance.repository,
                commit=fixture.provenance.commit,
                verified_paths=tuple(verified_paths),
                diagnostics=tuple(diagnostics),
            )
        )
    return ProvenanceReport(tuple(checks))


def _git(root: Path, *arguments: str, capture: bool = True) -> str | None:
    try:
        completed = subprocess.run(
            ("git", *arguments),
            cwd=root,
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() if capture else "ok"


def _remote_repository_id(url: str) -> str:
    value = url.strip().removesuffix(".git").rstrip("/")
    if value.startswith("git@") and ":" in value:
        value = value.split(":", 1)[1]
    elif "://" in value:
        value = value.split("://", 1)[1].split("/", 1)[-1]
    parts = value.split("/")
    return "/".join(parts[-2:]).lower() if len(parts) >= 2 else value.lower()
