"""Trusted service boundary around durable jobs and accepted factory knowledge."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import time
from typing import Any, Callable
import uuid

from .acceptance import build_acceptance_registry
from .adapters import inspect_repository
from .artifact_store import ArtifactStore
from .errors import (
    FactoryError,
    JobError,
    JobStateError,
    ReplayCancelled,
    ServiceConfigError,
)
from .jobs import JobOutcome, JobRecord, JobState, JobStore, ReplayJobSpec
from .knowledge import KnowledgeStatus, load_knowledge_catalog
from .ontology import Claim, ClaimType, RepositorySnapshot, to_primitive
from .oracle_receipts import SourceBinding, oracle_receipt_from_dict
from .regressions import load_fixture_suite
from .replay_drivers import ReplayPlan, driver_version, select_driver
from .replay_identity import capture_source_binding, repository_lock
from .replay_runner import (
    ReplayExpectation,
    ReplayRunner,
    runner_implementation_sha256,
)
from .service_config import RepositoryRegistration, ServiceConfig, load_service_config


@dataclass(frozen=True, slots=True)
class Page:
    total: int
    offset: int
    limit: int
    items: tuple[Any, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "offset": self.offset,
            "limit": self.limit,
            "next_offset": (
                self.offset + len(self.items)
                if self.offset + len(self.items) < self.total
                else None
            ),
            "items": [
                item.to_dict() if hasattr(item, "to_dict") else to_primitive(item)
                for item in self.items
            ],
        }


class FactoryService:
    """One short-lived view of an operator-controlled service configuration."""

    def __init__(self, config: ServiceConfig) -> None:
        self.config = config
        self.store = ArtifactStore(config.evidence_store)
        self.jobs = JobStore(config.database_path)

    @classmethod
    def from_path(cls, path: str | Path) -> FactoryService:
        return cls(load_service_config(path))

    def describe(self) -> dict[str, Any]:
        return self.config.public_dict()

    def list_repositories(self) -> tuple[dict[str, Any], ...]:
        return tuple(item.public_dict() for item in self.config.repositories)

    def inspect_repository(self, repository_id: str) -> dict[str, Any]:
        registration, snapshot = self._snapshot(repository_id)
        return {
            **registration.public_dict(),
            "project": to_primitive(snapshot.project),
            "input_fingerprint_sha256": snapshot.input_fingerprint_sha256,
            "targets": [to_primitive(item) for item in snapshot.targets],
            "counts": {
                "products": len(snapshot.products),
                "toolchains": len(snapshot.toolchains),
                "subjects": len(snapshot.subjects),
                "claims": len(snapshot.claims),
                "imported_oracle_results": len(snapshot.oracle_results),
                "diagnostics": len(snapshot.diagnostics),
            },
            "diagnostics": [to_primitive(item) for item in snapshot.diagnostics],
        }

    def list_claims(
        self,
        repository_id: str,
        *,
        claim_type: ClaimType | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Page:
        _page_bounds(limit, offset, maximum=100)
        _, snapshot = self._snapshot(repository_id)
        claims = tuple(
            sorted(
                (
                    item
                    for item in snapshot.claims
                    if claim_type is None or item.type is claim_type
                ),
                key=lambda item: item.id,
            )
        )
        subjects = {item.id: item for item in snapshot.subjects}
        items = tuple(
            {
                "claim": to_primitive(claim),
                "subject": to_primitive(subjects[claim.subject_id]),
            }
            for claim in claims[offset : offset + limit]
        )
        return Page(len(claims), offset, limit, items)

    def submit_replay(
        self,
        repository_id: str,
        claim_id: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        registration = self.config.repository(repository_id)
        with repository_lock(registration.path, exclusive=False):
            snapshot = inspect_repository(registration.path)
            self._validate_registration(registration, snapshot)
            claim = _one(snapshot.claims, claim_id, "claim")
            subject = _one(snapshot.subjects, claim.subject_id, "subject")
            if claim.target_identity_id not in registration.target_identity_ids:
                raise ServiceConfigError(
                    "claim target is outside the repository registration"
                )
            driver = select_driver(snapshot, claim)
            run_id = _new_run_id()
            plan = driver.prepare(
                registration.path,
                snapshot,
                claim,
                subject,
                run_id,
            )
            source = capture_source_binding(registration.path)
            self._require_policy_submission(snapshot.adapter_id, claim, plan, source)
            spec = ReplayJobSpec(
                repository_id=registration.id,
                repository_adapter_id=snapshot.adapter_id,
                target_identity_id=claim.target_identity_id,
                claim_id=claim.id,
                claim_type=claim.type,
                claim_sha256=_digest(claim),
                subject_id=subject.id,
                subject_sha256=_digest(subject),
                source_binding=source,
                policy_id=self.config.policy.id,
                policy_sha256=self.config.policy.sha256,
                configuration_sha256=self.config.sha256,
                driver_id=plan.driver_id,
                driver_version_sha256=driver_version(plan),
                oracle_id=plan.oracle_id,
                coldness=plan.coldness,
                runner_implementation_sha256=runner_implementation_sha256(),
                timeout_seconds=self.config.replay_timeout_seconds,
            )
        submission = self.jobs.submit(spec, idempotency_key)
        return {"reused": submission.reused, "job": submission.job.public_dict()}

    def get_job(self, job_id: str) -> dict[str, Any]:
        self.jobs.recover_expired()
        return self.jobs.get(job_id).public_dict()

    def list_jobs(
        self,
        *,
        state: JobState | None = None,
        repository_id: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        self.jobs.recover_expired()
        total, jobs = self.jobs.list(
            state=state,
            repository_id=repository_id,
            limit=limit,
            offset=offset,
        )
        return _page_dict(
            total,
            offset,
            limit,
            tuple(item.public_dict() for item in jobs),
        )

    def cancel_job(self, job_id: str, reason: str) -> dict[str, Any]:
        return self.jobs.cancel(job_id, reason).public_dict()

    def job_events(
        self, job_id: str, *, limit: int = 20, offset: int = 0
    ) -> dict[str, Any]:
        self.jobs.recover_expired()
        total, events = self.jobs.events(job_id, limit=limit, offset=offset)
        return _page_dict(
            total,
            offset,
            limit,
            tuple(item.to_dict() for item in events),
        )

    def accepted_registry(self) -> dict[str, Any]:
        return self._registry().to_dict()

    def accepted_snapshot(self, repository_id: str) -> dict[str, Any]:
        registration = self.config.repository(repository_id)
        snapshot = self._registry().materialize_live_snapshot(registration.path)
        return snapshot.to_dict()

    def accepted_facts(
        self,
        *,
        target_identity_id: str | None = None,
        claim_type: ClaimType | None = None,
        oracle_id: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        _page_bounds(limit, offset, maximum=100)
        registry = self._registry()
        facts = registry.accepted_facts(
            target_identity_id=target_identity_id,
            claim_type=claim_type,
            oracle_id=oracle_id,
        )
        return {
            "registry_id": registry.registry_id,
            **_page_dict(len(facts), offset, limit, facts[offset : offset + limit]),
        }

    def knowledge(
        self,
        *,
        status: KnowledgeStatus | None = None,
        scope: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        _page_bounds(limit, offset, maximum=100)
        entries = tuple(
            item
            for item in load_knowledge_catalog().entries
            if (status is None or item.status is status)
            and (scope is None or scope in item.scopes)
        )
        return _page_dict(
            len(entries),
            offset,
            limit,
            tuple(item.to_dict() for item in entries[offset : offset + limit]),
        )

    def fixtures(
        self,
        *,
        project: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        _page_bounds(limit, offset, maximum=100)
        fixtures = tuple(
            item
            for item in load_fixture_suite()
            if project is None or item.project == project
        )
        return _page_dict(
            len(fixtures),
            offset,
            limit,
            tuple(to_primitive(item) for item in fixtures[offset : offset + limit]),
        )

    def artifact_page(
        self,
        job_id: str,
        artifact_id: str | None,
        *,
        offset: int = 0,
        limit: int = 16384,
    ) -> dict[str, Any]:
        _page_bounds(limit, offset, maximum=65536)
        job = self.jobs.get(job_id)
        if job.state is not JobState.COMPLETED or job.outcome is None:
            raise JobError("job output is available only after receipt completion")
        receipt_path = (
            self.store.receipts
            / f"{job.outcome.receipt_id.removeprefix('receipt:')}.json"
        )
        document = self.store.verify_receipt_document(receipt_path)
        receipt = oracle_receipt_from_dict(document)
        artifacts = {item.id: item for item in receipt.artifacts}
        if artifact_id is None:
            return {
                "job_id": job_id,
                "receipt_id": receipt.receipt_id,
                "artifacts": [to_primitive(item) for item in receipt.artifacts],
            }
        artifact = artifacts.get(artifact_id)
        if artifact is None:
            raise JobError("artifact is not referenced by this job receipt")
        payload = self.store.read_verified_page(artifact, offset=offset, limit=limit)
        next_offset = offset + len(payload)
        result: dict[str, Any] = {
            "job_id": job_id,
            "receipt_id": receipt.receipt_id,
            "artifact": to_primitive(artifact),
            "offset": offset,
            "bytes_returned": len(payload),
            "next_offset": next_offset if next_offset < artifact.size else None,
        }
        if (
            artifact.media_type.startswith("text/")
            or artifact.media_type == "application/json"
        ):
            try:
                result["text"] = payload.decode("utf-8")
            except UnicodeDecodeError:
                result["base64"] = base64.b64encode(payload).decode("ascii")
        else:
            result["base64"] = base64.b64encode(payload).decode("ascii")
        return result

    def _snapshot(
        self, repository_id: str
    ) -> tuple[RepositoryRegistration, RepositorySnapshot]:
        registration = self.config.repository(repository_id)
        with repository_lock(registration.path, exclusive=False):
            snapshot = inspect_repository(registration.path)
            self._validate_registration(registration, snapshot)
            return registration, snapshot

    @staticmethod
    def _validate_registration(
        registration: RepositoryRegistration, snapshot: RepositorySnapshot
    ) -> None:
        if snapshot.adapter_id != registration.adapter_id:
            raise ServiceConfigError(
                f"repository {registration.id!r} adapter changed from "
                f"{registration.adapter_id!r} to {snapshot.adapter_id!r}"
            )
        observed_targets = {item.id for item in snapshot.targets}
        missing = set(registration.target_identity_ids) - observed_targets
        if missing:
            raise ServiceConfigError(
                "registered target identities are absent: " + ", ".join(sorted(missing))
            )

    def _require_policy_submission(
        self,
        adapter_id: str,
        claim: Claim,
        plan: ReplayPlan,
        source: SourceBinding,
    ) -> None:
        policy = self.config.policy
        violations = []
        if adapter_id not in policy.allowed_adapter_ids:
            violations.append("adapter-not-allowed")
        if claim.type not in policy.allowed_claim_types:
            violations.append("claim-type-not-allowed")
        if plan.driver_id not in policy.allowed_driver_ids:
            violations.append("driver-not-allowed")
        if plan.oracle_id not in policy.allowed_oracle_ids:
            violations.append("oracle-not-allowed")
        if plan.coldness not in policy.allowed_coldness:
            violations.append("coldness-not-allowed")
        if source.dirty and not policy.allow_dirty_source:
            violations.append("dirty-source-not-allowed")
        if violations:
            raise JobError(
                "replay request cannot satisfy the configured acceptance policy: "
                + ", ".join(sorted(violations))
            )

    def _registry(self):
        return build_acceptance_registry(
            self.store,
            self.config.policy,
            self.config.repository_map(),
        )


class ReplayWorker:
    """Single-job worker; multiple processes coordinate through SQLite leases."""

    def __init__(
        self,
        config_path: str | Path,
        *,
        worker_id: str | None = None,
        stop_requested: Callable[[], bool] | None = None,
    ) -> None:
        self.config_path = Path(config_path).expanduser().resolve(strict=True)
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex}"
        self.stop_requested = stop_requested or (lambda: False)

    def run_once(self) -> JobRecord | None:
        service = FactoryService.from_path(self.config_path)
        config = service.config
        job = service.jobs.claim_next(self.worker_id, config.worker_lease_seconds)
        if job is None:
            return None
        try:
            if service.jobs.cancellation_requested(job.job_id):
                return service.jobs.mark_cancelled(job.job_id, self.worker_id)
            if job.spec.configuration_sha256 != config.sha256:
                raise JobError(
                    "service configuration changed after submission; resubmit explicitly"
                )
            if (
                job.spec.policy_id != config.policy.id
                or job.spec.policy_sha256 != config.policy.sha256
            ):
                raise JobError(
                    "acceptance policy changed after submission; resubmit explicitly"
                )
            registration = config.repository(job.spec.repository_id)
            service.jobs.mark_running(job.job_id, self.worker_id, os.getpid())
            last_heartbeat = 0.0
            last_stage: str | None = None

            def cancelled() -> bool:
                return self.stop_requested() or service.jobs.cancellation_requested(
                    job.job_id
                )

            def progress(stage: str | None, pid: int | None) -> None:
                nonlocal last_heartbeat, last_stage
                now = time.monotonic()
                if (
                    stage != last_stage
                    or now - last_heartbeat >= config.worker_lease_seconds / 3
                ):
                    service.jobs.heartbeat(
                        job.job_id,
                        self.worker_id,
                        config.worker_lease_seconds,
                        current_stage=stage,
                        stage_pid=pid,
                    )
                    last_heartbeat = now
                    last_stage = stage

            expectation = ReplayExpectation(
                repository_adapter_id=job.spec.repository_adapter_id,
                target_identity_id=job.spec.target_identity_id,
                claim_id=job.spec.claim_id,
                claim_sha256=job.spec.claim_sha256,
                subject_id=job.spec.subject_id,
                subject_sha256=job.spec.subject_sha256,
                source_binding=job.spec.source_binding,
                driver_id=job.spec.driver_id,
                driver_version_sha256=job.spec.driver_version_sha256,
                oracle_id=job.spec.oracle_id,
                runner_implementation_sha256=job.spec.runner_implementation_sha256,
            )
            run = ReplayRunner(
                service.store,
                timeout_seconds=job.spec.timeout_seconds,
                expectation=expectation,
                cancel_requested=cancelled,
                on_stage_process=progress,
            ).run(registration.path, job.spec.claim_id)
            service.jobs.heartbeat(
                job.job_id,
                self.worker_id,
                config.worker_lease_seconds,
                current_stage=None,
                stage_pid=None,
            )
            current = load_service_config(self.config_path)
            if current.sha256 != job.spec.configuration_sha256:
                raise JobError(
                    "service configuration changed during replay; receipt was not promoted by this job"
                )
            registry = build_acceptance_registry(
                service.store,
                current.policy,
                current.repository_map(),
            )
            entries = [
                item
                for item in registry.entries
                if item.receipt_id == run.receipt.receipt_id
            ]
            if len(entries) != 1:
                raise JobError(
                    "completed receipt did not resolve to one registry entry"
                )
            entry = entries[0]
            result = JobOutcome(
                receipt_id=run.receipt.receipt_id,
                receipt_verdict=run.receipt.result.verdict,
                acceptance_decision=entry.decision.value,
                acceptance_reasons=entry.reasons,
                registry_id=registry.registry_id,
            )
            return service.jobs.complete(job.job_id, self.worker_id, result)
        except ReplayCancelled as error:
            current = service.jobs.get(job.job_id)
            if current.state is JobState.CANCEL_REQUESTED:
                try:
                    return service.jobs.mark_cancelled(job.job_id, self.worker_id)
                except JobStateError:
                    current = service.jobs.get(job.job_id)
                    if current.state.terminal:
                        return current
                    raise
            return _fail_owned_job(
                service,
                job,
                self.worker_id,
                error_code="worker-stopped",
                error_message=str(error),
            )
        except (FactoryError, OSError, TypeError, ValueError) as error:
            return _fail_owned_job(
                service,
                job,
                self.worker_id,
                error_code="replay-failed",
                error_message=f"{type(error).__name__}: {error}",
            )


def _new_run_id() -> str:
    return (
        "factory-"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-")
        + uuid.uuid4().hex[:12]
    )


def _fail_owned_job(
    service: FactoryService,
    job: JobRecord,
    worker_id: str,
    *,
    error_code: str,
    error_message: str,
) -> JobRecord:
    current = service.jobs.get(job.job_id)
    if current.state.terminal:
        return current
    try:
        return service.jobs.fail(
            job.job_id,
            worker_id,
            error_code=error_code,
            error_message=error_message,
        )
    except JobStateError:
        current = service.jobs.get(job.job_id)
        if current.state.terminal:
            return current
        raise


def _one(values: tuple[Any, ...], wanted: str, noun: str):
    matches = [value for value in values if value.id == wanted]
    if len(matches) != 1:
        raise JobError(f"{noun} {wanted!r} resolved to {len(matches)} objects")
    return matches[0]


def _digest(value: Any) -> str:
    from .oracle_receipts import canonical_sha256

    return canonical_sha256(to_primitive(value))


def _page_bounds(limit: int, offset: int, *, maximum: int) -> None:
    if (
        not isinstance(limit, int)
        or isinstance(limit, bool)
        or not 1 <= limit <= maximum
    ):
        raise JobError(f"limit must be an integer from 1 through {maximum}")
    if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
        raise JobError("offset must be a non-negative integer")


def _page_dict(
    total: int,
    offset: int,
    limit: int,
    items: tuple[Any, ...],
) -> dict[str, Any]:
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "next_offset": offset + len(items) if offset + len(items) < total else None,
        "items": list(items),
    }
