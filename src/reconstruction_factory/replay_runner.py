"""Controlled replay execution, receipt construction, and live freshness checks."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import fcntl
import os
from pathlib import Path
import re
import signal
import subprocess
import tempfile
import time
from typing import Iterator, Mapping
import uuid

from .adapters import inspect_repository
from .artifact_store import ArtifactStore
from .errors import ReplayError
from .ontology import (
    ArtifactRef,
    Claim,
    Coverage,
    OracleResult,
    OracleRole,
    RepositorySnapshot,
    Subject,
    TargetIdentity,
    ToolchainIdentity,
    Verdict,
    to_primitive,
)
from .oracle_receipts import (
    AttestationLevel,
    ClaimBinding,
    Coldness,
    InvocationBinding,
    InvocationStage,
    OracleReceipt,
    StageExecution,
    TargetBinding,
    ToolchainBinding,
    canonical_sha256,
)
from .replay_drivers import (
    NativeOutcome,
    RawExecution,
    ReplayDriver,
    ReplayPlan,
    ReplayStagePlan,
    driver_version,
    select_driver,
)
from .replay_identity import (
    capture_source_binding,
    environment_binding,
    file_sha256,
    observe_component,
)


@dataclass(frozen=True, slots=True)
class ReplayRun:
    receipt: OracleReceipt
    receipt_path: Path


class ReplayRunner:
    def __init__(self, store: ArtifactStore, *, timeout_seconds: int = 1800) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.store = store
        self.timeout_seconds = timeout_seconds

    def run(self, repository: str | Path, claim_id: str) -> ReplayRun:
        root = Path(repository).expanduser().resolve(strict=True)
        with self._repository_lock(root):
            snapshot = inspect_repository(root)
            claim = _one(snapshot.claims, claim_id, "claim")
            subject = _one(snapshot.subjects, claim.subject_id, "subject")
            target = _one(snapshot.targets, claim.target_identity_id, "target")
            if claim.toolchain_identity_id is None:
                raise ReplayError(f"claim {claim.id} has no toolchain identity")
            toolchain = _one(
                snapshot.toolchains,
                claim.toolchain_identity_id,
                "toolchain",
            )
            driver = select_driver(snapshot, claim)
            run_id = (
                "factory-"
                + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-")
                + uuid.uuid4().hex[:12]
            )
            plan = driver.prepare(root, snapshot, claim, subject, run_id)
            return self._run_locked(
                root,
                snapshot,
                claim,
                subject,
                target,
                toolchain,
                driver,
                plan,
                run_id,
            )

    def _run_locked(
        self,
        root: Path,
        snapshot: RepositorySnapshot,
        claim: Claim,
        subject: Subject,
        target: TargetIdentity,
        toolchain: ToolchainIdentity,
        driver: ReplayDriver,
        plan: ReplayPlan,
        run_id: str,
    ) -> ReplayRun:
        source_before = capture_source_binding(root)
        target_before_sha256, target_before_size = _observe_target(plan.target_path)
        components_before, component_errors_before = _observe_components(plan)
        environment_names, environment_sha256 = environment_binding(
            plan.environment_names
        )
        runner_implementation_before = _runner_implementation_sha256()
        version = driver_version(plan)
        claim_sha256 = canonical_sha256(to_primitive(claim))
        subject_sha256 = canonical_sha256(to_primitive(subject))
        component_digest_before = canonical_sha256(to_primitive(components_before))

        stage_bindings = _bind_stages(
            root,
            plan,
            claim_sha256=claim_sha256,
            subject_sha256=subject_sha256,
            source_sha256=source_before.snapshot_sha256,
            target_sha256=target_before_sha256,
            components_sha256=component_digest_before,
            environment_names=environment_names,
            environment_sha256=environment_sha256,
            runner_sha256=runner_implementation_before,
            driver_sha256=version,
        )

        raw_executions: list[RawExecution] = []
        preflight_errors = list(component_errors_before)
        if target_before_sha256 != target.sha256 or target_before_size != target.size:
            preflight_errors.append("target-identity-mismatch-before-replay")
        if not preflight_errors:
            for stage in plan.stages:
                execution = self._execute_stage(stage)
                raw_executions.append(execution)
                if execution.timed_out or execution.exit_code != 0:
                    break

        try:
            outcome = (
                driver.decode(plan, claim, subject, raw_executions)
                if raw_executions
                else NativeOutcome(
                    Verdict.ERROR,
                    0,
                    None,
                    tuple(preflight_errors or ("replay-not-started",)),
                    attestation=AttestationLevel.UNKNOWN,
                )
            )
        except (KeyError, OSError, TypeError, ValueError, ReplayError) as error:
            outcome = NativeOutcome(
                Verdict.ERROR,
                0,
                None,
                (f"native-output-invalid:{error}",),
                attestation=AttestationLevel.UNKNOWN,
            )

        source_after = capture_source_binding(root)
        runner_implementation_after = _runner_implementation_sha256()
        target_after_sha256, target_after_size = _observe_target(plan.target_path)
        components_after, component_errors_after = _observe_components(plan)
        component_digest_before = canonical_sha256(to_primitive(components_before))
        component_digest_after = canonical_sha256(to_primitive(components_after))

        artifacts: list[ArtifactRef] = []
        executions: list[StageExecution] = []
        for raw in raw_executions:
            stdout = self.store.add_bytes(
                raw.stdout,
                media_type="text/plain; charset=utf-8",
                producer=f"{plan.driver_id}:{raw.stage_id}:stdout",
            )
            stderr = self.store.add_bytes(
                raw.stderr,
                media_type="text/plain; charset=utf-8",
                producer=f"{plan.driver_id}:{raw.stage_id}:stderr",
            )
            artifacts.extend((stdout, stderr))
            executions.append(
                StageExecution(
                    stage_id=raw.stage_id,
                    exit_code=raw.exit_code,
                    timed_out=raw.timed_out,
                    duration_ms=raw.duration_ms,
                    stdout_ref=stdout.id,
                    stderr_ref=stderr.id,
                )
            )

        native_report_ref: str | None = None
        if outcome.report is not None:
            native_report = self.store.add_json(
                outcome.report,
                producer=f"{plan.driver_id}:native-report",
            )
            artifacts.append(native_report)
            native_report_ref = native_report.id
        artifacts = list(_unique_artifacts(artifacts))

        errors = set(preflight_errors)
        errors.update(component_errors_after)
        if source_before != source_after:
            errors.add("source-mutated-during-replay")
        if runner_implementation_before != runner_implementation_after:
            errors.add("runner-mutated-during-replay")
        if (
            target_before_sha256 != target_after_sha256
            or target_before_size != target_after_size
        ):
            errors.add("target-mutated-during-replay")
        if target_after_sha256 != target.sha256 or target_after_size != target.size:
            errors.add("target-identity-mismatch-after-replay")
        if component_digest_before != component_digest_after:
            errors.add("toolchain-mutated-during-replay")
        if any(item.timed_out for item in raw_executions):
            errors.add("replay-stage-timed-out")
        if outcome.verdict is Verdict.PASS and any(
            item.exit_code != 0 for item in raw_executions
        ):
            errors.add("replay-stage-nonzero-on-native-pass")
        expected_bytes = sum(item.size for item in subject.extents)
        complete = (
            expected_bytes > 0
            and outcome.observed_bytes == expected_bytes
            and outcome.verdict in {Verdict.PASS, Verdict.FAIL}
        )
        if outcome.verdict is Verdict.PASS and not complete:
            errors.add("native-coverage-incomplete")
        if plan.coldness in {Coldness.INCREMENTAL, Coldness.UNKNOWN}:
            errors.add("replay-coldness-insufficient")
        effective_attestation = (
            outcome.attestation
            if components_before and not component_errors_before
            else AttestationLevel.UNKNOWN
        )
        if outcome.verdict is Verdict.PASS and effective_attestation is AttestationLevel.UNKNOWN:
            errors.add("identity-attestation-incomplete")

        verdict = outcome.verdict
        integrity_errors = {
            value
            for value in errors
            if value.startswith(
                ("source-", "target-", "toolchain-", "runner-", "replay-stage-")
            )
        }
        if integrity_errors:
            verdict = Verdict.ERROR
        elif verdict is Verdict.PASS and errors:
            verdict = Verdict.INCOMPLETE

        evidence_refs = tuple(artifact.id for artifact in artifacts)
        duration_ms = sum(item.duration_ms for item in raw_executions)
        result = OracleResult(
            id="result:" + run_id.lower(),
            oracle_id=plan.oracle_id,
            oracle_version=version,
            role=OracleRole.ACCEPTANCE,
            claim_id=claim.id,
            claim_type=claim.type,
            target_identity_id=target.id,
            toolchain_identity_id=toolchain.id,
            source_tree=source_before.snapshot_sha256,
            coverage=Coverage(
                domain="claimed-bytes",
                expected_units=expected_bytes,
                observed_units=outcome.observed_bytes,
                complete=complete,
                notes="Coverage is the sum of every extent bound by the normalized subject.",
            ),
            verdict=verdict,
            evidence_refs=evidence_refs,
            normalizations=outcome.normalizations,
            diagnostics=tuple(sorted(set((*outcome.diagnostics, *errors)))),
            duration_ms=duration_ms,
        )
        receipt = OracleReceipt(
            receipt_id="",
            created_utc=datetime.now(timezone.utc).isoformat(),
            repository_adapter_id=snapshot.adapter_id,
            oracle_id=plan.oracle_id,
            oracle_version=version,
            claim=ClaimBinding(
                claim_id=claim.id,
                claim_type=claim.type.value,
                claim_sha256=claim_sha256,
                subject_id=subject.id,
                subject_sha256=subject_sha256,
                extents=subject.extents,
            ),
            source_before=source_before,
            source_after=source_after,
            target=TargetBinding(
                identity_id=target.id,
                repository_path=plan.target_path.relative_to(root).as_posix(),
                declared_sha256=target.sha256,
                observed_before_sha256=target_before_sha256,
                observed_after_sha256=target_after_sha256,
                declared_size=target.size,
                observed_before_size=target_before_size,
                observed_after_size=target_after_size,
            ),
            toolchain=ToolchainBinding(
                identity_id=toolchain.id,
                declared_fingerprint_sha256=toolchain.fingerprint_sha256,
                attestation=effective_attestation,
                components=components_before,
                components_sha256=component_digest_before,
                observed_after_sha256=component_digest_after,
                environment_sha256=environment_sha256,
                environment_names=environment_names,
            ),
            invocation=InvocationBinding(
                driver_id=plan.driver_id,
                driver_version=version,
                coldness=plan.coldness,
                stages=stage_bindings,
                executions=tuple(executions),
            ),
            result=result,
            artifacts=tuple(artifacts),
            native_report_ref=native_report_ref,
            acceptance_errors=tuple(sorted(errors)),
            runner_implementation_sha256=runner_implementation_before,
            runner_observed_after_sha256=runner_implementation_after,
            metadata={
                "run_id": run_id,
                "native_report_kind": (
                    "structured" if native_report_ref is not None else "absent"
                ),
                "driver": to_primitive(plan.metadata),
            },
        ).seal()
        path = self.store.write_receipt(receipt)
        return ReplayRun(receipt, path)

    def _execute_stage(self, stage: ReplayStagePlan) -> RawExecution:
        environment = os.environ.copy()
        environment.update(stage.environment)
        started = time.monotonic()
        with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            process = subprocess.Popen(
                stage.argv,
                cwd=stage.cwd,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                start_new_session=True,
            )
            timed_out = False
            exit_code: int | None
            try:
                exit_code = process.wait(timeout=self.timeout_seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                exit_code = None
            duration_ms = round((time.monotonic() - started) * 1000)
            stdout.seek(0)
            stderr.seek(0)
            return RawExecution(
                stage.id,
                exit_code,
                timed_out,
                duration_ms,
                stdout.read(),
                stderr.read(),
            )

    @contextmanager
    def _repository_lock(self, repository: Path) -> Iterator[None]:
        try:
            raw_path = subprocess.check_output(
                [
                    "git",
                    "-C",
                    str(repository),
                    "rev-parse",
                    "--git-path",
                    "reconstruction-factory-replay.lock",
                ],
                stderr=subprocess.PIPE,
                text=True,
            ).strip()
        except subprocess.CalledProcessError as error:
            detail = error.stderr.strip()
            raise ReplayError(f"cannot resolve repository replay lock: {detail}") from error
        path = Path(raw_path)
        if not path.is_absolute():
            path = repository / path
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a+b") as stream:
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise ReplayError(f"another factory replay owns {repository}") from error
            try:
                yield
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)


def verify_live_freshness(
    document: Mapping[str, object], repository: str | Path
) -> tuple[str, ...]:
    """Compare a verified receipt document with the current normalized graph."""

    root = Path(repository).expanduser().resolve(strict=True)
    snapshot = inspect_repository(root)
    errors: list[str] = []
    if document.get("repository_adapter_id") != snapshot.adapter_id:
        errors.append("adapter-id-changed")
    current_runner = _runner_implementation_sha256()
    if document.get("runner_implementation_sha256") != current_runner:
        errors.append("runner-implementation-stale")
    claim_doc = document.get("claim")
    if not isinstance(claim_doc, dict):
        return ("claim-binding-malformed",)
    metadata = document.get("metadata")
    run_id = metadata.get("run_id") if isinstance(metadata, dict) else None
    if not isinstance(run_id, str) or not re.fullmatch(
        r"factory-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{12}", run_id
    ):
        return ("receipt-run-id-malformed",)
    claim_id = claim_doc.get("claim_id")
    try:
        claim = _one(snapshot.claims, claim_id, "claim")
        subject = _one(snapshot.subjects, claim.subject_id, "subject")
        target = _one(snapshot.targets, claim.target_identity_id, "target")
        if claim.toolchain_identity_id is None:
            raise ReplayError("claim has no toolchain identity")
        toolchain = _one(snapshot.toolchains, claim.toolchain_identity_id, "toolchain")
        driver = select_driver(snapshot, claim)
        plan = driver.prepare(root, snapshot, claim, subject, run_id)
    except ReplayError:
        return ("claim-subject-or-driver-absent",)
    claim_sha256 = canonical_sha256(to_primitive(claim))
    subject_sha256 = canonical_sha256(to_primitive(subject))
    if claim_doc.get("claim_sha256") != claim_sha256:
        errors.append("claim-changed")
    if claim_doc.get("subject_sha256") != subject_sha256:
        errors.append("subject-or-extents-changed")
    source_doc = document.get("source_after")
    current_source = capture_source_binding(root)
    if not isinstance(source_doc, dict) or source_doc != to_primitive(current_source):
        errors.append("source-snapshot-stale")
    target_doc = document.get("target")
    current_target_sha256, current_target_size = _observe_target(plan.target_path)
    expected_target_path = plan.target_path.relative_to(root).as_posix()
    if not isinstance(target_doc, dict):
        errors.append("target-binding-malformed")
    else:
        if (
            target_doc.get("identity_id") != target.id
            or target_doc.get("repository_path") != expected_target_path
            or target_doc.get("declared_sha256") != target.sha256
            or target_doc.get("declared_size") != target.size
        ):
            errors.append("normalized-target-identity-changed")
        if (
            target_doc.get("observed_after_sha256") != current_target_sha256
            or target_doc.get("observed_after_size") != current_target_size
        ):
            errors.append("target-binding-stale")
    if current_target_sha256 != target.sha256 or current_target_size != target.size:
        errors.append("normalized-target-identity-changed")
    toolchain_doc = document.get("toolchain")
    current_components, component_errors = _observe_components(plan)
    current_component_digest = canonical_sha256(to_primitive(current_components))
    current_environment_names, current_environment = environment_binding(
        plan.environment_names
    )
    if not isinstance(toolchain_doc, dict):
        errors.append("toolchain-binding-malformed")
    else:
        if toolchain_doc.get("identity_id") != toolchain.id:
            errors.append("toolchain-identity-changed")
        if toolchain_doc.get("declared_fingerprint_sha256") != toolchain.fingerprint_sha256:
            errors.append("toolchain-declaration-changed")
        if (
            component_errors
            or current_component_digest != toolchain_doc.get("observed_after_sha256")
        ):
            errors.append("toolchain-surface-stale")
        if toolchain_doc.get("environment_names") != list(current_environment_names):
            errors.append("toolchain-environment-declaration-stale")
        if current_environment != toolchain_doc.get("environment_sha256"):
            errors.append("toolchain-environment-stale")
    invocation_doc = document.get("invocation")
    current_version = driver_version(plan)
    if document.get("oracle_id") != plan.oracle_id:
        errors.append("oracle-id-changed")
    if document.get("oracle_version") != current_version:
        errors.append("oracle-version-stale")
    if (
        not isinstance(invocation_doc, dict)
        or invocation_doc.get("driver_id") != plan.driver_id
        or invocation_doc.get("driver_version") != current_version
    ):
        errors.append("driver-version-stale")
    else:
        current_stages = _bind_stages(
            root,
            plan,
            claim_sha256=claim_sha256,
            subject_sha256=subject_sha256,
            source_sha256=current_source.snapshot_sha256,
            target_sha256=current_target_sha256,
            components_sha256=current_component_digest,
            environment_names=current_environment_names,
            environment_sha256=current_environment,
            runner_sha256=current_runner,
            driver_sha256=current_version,
        )
        if invocation_doc.get("stages") != to_primitive(current_stages):
            errors.append("invocation-plan-stale")
    return tuple(sorted(set(errors)))


def _runner_implementation_sha256() -> str:
    """Hash the factory Python implementation that can affect replay semantics."""

    package_root = Path(__file__).resolve(strict=True).parent
    records = []
    for path in sorted(package_root.rglob("*.py")):
        if path.is_symlink() or not path.is_file():
            raise ReplayError(f"runner implementation input is not a regular file: {path}")
        records.append(
            {
                "path": path.relative_to(package_root).as_posix(),
                "sha256": file_sha256(path),
                "size": path.stat().st_size,
            }
        )
    if not records:
        raise ReplayError("runner implementation contains no Python sources")
    return canonical_sha256(records)


def _bind_stages(
    root: Path,
    plan: ReplayPlan,
    *,
    claim_sha256: str,
    subject_sha256: str,
    source_sha256: str,
    target_sha256: str,
    components_sha256: str,
    environment_names: tuple[str, ...],
    environment_sha256: str,
    runner_sha256: str,
    driver_sha256: str,
) -> tuple[InvocationStage, ...]:
    allowed_environment = set(environment_names)
    bindings = []
    for stage in plan.stages:
        undeclared = set(stage.environment) - allowed_environment
        if undeclared:
            raise ReplayError(
                f"stage {stage.id} overrides undeclared environment names: "
                + ", ".join(sorted(undeclared))
            )
        effective_environment = {
            name: stage.environment.get(name, os.environ.get(name))
            for name in environment_names
        }
        stage_environment_sha256 = canonical_sha256(effective_environment)
        cwd = _relative_cwd(root, stage.cwd)
        stage_record = {
            "id": stage.id,
            "argv": stage.argv,
            "cwd": cwd,
            "environment_sha256": stage_environment_sha256,
        }
        bindings.append(
            InvocationStage(
                id=stage.id,
                argv=stage.argv,
                cwd=cwd,
                environment_sha256=stage_environment_sha256,
                input_sha256=canonical_sha256(
                    {
                        "claim_sha256": claim_sha256,
                        "subject_sha256": subject_sha256,
                        "source_sha256": source_sha256,
                        "target_sha256": target_sha256,
                        "toolchain_components_sha256": components_sha256,
                        "environment_sha256": environment_sha256,
                        "runner_implementation_sha256": runner_sha256,
                        "driver_version": driver_sha256,
                        "stage": stage_record,
                    }
                ),
            )
        )
    return tuple(bindings)


def _observe_target(path: Path) -> tuple[str, int]:
    resolved = path.resolve(strict=True)
    if not resolved.is_file():
        raise ReplayError(f"target is not a file: {path}")
    return file_sha256(resolved), resolved.stat().st_size


def _observe_components(plan: ReplayPlan) -> tuple[tuple, tuple[str, ...]]:
    components = []
    errors = []
    for spec in plan.toolchain_components:
        try:
            components.append(
                observe_component(
                    spec.id,
                    spec.path,
                    logical_path=spec.logical_path,
                    kind=spec.kind,
                )
            )
        except (OSError, ReplayError) as error:
            errors.append(f"toolchain-component-unavailable:{spec.id}:{error}")
    return tuple(sorted(components, key=lambda item: item.id)), tuple(errors)


def _unique_artifacts(values: list[ArtifactRef]) -> Iterator[ArtifactRef]:
    seen: set[str] = set()
    for value in values:
        if value.id not in seen:
            seen.add(value.id)
            yield value


def _relative_cwd(root: Path, cwd: Path) -> str:
    resolved = cwd.resolve(strict=True)
    if not resolved.is_relative_to(root):
        raise ReplayError("replay stage cwd escapes repository")
    return resolved.relative_to(root).as_posix() or "."


def _one(values: tuple, wanted: object, noun: str):
    matches = [value for value in values if value.id == wanted]
    if len(matches) != 1:
        raise ReplayError(f"{noun} {wanted!r} resolved to {len(matches)} objects")
    return matches[0]
