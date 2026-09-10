"""Narrow adapters from native game oracles to the factory receipt contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import json
import os
from pathlib import Path
import shutil
import sys
import tomllib
from typing import Any, Mapping, Sequence

from .errors import ReplayError
from .ontology import (
    Claim,
    ClaimType,
    Coverage,
    RepositorySnapshot,
    Subject,
    SubjectKind,
    Verdict,
)
from .oracle_receipts import AttestationLevel, Coldness, canonical_sha256
from .replay_identity import file_sha256


@dataclass(frozen=True, slots=True)
class ComponentSpec:
    id: str
    path: Path
    logical_path: str
    kind: str | None = None


@dataclass(frozen=True, slots=True)
class ReplayStagePlan:
    id: str
    argv: tuple[str, ...]
    cwd: Path
    environment: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ReplayPlan:
    driver_id: str
    oracle_id: str
    coldness: Coldness
    stages: tuple[ReplayStagePlan, ...]
    oracle_inputs: tuple[Path, ...]
    target_path: Path
    toolchain_components: tuple[ComponentSpec, ...]
    environment_names: tuple[str, ...]
    native_report_path: Path | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RawExecution:
    stage_id: str
    exit_code: int | None
    timed_out: bool
    duration_ms: int
    stdout: bytes
    stderr: bytes


@dataclass(frozen=True, slots=True)
class NativeOutcome:
    verdict: Verdict
    observed_bytes: int
    report: Mapping[str, Any] | None
    diagnostics: tuple[str, ...] = ()
    normalizations: tuple[str, ...] = ()
    attestation: AttestationLevel = AttestationLevel.OBSERVED
    coverage: Coverage | None = None


class ReplayDriver:
    driver_id: str
    adapter_id: str
    oracle_id: str

    def supports(self, snapshot: RepositorySnapshot, claim: Claim) -> bool:
        raise NotImplementedError

    def prepare(
        self,
        root: Path,
        snapshot: RepositorySnapshot,
        claim: Claim,
        subject: Subject,
        run_id: str,
    ) -> ReplayPlan:
        raise NotImplementedError

    def decode(
        self,
        plan: ReplayPlan,
        claim: Claim,
        subject: Subject,
        executions: Sequence[RawExecution],
    ) -> NativeOutcome:
        raise NotImplementedError


def _repo_file(root: Path, relative: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ReplayError(f"driver path must be a contained relative path: {relative}")
    try:
        resolved = (root / candidate).resolve(strict=True)
    except FileNotFoundError as error:
        raise ReplayError(f"required replay input is missing: {relative}") from error
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise ReplayError(f"replay input is not a contained file: {relative}")
    return resolved


def _repo_output(root: Path, relative: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ReplayError(f"driver output must be a contained relative path: {relative}")
    resolved = (root / candidate).resolve()
    if not resolved.is_relative_to(root):
        raise ReplayError(f"driver output escapes repository: {relative}")
    return resolved


def _toml(root: Path, relative: str) -> dict[str, Any]:
    try:
        payload = _repo_file(root, relative).read_bytes()
        return _parse_toml_payload(payload)
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise ReplayError(f"invalid replay manifest {relative}: {error}") from error


@lru_cache(maxsize=64)
def _parse_toml_payload(payload: bytes) -> dict[str, Any]:
    """Parse identical immutable manifest bytes once per worker process."""

    return tomllib.loads(payload.decode("utf-8"))


def _extent(subject: Subject) -> tuple[str, int]:
    if not subject.extents:
        raise ReplayError("exact replay requires an explicit subject extent")
    starts = {item.start for item in subject.extents}
    if len(starts) != 1 and len(subject.extents) > 1:
        raise ReplayError("this driver does not yet support disjoint claim extents")
    return subject.extents[0].start, sum(item.size for item in subject.extents)


def _unit_name(claim: Claim) -> str:
    value = claim.value.get("unit")
    if not isinstance(value, str) or not value:
        raise ReplayError(f"claim {claim.id} has no structured unit identity")
    return value


def _json_stdout(execution: RawExecution) -> Mapping[str, Any]:
    try:
        value = json.loads(execution.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReplayError(f"stage {execution.stage_id} did not emit one JSON document") from error
    if not isinstance(value, dict):
        raise ReplayError(f"stage {execution.stage_id} JSON output must be an object")
    return value


def _runtime_components() -> tuple[ComponentSpec, ...]:
    specs = [
        ComponentSpec("runtime-python", Path(sys.executable), "$PYTHON", "runtime")
    ]
    wine_name = os.environ.get("WINE", "wine")
    wine = shutil.which(wine_name)
    if wine:
        specs.append(ComponentSpec("runtime-wine", Path(wine), "$WINE", "runtime"))
        wine64 = Path("/usr/lib/wine/wine64")
        if wine64.is_file():
            specs.append(
                ComponentSpec("runtime-wine64", wine64, "/usr/lib/wine/wine64", "runtime")
            )
    return tuple(specs)


def _identity_inputs(root: Path, relatives: Sequence[str]) -> tuple[Path, ...]:
    return tuple(_repo_file(root, relative) for relative in relatives)


def driver_version(plan: ReplayPlan) -> str:
    records = []
    implementation = Path(__file__).resolve(strict=True)
    for path in (implementation, *plan.oracle_inputs):
        records.append(
            {
                "path": (
                    "$FACTORY/replay_drivers.py"
                    if path == implementation
                    else path.relative_to(plan.stages[0].cwd).as_posix()
                ),
                "sha256": file_sha256(path),
            }
        )
    return canonical_sha256(
        {
            "driver_id": plan.driver_id,
            "oracle_id": plan.oracle_id,
            "coldness": plan.coldness.value,
            "inputs": records,
        }
    )


class Th04OwnedExtentDriver(ReplayDriver):
    driver_id = "th04-main-owned-extent-v1"
    adapter_id = "th04-pc98-v1"
    oracle_id = "pc98.borland16.owned-extent-exact"

    def supports(self, snapshot: RepositorySnapshot, claim: Claim) -> bool:
        return (
            snapshot.adapter_id == self.adapter_id
            and claim.type is ClaimType.OWNED_EXTENT_EXACT
            and claim.value.get("exact") is True
            and claim.subject_id.startswith("unit:th04-main-")
        )

    def prepare(self, root: Path, snapshot: RepositorySnapshot, claim: Claim, subject: Subject, run_id: str) -> ReplayPlan:
        _extent(subject)
        unit = claim.subject_id.removeprefix("unit:")
        script = _repo_file(root, "scripts/replay_th04_main_exact_units.py")
        report = _repo_output(
            root, f".analysis/reconstruction/exact-unit-replay/{run_id}/receipt.json"
        )
        inputs = _identity_inputs(
            root,
            (
                "scripts/replay_th04_main_exact_units.py",
                "scripts/attest_toolchain.py",
                "scripts/lib/omf.py",
                "scripts/lib/pc98.py",
                "scripts/lib/toolchain.py",
                "config/th04_main_exact_units.toml",
                "config/toolchain.toml",
                "config/targets.toml",
                "config/units.csv",
            ),
        )
        toolchain_manifest = _toml(root, "config/toolchain.toml")
        component_specs = []
        surfaces = toolchain_manifest.get("surfaces")
        if not isinstance(surfaces, list):
            raise ReplayError("TH04 toolchain manifest has no surfaces")
        for surface in surfaces:
            if not isinstance(surface, dict) or not isinstance(surface.get("path"), str):
                raise ReplayError("TH04 toolchain surface is malformed")
            raw_path = Path(surface["path"])
            actual_path = raw_path if raw_path.is_absolute() else root / raw_path
            if surface.get("required") is True or actual_path.exists():
                component_specs.append(
                    ComponentSpec(
                        str(surface["id"]),
                        actual_path,
                        str(surface["path"]),
                    )
                )
        component_specs.append(
            ComponentSpec("runtime-python", Path(sys.executable), "$PYTHON", "runtime")
        )
        return ReplayPlan(
            driver_id=self.driver_id,
            oracle_id=self.oracle_id,
            coldness=Coldness.ISOLATED_DOUBLE_BUILD,
            stages=(ReplayStagePlan("cold-replay", (sys.executable, str(script.relative_to(root)), "--unit", unit, "--run-id", run_id), root),),
            oracle_inputs=inputs,
            target_path=_repo_file(root, ".analysis/targets/th04/main.exe"),
            toolchain_components=tuple(component_specs),
            environment_names=("HOME", "PATH", "PYTHONPATH", "WINE", "WINEPREFIX"),
            native_report_path=report,
            metadata={"unit": unit},
        )

    def decode(self, plan: ReplayPlan, claim: Claim, subject: Subject, executions: Sequence[RawExecution]) -> NativeOutcome:
        if not executions or not plan.native_report_path or not plan.native_report_path.is_file():
            return NativeOutcome(Verdict.ERROR, 0, None, ("native-receipt-missing",))
        try:
            report = json.loads(plan.native_report_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ReplayError(f"invalid TH04 native receipt: {error}") from error
        if not isinstance(report, dict):
            raise ReplayError("TH04 native receipt must be an object")
        unit = str(plan.metadata["unit"])
        start, expected_size = _extent(subject)
        selected = report.get("selected_units")
        builds = report.get("builds")
        if not isinstance(selected, list) or unit not in selected or not isinstance(builds, list) or len(builds) != 2:
            return NativeOutcome(Verdict.INCOMPLETE, 0, report, ("native-unit-or-double-build-coverage-missing",))
        units = []
        for build in builds:
            if not isinstance(build, dict) or not isinstance(build.get("units"), dict):
                return NativeOutcome(Verdict.ERROR, 0, report, ("native-build-result-malformed",))
            unit_result = build["units"].get(unit)
            if not isinstance(unit_result, dict):
                return NativeOutcome(Verdict.INCOMPLETE, 0, report, ("native-unit-result-missing",))
            units.append(unit_result)
        if any(
            int(item.get("size", -1)) != expected_size
            or int(item.get("file_start", -1)) != int(start, 0)
            for item in units
        ):
            return NativeOutcome(Verdict.INCOMPLETE, 0, report, (f"extent-size-mismatch:{start}",))
        checks = (
            "raw_exact",
            "map_exact",
            "relocations_exact",
            "object_valid",
        )
        requested_exact = all(
            item.get(check) is True for item in units for check in checks
        )
        failure_units = {
            item.get("unit_id") for item in report.get("failures", []) if isinstance(item, dict)
        }
        if requested_exact and report.get("pass") is True:
            verdict = Verdict.PASS
        elif not requested_exact or unit in failure_units:
            verdict = Verdict.FAIL
        else:
            verdict = Verdict.INCOMPLETE
        attestation_path = plan.stages[0].cwd / ".analysis/toolchain/attestation.json"
        evidence_report: dict[str, Any] = {"replay_receipt": report}
        attestation = AttestationLevel.UNKNOWN
        if attestation_path.is_file():
            native_attestation = json.loads(attestation_path.read_text(encoding="utf-8"))
            evidence_report["toolchain_attestation"] = native_attestation
            attestation_hash = file_sha256(attestation_path)
            if (
                isinstance(native_attestation, dict)
                and native_attestation.get("ready") is True
                and report.get("toolchain_attestation_sha256") == attestation_hash
            ):
                attestation = AttestationLevel.VERIFIED
        if report.get("target_sha256") != file_sha256(plan.target_path):
            return NativeOutcome(Verdict.ERROR, 0, report, ("native-target-binding-mismatch",))
        return NativeOutcome(
            verdict,
            expected_size,
            evidence_report,
            () if verdict is Verdict.PASS else ("native-exact-check-failed",),
            ("omf-dependency-timestamp-normalized-for-determinism-v1",),
            attestation,
        )


class Th08FunctionDriver(ReplayDriver):
    driver_id = "th08-vc7-function-v1"
    adapter_id = "th08-vc7-ledgers-v1"
    oracle_id = "windows.msvc7.function-exact"

    def supports(self, snapshot: RepositorySnapshot, claim: Claim) -> bool:
        return (
            snapshot.adapter_id == self.adapter_id
            and claim.type is ClaimType.CODEGEN_EXACT
            and claim.value.get("exact") is True
        )

    def prepare(self, root: Path, snapshot: RepositorySnapshot, claim: Claim, subject: Subject, run_id: str) -> ReplayPlan:
        _extent(subject)
        unit_name = _unit_name(claim)
        manifest = _toml(root, "config/match-units.toml")
        units = manifest.get("units")
        if not isinstance(units, list):
            raise ReplayError("TH08 match unit manifest is malformed")
        unit = next((item for item in units if isinstance(item, dict) and item.get("name") == unit_name), None)
        if unit is None or not isinstance(unit.get("object"), str):
            raise ReplayError(f"TH08 claim unit is absent from manifest: {unit_name}")
        build = _repo_file(root, "scripts/build.py")
        compare = _repo_file(root, "scripts/compare-function.py")
        prefix = root / "scripts/prefix"
        vc7 = prefix / "PROGRAM FILES/MICROSOFT VISUAL STUDIO .NET/VC7"
        specs = (
            ComponentSpec("vc7-bin", vc7 / "BIN", "$TH08_PREFIX/VC7/BIN"),
            ComponentSpec("vc7-include", vc7 / "INCLUDE", "$TH08_PREFIX/VC7/INCLUDE"),
            ComponentSpec("vc7-platformsdk-include", vc7 / "PLATFORMSDK/INCLUDE", "$TH08_PREFIX/VC7/PlatformSDK/include"),
            ComponentSpec("dxsdk-include", prefix / "mssdk/include", "$TH08_PREFIX/mssdk/include"),
            ComponentSpec("native-ninja", prefix / "ninja", "$TH08_PREFIX/ninja"),
            *_runtime_components(),
        )
        inputs = _identity_inputs(
            root,
            (
                "scripts/build.py",
                "scripts/configure.py",
                "scripts/compare-function.py",
                "scripts/coff.py",
                "scripts/match_literals.py",
                "scripts/th08run.bat",
                "scripts/th08vars.bat",
                "scripts/wineth08",
                "config/match-units.toml",
                "config/target.toml",
            ),
        )
        return ReplayPlan(
            self.driver_id,
            self.oracle_id,
            Coldness.CLEAN_OUTPUT_GRAPH,
            (
                ReplayStagePlan("clean-build", (sys.executable, str(build.relative_to(root)), "--build-type=objdiffbuild", "--fresh", str(unit["object"])), root),
                ReplayStagePlan("compare", (sys.executable, str(compare.relative_to(root)), unit_name, "--json"), root),
            ),
            inputs,
            _repo_file(root, "resources/th08.exe"),
            specs,
            ("HOME", "PATH", "PYTHONPATH", "WINE", "WINEPREFIX"),
            metadata={"unit": unit_name},
        )

    def decode(self, plan: ReplayPlan, claim: Claim, subject: Subject, executions: Sequence[RawExecution]) -> NativeOutcome:
        if len(executions) != 2 or executions[0].exit_code != 0:
            return NativeOutcome(Verdict.ERROR, 0, None, ("native-build-stage-failed",))
        report = _json_stdout(executions[-1])
        return _decode_linear_function_report(report, subject, unit=str(plan.metadata["unit"]), size_key="size")


class Th095FunctionDriver(ReplayDriver):
    driver_id = "th095-vc71-function-v1"
    adapter_id = "windows-pe-ledgers-v1"
    oracle_id = "windows.msvc71.function-exact"

    def supports(self, snapshot: RepositorySnapshot, claim: Claim) -> bool:
        return (
            snapshot.project.id == "th095"
            and snapshot.adapter_id == self.adapter_id
            and claim.type is ClaimType.CODEGEN_EXACT
            and claim.value.get("exact") is True
        )

    def prepare(self, root: Path, snapshot: RepositorySnapshot, claim: Claim, subject: Subject, run_id: str) -> ReplayPlan:
        _extent(subject)
        unit = _unit_name(claim)
        _toml(root, "config/match-units.toml")
        build = _repo_file(root, "scripts/build.py")
        compare = _repo_file(root, "scripts/compare-coff-function.py")
        tool_root = Path(os.environ.get("TH095_MSVC71_ROOT", str(root / ".tools/msvc710"))).expanduser()
        vc7 = tool_root / "Vc7"
        specs = (
            ComponentSpec("vc71-bin", vc7 / "bin", "$TH095_MSVC71_ROOT/Vc7/bin"),
            ComponentSpec("vc71-include", vc7 / "include", "$TH095_MSVC71_ROOT/Vc7/include"),
            ComponentSpec("vc71-platformsdk-include", vc7 / "PlatformSDK/Include", "$TH095_MSVC71_ROOT/Vc7/PlatformSDK/Include"),
            *_runtime_components(),
        )
        inputs = _identity_inputs(
            root,
            (
                "scripts/build.py",
                "scripts/compile-probe.sh",
                "scripts/compare-coff-function.py",
                "config/match-units.toml",
                "config/target.toml",
            ),
        )
        return ReplayPlan(
            self.driver_id,
            self.oracle_id,
            Coldness.FORCED_RECOMPILE,
            (
                ReplayStagePlan("compile", (sys.executable, str(build.relative_to(root)), "--unit", unit), root),
                ReplayStagePlan("compare", (sys.executable, str(compare.relative_to(root)), "--unit", unit, "--json"), root),
            ),
            inputs,
            _repo_file(root, "resources/th095.exe"),
            specs,
            ("HOME", "PATH", "PYTHONPATH", "TH095_MSVC71_ROOT", "WINE", "WINEPREFIX"),
            metadata={"unit": unit},
        )

    def decode(self, plan: ReplayPlan, claim: Claim, subject: Subject, executions: Sequence[RawExecution]) -> NativeOutcome:
        if len(executions) != 2 or executions[0].exit_code != 0:
            return NativeOutcome(Verdict.ERROR, 0, None, ("native-compile-stage-failed",))
        report = _json_stdout(executions[-1])
        return _decode_linear_function_report(report, subject, unit=str(plan.metadata["unit"]), size_key="size")


class Th095WholeBuildDriver(ReplayDriver):
    """Cold-build the complete declared TH095 production graph."""

    driver_id = "th095-vc71-whole-build-v1"
    adapter_id = "windows-pe-ledgers-v1"
    oracle_id = "windows.msvc71.whole-build-closed"

    def supports(self, snapshot: RepositorySnapshot, claim: Claim) -> bool:
        return (
            snapshot.project.id == "th095"
            and snapshot.adapter_id == self.adapter_id
            and claim.type is ClaimType.WHOLE_BUILD_CLOSED
            and claim.value.get("closed") is True
        )

    def prepare(
        self,
        root: Path,
        snapshot: RepositorySnapshot,
        claim: Claim,
        subject: Subject,
        run_id: str,
    ) -> ReplayPlan:
        if subject.kind is not SubjectKind.PRODUCT or subject.extents:
            raise ReplayError("TH095 whole-build closure requires an extent-free product subject")
        for key in ("source_count", "profile_count"):
            value = claim.value.get(key)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ReplayError(f"TH095 whole-build claim has invalid {key}")
        if (
            claim.value.get("compile_machine") != "i386-coff"
            or claim.value.get("link_output") != "pe32-i386-windows-gui"
            or claim.value.get("zero_unresolved_required") is not True
            or claim.value.get("whole_image_exact") is not False
        ):
            raise ReplayError("TH095 whole-build claim has an unsupported closure policy")

        build = _repo_file(root, "scripts/build-whole.py")
        _toml(root, "config/match-units.toml")
        _toml(root, "config/target.toml")
        _toml(root, "config/tools.lock.toml")
        tool_root = Path(
            os.environ.get("TH095_MSVC71_ROOT", str(root / ".tools/msvc710"))
        ).expanduser()
        vc7 = tool_root / "Vc7"
        specs = (
            ComponentSpec("vc71-bin", vc7 / "bin", "$TH095_MSVC71_ROOT/Vc7/bin"),
            ComponentSpec(
                "vc71-compiler",
                vc7 / "bin/cl.exe",
                "$TH095_MSVC71_ROOT/Vc7/bin/cl.exe",
                "native-attestation",
            ),
            ComponentSpec(
                "vc71-linker",
                vc7 / "bin/link.exe",
                "$TH095_MSVC71_ROOT/Vc7/bin/link.exe",
                "native-attestation",
            ),
            ComponentSpec(
                "vc71-include", vc7 / "include", "$TH095_MSVC71_ROOT/Vc7/include"
            ),
            ComponentSpec("vc71-lib", vc7 / "lib", "$TH095_MSVC71_ROOT/Vc7/lib"),
            ComponentSpec(
                "vc71-platformsdk-include",
                vc7 / "PlatformSDK/Include",
                "$TH095_MSVC71_ROOT/Vc7/PlatformSDK/Include",
            ),
            ComponentSpec(
                "vc71-platformsdk-lib",
                vc7 / "PlatformSDK/Lib",
                "$TH095_MSVC71_ROOT/Vc7/PlatformSDK/Lib",
            ),
            *_runtime_components(),
        )
        return ReplayPlan(
            driver_id=self.driver_id,
            oracle_id=self.oracle_id,
            coldness=Coldness.CLEAN_OUTPUT_GRAPH,
            stages=(
                ReplayStagePlan(
                    "whole-build",
                    (sys.executable, str(build.relative_to(root))),
                    root,
                ),
            ),
            oracle_inputs=_identity_inputs(
                root,
                (
                    "scripts/build-whole.py",
                    "config/match-units.toml",
                    "config/target.toml",
                    "config/tools.lock.toml",
                ),
            ),
            target_path=_repo_file(root, "resources/th095.exe"),
            toolchain_components=specs,
            environment_names=(
                "HOME",
                "PATH",
                "PYTHONPATH",
                "TH095_MSVC71_ROOT",
                "WINEPREFIX",
            ),
            native_report_path=_repo_output(
                root, "build/whole-validation/report.json"
            ),
            metadata={
                "coverage_domain": "production-translation-units",
                "source_count": claim.value["source_count"],
                "profile_count": claim.value["profile_count"],
                "whole_image_exact": False,
            },
        )

    def decode(
        self,
        plan: ReplayPlan,
        claim: Claim,
        subject: Subject,
        executions: Sequence[RawExecution],
    ) -> NativeOutcome:
        if not executions or plan.native_report_path is None:
            return NativeOutcome(
                Verdict.ERROR, 0, None, ("native-whole-build-not-executed",)
            )
        if not plan.native_report_path.is_file():
            return NativeOutcome(
                Verdict.ERROR, 0, None, ("native-whole-build-report-missing",)
            )
        try:
            report = json.loads(plan.native_report_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ReplayError(f"invalid TH095 whole-build report: {error}") from error
        if not isinstance(report, dict):
            raise ReplayError("TH095 whole-build report must be a JSON object")

        expected_sources = int(claim.value["source_count"])
        expected_profiles = int(claim.value["profile_count"])
        compile_report = report.get("compile")
        link_report = report.get("link")
        report_sources = report.get("source_count")
        observed_objects = (
            compile_report.get("object_count", 0)
            if isinstance(compile_report, dict)
            else 0
        )
        coverage = Coverage(
            domain="production-translation-units",
            expected_units=expected_sources,
            observed_units=(
                observed_objects
                if isinstance(observed_objects, int)
                and not isinstance(observed_objects, bool)
                and 0 <= observed_objects <= expected_sources
                else 0
            ),
            complete=(
                report_sources == expected_sources
                and report.get("profile_count") == expected_profiles
                and isinstance(compile_report, dict)
                and compile_report.get("status") == "passed"
                and observed_objects == expected_sources
                and compile_report.get("machine") == "i386-coff"
            ),
            notes=(
                "Coverage is the complete src/**/*.cpp production graph declared by "
                "the canonical TH095 match-unit profiles; it is not function-exact or "
                "whole-image coverage."
            ),
        )
        diagnostics: list[str] = []
        if report.get("schema_version") != 1:
            diagnostics.append("native-whole-build-schema-unsupported")
        if report.get("target_sha256") != file_sha256(plan.target_path):
            diagnostics.append("native-target-binding-mismatch")
        if report_sources != expected_sources or report.get("profile_count") != expected_profiles:
            diagnostics.append("native-whole-build-plan-mismatch")
        if not coverage.complete:
            diagnostics.append("native-production-compile-incomplete")

        if not isinstance(link_report, dict):
            diagnostics.append("native-link-report-missing")
            verdict = Verdict.ERROR
        elif link_report.get("status") == "failed":
            unresolved = link_report.get("unresolved_unique_count")
            diagnostics.append(
                "native-whole-build-unresolved-symbols"
                if isinstance(unresolved, int) and unresolved > 0
                else "native-whole-build-link-failed"
            )
            verdict = Verdict.FAIL
        elif link_report.get("status") != "passed":
            diagnostics.append("native-whole-build-link-incomplete")
            verdict = Verdict.INCOMPLETE
        else:
            verdict = Verdict.PASS
            flags = link_report.get("flags")
            if not isinstance(flags, list) or any(
                not isinstance(flag, str) or flag.upper().startswith("/FORCE")
                for flag in flags
            ):
                diagnostics.append("native-link-policy-unsafe")
            artifact = link_report.get("artifact")
            output = _repo_output(
                root=plan.stages[0].cwd,
                relative="build/whole-validation/th095-reconstructed.exe",
            )
            if not isinstance(artifact, dict) or not output.is_file():
                diagnostics.append("native-linked-artifact-missing")
            elif (
                artifact.get("format") != "PE32"
                or artifact.get("machine") != "i386"
                or artifact.get("subsystem") != "windows-gui"
                or artifact.get("size") != output.stat().st_size
                or artifact.get("sha256") != file_sha256(output)
            ):
                diagnostics.append("native-linked-artifact-binding-mismatch")

        toolchain_report = report.get("toolchain")
        component_paths = {item.id: item.path for item in plan.toolchain_components}
        if not isinstance(toolchain_report, dict) or any(
            toolchain_report.get(key) != file_sha256(component_paths[component_id])
            for key, component_id in (
                ("compiler_sha256", "vc71-compiler"),
                ("linker_sha256", "vc71-linker"),
            )
        ) or not all(
            isinstance(toolchain_report.get(key), str)
            and toolchain_report.get(key)
            for key in ("compiler_version", "linker_version")
        ):
            diagnostics.append("native-toolchain-attestation-mismatch")

        if executions[-1].exit_code != 0 and verdict is Verdict.PASS:
            diagnostics.append("native-whole-build-exit-inconsistent")
        integrity_diagnostics = {
            "native-whole-build-schema-unsupported",
            "native-target-binding-mismatch",
            "native-whole-build-plan-mismatch",
            "native-link-policy-unsafe",
            "native-linked-artifact-missing",
            "native-linked-artifact-binding-mismatch",
            "native-toolchain-attestation-mismatch",
            "native-whole-build-exit-inconsistent",
        }
        if integrity_diagnostics.intersection(diagnostics):
            verdict = Verdict.ERROR
        elif verdict is Verdict.PASS and not coverage.complete:
            verdict = Verdict.INCOMPLETE
        return NativeOutcome(
            verdict=verdict,
            observed_bytes=0,
            report=report,
            diagnostics=tuple(sorted(set(diagnostics))),
            attestation=AttestationLevel.VERIFIED,
            coverage=coverage,
        )


class Th105FunctionDriver(ReplayDriver):
    driver_id = "th105-vc8-function-v1"
    adapter_id = "windows-pe-ledgers-v1"
    oracle_id = "windows.msvc8.standalone-function-exact"

    def supports(self, snapshot: RepositorySnapshot, claim: Claim) -> bool:
        return (
            snapshot.project.id == "th105"
            and snapshot.adapter_id == self.adapter_id
            and claim.type is ClaimType.CODEGEN_EXACT
            and claim.value.get("exact") is True
        )

    def prepare(self, root: Path, snapshot: RepositorySnapshot, claim: Claim, subject: Subject, run_id: str) -> ReplayPlan:
        start, _ = _extent(subject)
        unit_name = _unit_name(claim)
        manifest = _toml(root, "config/match-units.toml")
        units = manifest.get("units")
        if not isinstance(units, dict) or unit_name not in units or not isinstance(units[unit_name], dict):
            raise ReplayError(f"TH105 claim unit is absent from manifest: {unit_name}")
        unit = units[unit_name]
        if unit.get("kind") not in {"probe", "synthetic_island", "linked_candidate"}:
            raise ReplayError(f"TH105 driver does not yet attest unit kind {unit.get('kind')!r}")
        function = next(
            (item for item in unit.get("functions", []) if isinstance(item, dict) and str(item.get("address", "")).lower() == start.lower()),
            None,
        )
        if function is None:
            raise ReplayError(f"TH105 claim extent is absent from unit {unit_name}")
        build = _repo_file(root, "scripts/build.py")
        compare = _repo_file(root, "scripts/compare-function.py")
        output = str(unit["object"])
        argv = [sys.executable, str(compare.relative_to(root))]
        if function.get("contiguous_span"):
            argv.append("--contiguous-span")
        if function.get("symbol_base"):
            argv.extend(("--symbol-base", str(function["symbol_base"])))
        for mapping in function.get("rel32_targets", []):
            argv.extend(("--rel32-target", str(mapping)))
        for mapping in function.get("dir32_targets", []):
            argv.extend(("--dir32-target", str(mapping)))
        argv.extend(("--json", str(function["address"]), output))
        tool_root = Path(os.environ.get("TH105_MSVC8_ROOT", str(root / ".tools/msvc80-sp1"))).expanduser()
        specs = (
            ComponentSpec("vc8-bin", tool_root / "bin", "$TH105_MSVC8_ROOT/bin"),
            ComponentSpec("vc8-include", tool_root / "include", "$TH105_MSVC8_ROOT/include"),
            ComponentSpec("vc8-platformsdk-include", tool_root / "PlatformSDK/Include", "$TH105_MSVC8_ROOT/PlatformSDK/Include"),
            *_runtime_components(),
        )
        inputs = _identity_inputs(
            root,
            (
                "scripts/build.py",
                "scripts/workflow_manifest.py",
                "scripts/compile-unit.sh",
                "scripts/compare-function.py",
                "scripts/function_byte_ownership.py",
                "scripts/match_literals.py",
                "config/match-units.toml",
                "config/target.toml",
                "config/functions.csv",
                "config/reccmp-relocations.csv",
            ),
        )
        return ReplayPlan(
            self.driver_id,
            self.oracle_id,
            Coldness.FORCED_RECOMPILE,
            (
                ReplayStagePlan("compile", (sys.executable, str(build.relative_to(root)), "--unit", unit_name, "--json"), root),
                ReplayStagePlan("compare", tuple(argv), root),
            ),
            inputs,
            _repo_file(root, "resources/th105.exe"),
            specs,
            ("HOME", "PATH", "PYTHONPATH", "TH105_ENABLE_GS", "TH105_FP_MODE", "TH105_MSVC8_ROOT", "TH105_WINEPREFIX", "WINE", "WINEPREFIX"),
            metadata={
                "unit": unit_name,
                "proof_scope": "standalone-vc8-function-codegen",
                "does_not_prove": [
                    "ltcg-physical-ownership",
                    "linked-owner-layout",
                    "whole-image-closure",
                ],
            },
        )

    def decode(self, plan: ReplayPlan, claim: Claim, subject: Subject, executions: Sequence[RawExecution]) -> NativeOutcome:
        if len(executions) != 2 or executions[0].exit_code != 0:
            return NativeOutcome(Verdict.ERROR, 0, None, ("native-compile-stage-failed",))
        build_report = _json_stdout(executions[0])
        if build_report.get("result") != "ok" or not isinstance(build_report.get("build"), dict):
            return NativeOutcome(Verdict.ERROR, 0, build_report, ("native-build-provenance-missing",))
        build_provenance = build_report["build"]
        if (
            build_provenance.get("target_sha256") != file_sha256(plan.target_path)
            or not isinstance(build_provenance.get("input_digest"), str)
        ):
            return NativeOutcome(Verdict.ERROR, 0, build_report, ("native-build-provenance-unbound",))
        report = _json_stdout(executions[-1])
        if report.get("target_executable_sha256") != file_sha256(plan.target_path):
            return NativeOutcome(Verdict.ERROR, 0, report, ("native-target-binding-mismatch",))
        outcome = _decode_linear_function_report(report, subject, unit=None, size_key="target_size")
        combined = {"build": build_report, "comparison": report}
        return NativeOutcome(
            outcome.verdict,
            outcome.observed_bytes,
            combined,
            outcome.diagnostics,
            ("coff-relocation-resolution-v1", "target-data-relocation-allowlist-v1"),
            outcome.attestation,
        )


def _decode_linear_function_report(
    report: Mapping[str, Any],
    subject: Subject,
    *,
    unit: str | None,
    size_key: str,
) -> NativeOutcome:
    start, expected_size = _extent(subject)
    address = report.get("target_address", report.get("address"))
    size = report.get(size_key)
    if unit is not None and report.get("unit") != unit:
        return NativeOutcome(Verdict.INCOMPLETE, 0, report, ("native-unit-binding-mismatch",))
    if not isinstance(address, str) or int(address, 0) != int(start, 0):
        return NativeOutcome(Verdict.INCOMPLETE, 0, report, ("native-address-binding-mismatch",))
    if not isinstance(size, int) or size != expected_size:
        return NativeOutcome(Verdict.INCOMPLETE, 0, report, ("native-extent-binding-mismatch",))
    result = report.get("result")
    if result == "exact" and "matched_bytes" in report and report.get("matched_bytes") != expected_size:
        return NativeOutcome(Verdict.ERROR, 0, report, ("native-exact-count-inconsistent",))
    if result == "exact":
        verdict = Verdict.PASS
    elif result == "mismatch":
        verdict = Verdict.FAIL
    elif result in {"incomplete", "size-mismatch"}:
        verdict = Verdict.INCOMPLETE
    else:
        verdict = Verdict.ERROR
    return NativeOutcome(
        verdict,
        expected_size if verdict in {Verdict.PASS, Verdict.FAIL} else 0,
        report,
        () if verdict is Verdict.PASS else (f"native-result:{result}",),
        ("coff-relocation-resolution-v1",),
    )


BUILTIN_DRIVERS: tuple[ReplayDriver, ...] = (
    Th04OwnedExtentDriver(),
    Th08FunctionDriver(),
    Th095FunctionDriver(),
    Th095WholeBuildDriver(),
    Th105FunctionDriver(),
)


def select_driver(snapshot: RepositorySnapshot, claim: Claim) -> ReplayDriver:
    matches = [driver for driver in BUILTIN_DRIVERS if driver.supports(snapshot, claim)]
    if len(matches) != 1:
        raise ReplayError(
            f"claim {claim.id} has {len(matches)} factory replay drivers; exactly one is required"
        )
    return matches[0]
