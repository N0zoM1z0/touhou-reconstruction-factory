"""SQLite-backed durable state machine for factory replay jobs."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
import json
from pathlib import Path
import re
import sqlite3
from typing import Any, Callable, Iterator, Mapping
import uuid

from .errors import JobConflictError, JobError, JobStateError, ValidationError
from .ontology import ClaimType, Verdict, to_primitive
from .oracle_receipts import Coldness, SourceBinding, canonical_sha256


JOB_SCHEMA_VERSION = 1
_JOB_ID = re.compile(r"^job:[0-9a-f]{32}$")
_IDEMPOTENCY_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class JobKind(str, Enum):
    REPLAY_CLAIM = "replay-claim"


class JobState(str, Enum):
    QUEUED = "queued"
    LEASED = "leased"
    RUNNING = "running"
    CANCEL_REQUESTED = "cancel-requested"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def terminal(self) -> bool:
        return self in {self.COMPLETED, self.FAILED, self.CANCELLED}


@dataclass(frozen=True, slots=True)
class ReplayJobSpec:
    """Immutable request binding captured before a replay enters the queue."""

    repository_id: str
    repository_adapter_id: str
    target_identity_id: str
    claim_id: str
    claim_type: ClaimType
    claim_sha256: str
    subject_id: str
    subject_sha256: str
    source_binding: SourceBinding
    policy_id: str
    policy_sha256: str
    configuration_sha256: str
    driver_id: str
    driver_version_sha256: str
    oracle_id: str
    coldness: Coldness
    runner_implementation_sha256: str
    timeout_seconds: int
    kind: JobKind = JobKind.REPLAY_CLAIM
    schema_version: int = JOB_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for label, value in (
            ("repository_id", self.repository_id),
            ("repository_adapter_id", self.repository_adapter_id),
            ("target_identity_id", self.target_identity_id),
            ("claim_id", self.claim_id),
            ("subject_id", self.subject_id),
            ("policy_id", self.policy_id),
            ("driver_id", self.driver_id),
            ("oracle_id", self.oracle_id),
        ):
            _require_identifier(value, label)
        for label, value in (
            ("claim_sha256", self.claim_sha256),
            ("subject_sha256", self.subject_sha256),
            ("policy_sha256", self.policy_sha256),
            ("configuration_sha256", self.configuration_sha256),
            ("driver_version_sha256", self.driver_version_sha256),
            ("runner_implementation_sha256", self.runner_implementation_sha256),
        ):
            _require_sha256(value, label)
        if not isinstance(self.claim_type, ClaimType):
            raise ValidationError("job claim_type must use the claim vocabulary")
        if not isinstance(self.kind, JobKind) or self.kind is not JobKind.REPLAY_CLAIM:
            raise ValidationError("unsupported job kind")
        if not isinstance(self.coldness, Coldness):
            raise ValidationError("job coldness must use the replay vocabulary")
        if (
            not isinstance(self.timeout_seconds, int)
            or isinstance(self.timeout_seconds, bool)
            or self.timeout_seconds <= 0
        ):
            raise ValidationError("job timeout_seconds must be a positive integer")
        if (
            not isinstance(self.schema_version, int)
            or isinstance(self.schema_version, bool)
            or self.schema_version != JOB_SCHEMA_VERSION
        ):
            raise ValidationError("unsupported replay job schema version")

    @property
    def sha256(self) -> str:
        return canonical_sha256(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> ReplayJobSpec:
        required = {
            "repository_id",
            "repository_adapter_id",
            "target_identity_id",
            "claim_id",
            "claim_type",
            "claim_sha256",
            "subject_id",
            "subject_sha256",
            "source_binding",
            "policy_id",
            "policy_sha256",
            "configuration_sha256",
            "driver_id",
            "driver_version_sha256",
            "oracle_id",
            "coldness",
            "runner_implementation_sha256",
            "timeout_seconds",
            "kind",
            "schema_version",
        }
        _exact_keys(value, required, "replay job spec")
        source = _object(value["source_binding"], "source_binding")
        _exact_keys(
            source,
            {
                "git_commit",
                "git_tree",
                "repository_scope",
                "snapshot_sha256",
                "file_count",
                "dirty",
                "untracked_files",
            },
            "source_binding",
        )
        try:
            return cls(
                repository_id=value["repository_id"],
                repository_adapter_id=value["repository_adapter_id"],
                target_identity_id=value["target_identity_id"],
                claim_id=value["claim_id"],
                claim_type=ClaimType(value["claim_type"]),
                claim_sha256=value["claim_sha256"],
                subject_id=value["subject_id"],
                subject_sha256=value["subject_sha256"],
                source_binding=SourceBinding(**source),
                policy_id=value["policy_id"],
                policy_sha256=value["policy_sha256"],
                configuration_sha256=value["configuration_sha256"],
                driver_id=value["driver_id"],
                driver_version_sha256=value["driver_version_sha256"],
                oracle_id=value["oracle_id"],
                coldness=Coldness(value["coldness"]),
                runner_implementation_sha256=value["runner_implementation_sha256"],
                timeout_seconds=value["timeout_seconds"],
                kind=JobKind(value["kind"]),
                schema_version=value["schema_version"],
            )
        except (TypeError, ValueError) as error:
            if isinstance(error, ValidationError):
                raise
            raise ValidationError(f"invalid replay job spec: {error}") from error


@dataclass(frozen=True, slots=True)
class JobOutcome:
    """Receipt and acceptance result produced by a completed job."""

    receipt_id: str
    receipt_verdict: Verdict
    acceptance_decision: str
    acceptance_reasons: tuple[str, ...]
    registry_id: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"receipt:[0-9a-f]{64}", self.receipt_id):
            raise ValidationError("job outcome receipt_id is invalid")
        if not isinstance(self.receipt_verdict, Verdict):
            raise ValidationError("job outcome verdict must use the verdict vocabulary")
        if self.acceptance_decision not in {"accepted", "rejected", "invalid"}:
            raise ValidationError("job outcome acceptance decision is invalid")
        if tuple(sorted(set(self.acceptance_reasons))) != self.acceptance_reasons:
            raise ValidationError(
                "job outcome acceptance reasons must be sorted and unique"
            )
        if self.acceptance_decision == "accepted" and self.acceptance_reasons:
            raise ValidationError(
                "accepted job outcome cannot contain rejection reasons"
            )
        if self.acceptance_decision != "accepted" and not self.acceptance_reasons:
            raise ValidationError("non-accepted job outcome requires reasons")
        if not re.fullmatch(r"registry:[0-9a-f]{64}", self.registry_id):
            raise ValidationError("job outcome registry_id is invalid")

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> JobOutcome:
        _exact_keys(
            value,
            {
                "receipt_id",
                "receipt_verdict",
                "acceptance_decision",
                "acceptance_reasons",
                "registry_id",
            },
            "job outcome",
        )
        reasons = value["acceptance_reasons"]
        if not isinstance(reasons, list) or any(
            not isinstance(reason, str) for reason in reasons
        ):
            raise ValidationError("job outcome acceptance_reasons must be an array")
        try:
            return cls(
                receipt_id=value["receipt_id"],
                receipt_verdict=Verdict(value["receipt_verdict"]),
                acceptance_decision=value["acceptance_decision"],
                acceptance_reasons=tuple(reasons),
                registry_id=value["registry_id"],
            )
        except (TypeError, ValueError) as error:
            if isinstance(error, ValidationError):
                raise
            raise ValidationError(f"invalid job outcome: {error}") from error


@dataclass(frozen=True, slots=True)
class JobRecord:
    job_id: str
    idempotency_key: str
    spec_sha256: str
    spec: ReplayJobSpec
    state: JobState
    attempt: int
    created_utc: str
    updated_utc: str
    started_utc: str | None = None
    finished_utc: str | None = None
    lease_owner: str | None = None
    lease_expires_utc: str | None = None
    worker_pid: int | None = None
    current_stage: str | None = None
    stage_pid: int | None = None
    cancellation_reason: str | None = None
    outcome: JobOutcome | None = None
    error_code: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        if not _JOB_ID.fullmatch(self.job_id):
            raise ValidationError("job_id must be a normalized random identity")
        _require_idempotency_key(self.idempotency_key)
        _require_sha256(self.spec_sha256, "spec_sha256")
        if self.spec_sha256 != self.spec.sha256:
            raise ValidationError("stored job spec digest differs from its contents")
        if not isinstance(self.state, JobState):
            raise ValidationError("job state must use the state vocabulary")
        if (
            not isinstance(self.attempt, int)
            or isinstance(self.attempt, bool)
            or self.attempt < 0
        ):
            raise ValidationError("job attempt must be a non-negative integer")
        for label, value in (
            ("created_utc", self.created_utc),
            ("updated_utc", self.updated_utc),
        ):
            _require_utc(value, label)
        for label, value in (
            ("started_utc", self.started_utc),
            ("finished_utc", self.finished_utc),
            ("lease_expires_utc", self.lease_expires_utc),
        ):
            if value is not None:
                _require_utc(value, label)
        for label, value in (
            ("worker_pid", self.worker_pid),
            ("stage_pid", self.stage_pid),
        ):
            if value is not None and (
                not isinstance(value, int) or isinstance(value, bool) or value <= 0
            ):
                raise ValidationError(f"{label} must be a positive integer")
        active = self.state in {
            JobState.LEASED,
            JobState.RUNNING,
            JobState.CANCEL_REQUESTED,
        }
        if active != bool(self.lease_owner and self.lease_expires_utc):
            raise ValidationError("active job lease fields are inconsistent")
        if self.state is JobState.RUNNING and (
            self.started_utc is None or self.worker_pid is None
        ):
            raise ValidationError("running job requires start time and worker PID")
        if self.state.terminal != (self.finished_utc is not None):
            raise ValidationError("terminal job finish time is inconsistent")
        if (self.state is JobState.COMPLETED) != (self.outcome is not None):
            raise ValidationError("completed job outcome is inconsistent")
        if self.state is JobState.FAILED and not (
            self.error_code and self.error_message
        ):
            raise ValidationError("failed job requires an error code and message")
        if self.state is not JobState.FAILED and (
            self.error_code or self.error_message
        ):
            raise ValidationError("only failed jobs may contain errors")
        if (
            self.state in {JobState.CANCEL_REQUESTED, JobState.CANCELLED}
            and not self.cancellation_reason
        ):
            raise ValidationError("cancelled job requires a cancellation reason")

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "idempotency_key": self.idempotency_key,
            "spec_sha256": self.spec_sha256,
            "spec": self.spec.to_dict(),
            "state": self.state.value,
            "attempt": self.attempt,
            "created_utc": self.created_utc,
            "updated_utc": self.updated_utc,
            "started_utc": self.started_utc,
            "finished_utc": self.finished_utc,
            "lease_expires_utc": self.lease_expires_utc,
            "worker_pid": self.worker_pid,
            "current_stage": self.current_stage,
            "stage_pid": self.stage_pid,
            "cancellation_reason": self.cancellation_reason,
            "outcome": self.outcome.to_dict() if self.outcome else None,
            "error": (
                {"code": self.error_code, "message": self.error_message}
                if self.error_code
                else None
            ),
        }

    def public_dict(self) -> dict[str, Any]:
        """Return model-facing state without local process or lease identities."""

        value = self.to_dict()
        value.pop("worker_pid")
        value.pop("stage_pid")
        return value


@dataclass(frozen=True, slots=True)
class JobSubmission:
    job: JobRecord
    reused: bool


@dataclass(frozen=True, slots=True)
class JobEvent:
    job_id: str
    sequence: int
    occurred_utc: str
    state: JobState
    code: str
    message: str
    details: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return to_primitive(self)


class JobStore:
    """Transactional durable storage with explicit legal state transitions."""

    def __init__(
        self,
        path: str | Path,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        unresolved = Path(path).expanduser().absolute()
        if unresolved.is_symlink():
            raise JobError("job database must not be a symlink")
        self.path = unresolved.resolve()
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def submit(self, spec: ReplayJobSpec, idempotency_key: str) -> JobSubmission:
        _require_idempotency_key(idempotency_key)
        now = self._now()
        spec_json = _canonical_json(spec.to_dict())
        with self._transaction() as connection:
            existing = connection.execute(
                "SELECT * FROM jobs WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            if existing is not None:
                job = self._record(existing)
                if job.spec_sha256 != spec.sha256:
                    raise JobConflictError(
                        "idempotency key already names a different replay request; "
                        "reuse the original arguments or choose a new key"
                    )
                return JobSubmission(job, True)
            job_id = "job:" + uuid.uuid4().hex
            connection.execute(
                """
                INSERT INTO jobs (
                    job_id, idempotency_key, spec_sha256, spec_json,
                    repository_id, claim_id, state, attempt,
                    created_utc, updated_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
                """,
                (
                    job_id,
                    idempotency_key,
                    spec.sha256,
                    spec_json,
                    spec.repository_id,
                    spec.claim_id,
                    JobState.QUEUED.value,
                    now,
                    now,
                ),
            )
            self._append_event(
                connection,
                job_id,
                now,
                JobState.QUEUED,
                "submitted",
                "Replay request was durably queued.",
                {"spec_sha256": spec.sha256},
            )
            return JobSubmission(self._get_locked(connection, job_id), False)

    def get(self, job_id: str) -> JobRecord:
        _require_job_id(job_id)
        with self._connect() as connection:
            return self._get_locked(connection, job_id)

    def list(
        self,
        *,
        state: JobState | None = None,
        repository_id: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[int, tuple[JobRecord, ...]]:
        _require_page(limit, offset)
        clauses = []
        values: list[Any] = []
        if state is not None:
            clauses.append("state = ?")
            values.append(state.value)
        if repository_id is not None:
            _require_identifier(repository_id, "repository_id")
            clauses.append("repository_id = ?")
            values.append(repository_id)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self._connect() as connection:
            total = connection.execute(
                "SELECT COUNT(*) FROM jobs" + where,
                values,
            ).fetchone()[0]
            rows = connection.execute(
                "SELECT * FROM jobs"
                + where
                + " ORDER BY created_utc DESC, job_id DESC LIMIT ? OFFSET ?",
                (*values, limit, offset),
            ).fetchall()
        return total, tuple(self._record(row) for row in rows)

    def claim_next(self, worker_id: str, lease_seconds: int) -> JobRecord | None:
        _require_identifier(worker_id, "worker_id")
        if (
            not isinstance(lease_seconds, int)
            or isinstance(lease_seconds, bool)
            or lease_seconds < 3
        ):
            raise JobError("lease_seconds must be an integer of at least three")
        now_dt = self._now_datetime()
        now = _format_utc(now_dt)
        lease_expires = _format_utc(now_dt + timedelta(seconds=lease_seconds))
        with self._transaction() as connection:
            self._recover_expired_locked(connection, now)
            row = connection.execute(
                "SELECT job_id FROM jobs WHERE state = ? "
                "ORDER BY created_utc, job_id LIMIT 1",
                (JobState.QUEUED.value,),
            ).fetchone()
            if row is None:
                return None
            job_id = row["job_id"]
            connection.execute(
                """
                UPDATE jobs SET state = ?, attempt = attempt + 1,
                    updated_utc = ?, lease_owner = ?, lease_expires_utc = ?
                WHERE job_id = ? AND state = ?
                """,
                (
                    JobState.LEASED.value,
                    now,
                    worker_id,
                    lease_expires,
                    job_id,
                    JobState.QUEUED.value,
                ),
            )
            self._append_event(
                connection,
                job_id,
                now,
                JobState.LEASED,
                "leased",
                "Worker claimed the queued replay.",
                {"lease_expires_utc": lease_expires},
            )
            return self._get_locked(connection, job_id)

    def mark_running(self, job_id: str, worker_id: str, worker_pid: int) -> JobRecord:
        return self._transition_active(
            job_id,
            worker_id,
            expected={JobState.LEASED},
            state=JobState.RUNNING,
            code="started",
            message="Worker started controlled replay execution.",
            updates={"started_utc": self._now(), "worker_pid": worker_pid},
        )

    def heartbeat(
        self,
        job_id: str,
        worker_id: str,
        lease_seconds: int,
        *,
        current_stage: str | None,
        stage_pid: int | None,
    ) -> JobRecord:
        if lease_seconds < 3:
            raise JobError("lease_seconds must be at least three")
        now_dt = self._now_datetime()
        now = _format_utc(now_dt)
        expires = _format_utc(now_dt + timedelta(seconds=lease_seconds))
        expired = False
        with self._transaction() as connection:
            expired = job_id in self._recover_expired_locked(connection, now)
            if not expired:
                row = self._owned_active(connection, job_id, worker_id)
                if JobState(row["state"]) not in {
                    JobState.RUNNING,
                    JobState.CANCEL_REQUESTED,
                }:
                    raise JobStateError("only a running job can renew its lease")
                connection.execute(
                    """
                    UPDATE jobs SET updated_utc = ?, lease_expires_utc = ?,
                        current_stage = ?, stage_pid = ? WHERE job_id = ?
                    """,
                    (now, expires, current_stage, stage_pid, job_id),
                )
                result = self._get_locked(connection, job_id)
        if expired:
            raise JobStateError("worker lease expired before heartbeat")
        return result

    def cancellation_requested(self, job_id: str) -> bool:
        return self.get(job_id).state is JobState.CANCEL_REQUESTED

    def cancel(self, job_id: str, reason: str) -> JobRecord:
        _require_job_id(job_id)
        reason = _message(reason, "cancellation reason")
        now = self._now()
        with self._transaction() as connection:
            self._recover_expired_locked(connection, now)
            job = self._get_locked(connection, job_id)
            if job.state.terminal or job.state is JobState.CANCEL_REQUESTED:
                return job
            if job.state is JobState.QUEUED:
                next_state = JobState.CANCELLED
                connection.execute(
                    """
                    UPDATE jobs SET state = ?, updated_utc = ?, finished_utc = ?,
                        cancellation_reason = ? WHERE job_id = ?
                    """,
                    (next_state.value, now, now, reason, job_id),
                )
                message = "Queued replay was cancelled before a worker claimed it."
                event_code = "cancelled"
            else:
                next_state = JobState.CANCEL_REQUESTED
                connection.execute(
                    """
                    UPDATE jobs SET state = ?, updated_utc = ?,
                        cancellation_reason = ? WHERE job_id = ?
                    """,
                    (next_state.value, now, reason, job_id),
                )
                message = (
                    "Cancellation was requested; the worker will stop the active stage."
                )
                event_code = "cancellation-requested"
            self._append_event(
                connection,
                job_id,
                now,
                next_state,
                event_code,
                message,
                {},
            )
            return self._get_locked(connection, job_id)

    def complete(self, job_id: str, worker_id: str, outcome: JobOutcome) -> JobRecord:
        return self._transition_active(
            job_id,
            worker_id,
            expected={JobState.RUNNING, JobState.CANCEL_REQUESTED},
            state=JobState.COMPLETED,
            code="completed",
            message="Replay completed and its receipt received an acceptance decision.",
            updates={
                "finished_utc": self._now(),
                "outcome_json": _canonical_json(outcome.to_dict()),
            },
        )

    def fail(
        self,
        job_id: str,
        worker_id: str,
        *,
        error_code: str,
        error_message: str,
    ) -> JobRecord:
        _require_identifier(error_code, "job error code")
        return self._transition_active(
            job_id,
            worker_id,
            expected={JobState.LEASED, JobState.RUNNING, JobState.CANCEL_REQUESTED},
            state=JobState.FAILED,
            code=error_code,
            message=_message(error_message, "job error message"),
            updates={
                "finished_utc": self._now(),
                "error_code": error_code,
                "error_message": _message(error_message, "job error message"),
            },
        )

    def mark_cancelled(self, job_id: str, worker_id: str) -> JobRecord:
        job = self.get(job_id)
        return self._transition_active(
            job_id,
            worker_id,
            expected={JobState.CANCEL_REQUESTED},
            state=JobState.CANCELLED,
            code="cancelled",
            message="Worker terminated the active replay after cancellation was requested.",
            updates={"finished_utc": self._now()},
            details={"reason": job.cancellation_reason},
        )

    def recover_expired(self) -> int:
        now = self._now()
        with self._transaction() as connection:
            return len(self._recover_expired_locked(connection, now))

    def events(
        self,
        job_id: str,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[int, tuple[JobEvent, ...]]:
        _require_job_id(job_id)
        _require_page(limit, offset)
        with self._connect() as connection:
            self._get_locked(connection, job_id)
            total = connection.execute(
                "SELECT COUNT(*) FROM job_events WHERE job_id = ?",
                (job_id,),
            ).fetchone()[0]
            rows = connection.execute(
                "SELECT * FROM job_events WHERE job_id = ? "
                "ORDER BY sequence LIMIT ? OFFSET ?",
                (job_id, limit, offset),
            ).fetchall()
        return total, tuple(
            JobEvent(
                job_id=row["job_id"],
                sequence=row["sequence"],
                occurred_utc=row["occurred_utc"],
                state=JobState(row["state"]),
                code=row["code"],
                message=row["message"],
                details=json.loads(row["details_json"]),
            )
            for row in rows
        )

    def _transition_active(
        self,
        job_id: str,
        worker_id: str,
        *,
        expected: set[JobState],
        state: JobState,
        code: str,
        message: str,
        updates: Mapping[str, Any],
        details: Mapping[str, Any] | None = None,
    ) -> JobRecord:
        _require_job_id(job_id)
        _require_identifier(worker_id, "worker_id")
        now = self._now()
        expired = False
        with self._transaction() as connection:
            expired = job_id in self._recover_expired_locked(connection, now)
            if not expired:
                row = self._owned_active(connection, job_id, worker_id)
                current = JobState(row["state"])
                if current not in expected:
                    raise JobStateError(
                        f"job transition {current.value} -> {state.value} is not allowed"
                    )
                assignments = {
                    "state": state.value,
                    "updated_utc": now,
                    **updates,
                }
                if state.terminal:
                    assignments.update(
                        {
                            "lease_owner": None,
                            "lease_expires_utc": None,
                            "current_stage": None,
                            "stage_pid": None,
                        }
                    )
                sql = ", ".join(f"{name} = ?" for name in assignments)
                connection.execute(
                    f"UPDATE jobs SET {sql} WHERE job_id = ?",  # noqa: S608 - fixed column names
                    (*assignments.values(), job_id),
                )
                self._append_event(
                    connection,
                    job_id,
                    now,
                    state,
                    code,
                    message,
                    details or {},
                )
                result = self._get_locked(connection, job_id)
        if expired:
            raise JobStateError("worker lease expired before state transition")
        return result

    def _recover_expired_locked(
        self, connection: sqlite3.Connection, now: str
    ) -> tuple[str, ...]:
        rows = connection.execute(
            "SELECT job_id FROM jobs WHERE state IN (?, ?, ?) "
            "AND lease_expires_utc <= ? ORDER BY job_id",
            (
                JobState.LEASED.value,
                JobState.RUNNING.value,
                JobState.CANCEL_REQUESTED.value,
                now,
            ),
        ).fetchall()
        for row in rows:
            job_id = row["job_id"]
            connection.execute(
                """
                UPDATE jobs SET state = ?, updated_utc = ?, finished_utc = ?,
                    lease_owner = NULL, lease_expires_utc = NULL,
                    current_stage = NULL, stage_pid = NULL,
                    error_code = ?, error_message = ? WHERE job_id = ?
                """,
                (
                    JobState.FAILED.value,
                    now,
                    now,
                    "worker-lease-expired",
                    "The worker lease expired. Automatic replay is disabled because an orphaned native process cannot be ruled out; inspect the repository before submitting a new job.",
                    job_id,
                ),
            )
            self._append_event(
                connection,
                job_id,
                now,
                JobState.FAILED,
                "worker-lease-expired",
                "Worker lease expired; the job was failed without automatic retry.",
                {},
            )
        return tuple(row["job_id"] for row in rows)

    def _owned_active(
        self,
        connection: sqlite3.Connection,
        job_id: str,
        worker_id: str,
    ) -> sqlite3.Row:
        row = connection.execute(
            "SELECT * FROM jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()
        if row is None:
            raise JobError(f"unknown job_id {job_id!r}")
        if row["lease_owner"] != worker_id:
            raise JobStateError("worker does not own this job lease")
        return row

    def _append_event(
        self,
        connection: sqlite3.Connection,
        job_id: str,
        occurred_utc: str,
        state: JobState,
        code: str,
        message: str,
        details: Mapping[str, Any],
    ) -> None:
        sequence = connection.execute(
            "SELECT COALESCE(MAX(sequence), 0) + 1 FROM job_events WHERE job_id = ?",
            (job_id,),
        ).fetchone()[0]
        connection.execute(
            """
            INSERT INTO job_events (
                job_id, sequence, occurred_utc, state, code, message, details_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                sequence,
                occurred_utc,
                state.value,
                code,
                message,
                _canonical_json(details),
            ),
        )

    def _get_locked(self, connection: sqlite3.Connection, job_id: str) -> JobRecord:
        row = connection.execute(
            "SELECT * FROM jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()
        if row is None:
            raise JobError(f"unknown job_id {job_id!r}")
        return self._record(row)

    def _record(self, row: sqlite3.Row) -> JobRecord:
        spec = ReplayJobSpec.from_dict(json.loads(row["spec_json"]))
        outcome_raw = json.loads(row["outcome_json"]) if row["outcome_json"] else None
        return JobRecord(
            job_id=row["job_id"],
            idempotency_key=row["idempotency_key"],
            spec_sha256=row["spec_sha256"],
            spec=spec,
            state=JobState(row["state"]),
            attempt=row["attempt"],
            created_utc=row["created_utc"],
            updated_utc=row["updated_utc"],
            started_utc=row["started_utc"],
            finished_utc=row["finished_utc"],
            lease_owner=row["lease_owner"],
            lease_expires_utc=row["lease_expires_utc"],
            worker_pid=row["worker_pid"],
            current_stage=row["current_stage"],
            stage_pid=row["stage_pid"],
            cancellation_reason=row["cancellation_reason"],
            outcome=JobOutcome.from_dict(outcome_raw) if outcome_raw else None,
            error_code=row["error_code"],
            error_message=row["error_message"],
        )

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
            except BaseException:
                connection.rollback()
                raise
            else:
                connection.commit()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 10000")
            connection.execute("PRAGMA synchronous = FULL")
            yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA synchronous = FULL")
            connection.execute("BEGIN IMMEDIATE")
            try:
                version = connection.execute("PRAGMA user_version").fetchone()[0]
                if version not in {0, JOB_SCHEMA_VERSION}:
                    raise JobError(
                        f"unsupported job database schema version: {version}"
                    )
                if version == JOB_SCHEMA_VERSION:
                    connection.commit()
                    return
                connection.execute(
                    """
                    CREATE TABLE jobs (
                        job_id TEXT PRIMARY KEY,
                        idempotency_key TEXT NOT NULL UNIQUE,
                        spec_sha256 TEXT NOT NULL,
                        spec_json TEXT NOT NULL,
                        repository_id TEXT NOT NULL,
                        claim_id TEXT NOT NULL,
                        state TEXT NOT NULL CHECK (state IN (
                            'queued', 'leased', 'running', 'cancel-requested',
                            'completed', 'failed', 'cancelled'
                        )),
                        attempt INTEGER NOT NULL CHECK (attempt >= 0),
                        created_utc TEXT NOT NULL,
                        updated_utc TEXT NOT NULL,
                        started_utc TEXT,
                        finished_utc TEXT,
                        lease_owner TEXT,
                        lease_expires_utc TEXT,
                        worker_pid INTEGER,
                        current_stage TEXT,
                        stage_pid INTEGER,
                        cancellation_reason TEXT,
                        outcome_json TEXT,
                        error_code TEXT,
                        error_message TEXT
                    )
                    """
                )
                connection.execute(
                    """
                    CREATE TABLE job_events (
                        job_id TEXT NOT NULL REFERENCES jobs(job_id),
                        sequence INTEGER NOT NULL,
                        occurred_utc TEXT NOT NULL,
                        state TEXT NOT NULL,
                        code TEXT NOT NULL,
                        message TEXT NOT NULL,
                        details_json TEXT NOT NULL,
                        PRIMARY KEY (job_id, sequence)
                    )
                    """
                )
                connection.execute(
                    "CREATE INDEX jobs_queue_order ON jobs(state, created_utc, job_id)"
                )
                connection.execute(
                    "CREATE INDEX jobs_repository ON jobs(repository_id, created_utc)"
                )
                connection.execute(f"PRAGMA user_version = {JOB_SCHEMA_VERSION}")
                connection.commit()
            except BaseException:
                connection.rollback()
                raise

    def _now(self) -> str:
        return _format_utc(self._now_datetime())

    def _now_datetime(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise JobError("job clock must return a timezone-aware datetime")
        return value.astimezone(timezone.utc)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _format_utc(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise JobError("job clock must return a timezone-aware datetime")
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds")


def _require_utc(value: str, label: str) -> None:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise ValidationError(f"{label} must be an ISO timestamp") from error
    if parsed.utcoffset() != timedelta(0):
        raise ValidationError(f"{label} must identify UTC")


def _require_identifier(value: str, label: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(
        r"^[A-Za-z0-9][A-Za-z0-9._:-]*$", value
    ):
        raise ValidationError(f"{label} must be a normalized identifier")


def _require_sha256(value: str, label: str) -> None:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValidationError(f"{label} must be a lowercase SHA-256 digest")


def _require_job_id(value: str) -> None:
    if not isinstance(value, str) or not _JOB_ID.fullmatch(value):
        raise JobError("job_id must use job:<32 lowercase hex characters>")


def _require_idempotency_key(value: str) -> None:
    if not isinstance(value, str) or not _IDEMPOTENCY_KEY.fullmatch(value):
        raise ValidationError(
            "idempotency_key must be 1-128 safe identifier characters"
        )


def _message(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 1000:
        raise ValidationError(f"{label} must contain 1-1000 characters")
    return value.strip()


def _require_page(limit: int, offset: int) -> None:
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
        raise JobError("limit must be an integer from 1 through 100")
    if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
        raise JobError("offset must be a non-negative integer")


def _object(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError(f"{label} must be an object")
    return value


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise ValidationError(
            f"{label} fields differ: missing={sorted(expected - set(value))} "
            f"extra={sorted(set(value) - expected)}"
        )
