"""Compare adapter metrics with native read-only repository reports."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
from typing import Any

from .adapters import inspect_repository
from .errors import AdapterError
from .ontology import RepositorySnapshot


@dataclass(frozen=True, slots=True)
class LiveValidationResult:
    project_id: str
    adapter_id: str
    native_report: str
    compared_metrics: int
    input_fingerprint_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "adapter_id": self.adapter_id,
            "native_report": self.native_report,
            "compared_metrics": self.compared_metrics,
            "input_fingerprint_sha256": self.input_fingerprint_sha256,
        }


def validate_live_repository(root: str | Path) -> LiveValidationResult:
    """Run a native read-only status report and require exact metric parity."""

    resolved = Path(root).resolve(strict=True)
    dirty_before = _git_status(resolved)
    snapshot = inspect_repository(resolved)
    if snapshot.project.id == "th04":
        result = _validate_th04(resolved, snapshot)
    elif snapshot.adapter_id == "th08-vc7-ledgers-v1":
        result = _validate_th08(resolved, snapshot)
    elif snapshot.adapter_id == "windows-pe-ledgers-v1":
        result = _validate_windows(resolved, snapshot)
    else:
        raise AdapterError(
            f"no native parity validator for adapter {snapshot.adapter_id}"
        )
    dirty_after = _git_status(resolved)
    if dirty_after != dirty_before:
        raise AdapterError(
            "native validation changed the repository working tree; refusing the result"
        )
    return result


def _validate_th04(root: Path, snapshot: RepositorySnapshot) -> LiveValidationResult:
    native = _run_json(root, ("python3", "scripts/status.py", "--json"))
    native_artifacts = native["artifacts"]
    comparisons: dict[tuple[str, str], int] = {}
    for artifact_id, report in native_artifacts.items():
        comparisons.update(
            {
                (artifact_id, "inventory.boundary-observations"): report[
                    "boundary_observations"
                ],
                (artifact_id, "inventory.authored-candidates"): report[
                    "authored_function_candidates"
                ],
                (artifact_id, "inventory.authored-unreviewed"): report[
                    "authored_candidate_states"
                ].get("unreviewed", 0),
                (artifact_id, "inventory.authored-blocked"): report[
                    "authored_candidate_states"
                ].get("blocked", 0),
                (artifact_id, "exact.authored-functions"): report[
                    "exact_authored_functions"
                ],
                (artifact_id, "exact.authored-bytes"): report["exact_authored_bytes"],
                (artifact_id, "reviewed.authored-functions"): report[
                    "reviewed_authored_functions"
                ],
                (artifact_id, "reviewed.authored-bytes"): report[
                    "known_authored_bytes"
                ],
                (artifact_id, "target.bytes"): report["target_size"],
            }
        )
    _require_metric_parity(snapshot, comparisons)
    return LiveValidationResult(
        project_id=snapshot.project.id,
        adapter_id=snapshot.adapter_id,
        native_report="scripts/status.py --json",
        compared_metrics=len(comparisons),
        input_fingerprint_sha256=snapshot.input_fingerprint_sha256,
    )


def _validate_windows(root: Path, snapshot: RepositorySnapshot) -> LiveValidationResult:
    native = _run_json(
        root,
        ("python3", "scripts/report-reconstruction-status.py", "--summary", "--json"),
    )["summary"]
    project_id = snapshot.project.id
    mapping = {
        "inventory.candidates": "candidates",
        "inventory.candidate-bytes": "candidate_bytes",
        "inventory.review": "review",
        "inventory.authored": "authored",
        "inventory.excluded": "excluded",
        "mapping.functions": "mapped",
        "source.present-functions": "source_present",
        "exact.functions": "exact_functions",
        "exact.bytes": "exact_bytes",
        "build.configured-units": "configured_units",
    }
    if "authored_bytes" in native:
        mapping["inventory.authored-bytes"] = "authored_bytes"
    if "remote_authored_bytes" in native:
        mapping["inventory.remote-authored-bytes"] = "remote_authored_bytes"
    comparisons = {
        (project_id, metric_name): native[native_name]
        for metric_name, native_name in mapping.items()
    }
    _require_metric_parity(snapshot, comparisons)
    return LiveValidationResult(
        project_id=project_id,
        adapter_id=snapshot.adapter_id,
        native_report="scripts/report-reconstruction-status.py --summary --json",
        compared_metrics=len(comparisons),
        input_fingerprint_sha256=snapshot.input_fingerprint_sha256,
    )


def _validate_th08(root: Path, snapshot: RepositorySnapshot) -> LiveValidationResult:
    native = _run_json(
        root,
        (
            "python3",
            "scripts/analysis/report-reconstruction-status.py",
            "--summary",
            "--json",
        ),
    )["summary"]
    authored = native["authored"]
    library = native["library"]
    project_id = snapshot.project.id
    comparisons = {
        (project_id, "inventory.authored"): authored["functions"],
        (project_id, "inventory.authored-bytes"): authored["bytes"],
        (project_id, "source.present-functions"): authored["source_present_functions"],
        (project_id, "source.present-bytes"): authored["source_present_bytes"],
        (project_id, "exact.functions"): authored["exact_functions"],
        (project_id, "exact.bytes"): authored["exact_bytes"],
        (project_id, "inventory.library"): library["functions"],
        (project_id, "inventory.library-sized"): library["sized_functions"],
        (project_id, "inventory.library-known-bytes"): library["known_bytes"],
        (project_id, "library.configured-units"): library["with_match_units"],
        (project_id, "library.exact-functions"): library["accepted_matches"],
    }
    _require_metric_parity(snapshot, comparisons)
    return LiveValidationResult(
        project_id=project_id,
        adapter_id=snapshot.adapter_id,
        native_report="scripts/analysis/report-reconstruction-status.py --summary --json",
        compared_metrics=len(comparisons),
        input_fingerprint_sha256=snapshot.input_fingerprint_sha256,
    )


def _require_metric_parity(
    snapshot: RepositorySnapshot, expected: dict[tuple[str, str], int | float]
) -> None:
    actual = {(metric.scope_id, metric.name): metric.value for metric in snapshot.metrics}
    failures = []
    for key, expected_value in expected.items():
        actual_value = actual.get(key)
        if actual_value != expected_value:
            failures.append(f"{key}: adapter={actual_value!r} native={expected_value!r}")
    if failures:
        raise AdapterError("native metric parity failed: " + "; ".join(failures))


def _run_json(root: Path, command: tuple[str, ...]) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=root,
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=60,
    )
    if completed.returncode != 0:
        raise AdapterError(
            f"native report failed ({' '.join(command)}): {completed.stderr.strip()}"
        )
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise AdapterError(f"native report returned invalid JSON: {error}") from error
    if not isinstance(value, dict):
        raise AdapterError("native report JSON root must be an object")
    return value


def _git_status(root: Path) -> str:
    completed = subprocess.run(
        ("git", "status", "--porcelain=v1", "--untracked-files=all"),
        cwd=root,
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=15,
    )
    if completed.returncode != 0:
        raise AdapterError(f"cannot record repository status: {completed.stderr.strip()}")
    return completed.stdout
