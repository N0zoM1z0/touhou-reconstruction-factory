from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
import tempfile
import unittest

from reconstruction_factory.errors import JobConflictError, JobError, JobStateError
from reconstruction_factory.jobs import (
    JobOutcome,
    JobState,
    JobStore,
    ReplayJobSpec,
)
from reconstruction_factory.ontology import ClaimType, Verdict
from reconstruction_factory.oracle_receipts import Coldness, SourceBinding


class Clock:
    def __init__(self) -> None:
        self.value = datetime(2026, 9, 9, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.value

    def advance(self, seconds: int) -> None:
        self.value += timedelta(seconds=seconds)


def spec(*, claim_sha256: str = "a" * 64) -> ReplayJobSpec:
    return ReplayJobSpec(
        repository_id="th08",
        repository_adapter_id="th08-vc7-ledgers-v1",
        target_identity_id="target:th08-v1.00d-original",
        claim_id="claim:th08:test:codegen-exact",
        claim_type=ClaimType.CODEGEN_EXACT,
        claim_sha256=claim_sha256,
        subject_id="th08:function:00401000",
        subject_sha256="b" * 64,
        source_binding=SourceBinding(
            git_commit="c" * 40,
            git_tree="d" * 40,
            repository_scope=".",
            snapshot_sha256="e" * 64,
            file_count=1,
            dirty=False,
            untracked_files=0,
        ),
        policy_id="strict-live-v1",
        policy_sha256="f" * 64,
        configuration_sha256="1" * 64,
        driver_id="th08-vc7-function-v1",
        driver_version_sha256="4" * 64,
        oracle_id="windows.msvc7.function-exact",
        coldness=Coldness.FORCED_RECOMPILE,
        runner_implementation_sha256="5" * 64,
        timeout_seconds=30,
    )


def outcome() -> JobOutcome:
    return JobOutcome(
        receipt_id="receipt:" + "2" * 64,
        receipt_verdict=Verdict.PASS,
        acceptance_decision="accepted",
        acceptance_reasons=(),
        registry_id="registry:" + "3" * 64,
    )


class JobStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name) / "state" / "jobs.sqlite3"
        self.clock = Clock()
        self.store = JobStore(self.path, clock=self.clock)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_submission_is_durable_and_idempotent(self) -> None:
        first = self.store.submit(spec(), "conversation-42-turn-7")
        reopened = JobStore(self.path, clock=self.clock)
        second = reopened.submit(spec(), "conversation-42-turn-7")
        self.assertFalse(first.reused)
        self.assertTrue(second.reused)
        self.assertEqual(first.job.job_id, second.job.job_id)
        self.assertEqual(reopened.get(first.job.job_id), first.job)

    def test_idempotency_key_cannot_be_rebound(self) -> None:
        self.store.submit(spec(), "same-key")
        with self.assertRaisesRegex(JobConflictError, "different replay request"):
            self.store.submit(spec(claim_sha256="9" * 64), "same-key")

    def test_legal_lifecycle_has_ordered_events(self) -> None:
        job = self.store.submit(spec(), "lifecycle").job
        leased = self.store.claim_next("worker-1", 30)
        self.assertEqual(leased.job_id, job.job_id)
        self.assertEqual(leased.state, JobState.LEASED)
        running = self.store.mark_running(job.job_id, "worker-1", 1234)
        self.assertEqual(running.state, JobState.RUNNING)
        heartbeat = self.store.heartbeat(
            job.job_id,
            "worker-1",
            30,
            current_stage="compare",
            stage_pid=5678,
        )
        self.assertEqual(heartbeat.current_stage, "compare")
        complete = self.store.complete(job.job_id, "worker-1", outcome())
        self.assertEqual(complete.state, JobState.COMPLETED)
        self.assertEqual(complete.outcome, outcome())
        self.assertIsNone(complete.lease_owner)
        total, events = self.store.events(job.job_id, limit=2, offset=1)
        self.assertEqual(total, 4)
        self.assertEqual([item.code for item in events], ["leased", "started"])
        with self.assertRaises(JobStateError):
            self.store.fail(
                job.job_id,
                "worker-1",
                error_code="late-failure",
                error_message="must not replace a terminal outcome",
            )

    def test_queued_and_active_cancellation_are_distinct(self) -> None:
        queued = self.store.submit(spec(), "queued-cancel").job
        cancelled = self.store.cancel(queued.job_id, "operator changed direction")
        self.assertEqual(cancelled.state, JobState.CANCELLED)
        self.assertIsNotNone(cancelled.finished_utc)

        active = self.store.submit(spec(), "active-cancel").job
        self.store.claim_next("worker-1", 30)
        requested = self.store.cancel(active.job_id, "stop native build")
        self.assertEqual(requested.state, JobState.CANCEL_REQUESTED)
        self.assertIsNone(requested.started_utc)
        final = self.store.mark_cancelled(active.job_id, "worker-1")
        self.assertEqual(final.state, JobState.CANCELLED)

    def test_expired_lease_fails_without_requeue(self) -> None:
        job = self.store.submit(spec(), "lease-expiry").job
        self.store.claim_next("dead-worker", 3)
        self.clock.advance(4)
        self.assertEqual(self.store.recover_expired(), 1)
        failed = self.store.get(job.job_id)
        self.assertEqual(failed.state, JobState.FAILED)
        self.assertEqual(failed.error_code, "worker-lease-expired")
        self.assertIsNone(self.store.claim_next("new-worker", 3))

    def test_expired_worker_cannot_complete_late(self) -> None:
        job = self.store.submit(spec(), "late-completion").job
        self.store.claim_next("slow-worker", 3)
        self.store.mark_running(job.job_id, "slow-worker", 1234)
        self.clock.advance(4)
        with self.assertRaises(JobStateError):
            self.store.complete(job.job_id, "slow-worker", outcome())
        failed = self.store.get(job.job_id)
        self.assertEqual(failed.state, JobState.FAILED)
        self.assertEqual(failed.error_code, "worker-lease-expired")

    def test_two_store_instances_cannot_claim_the_same_job(self) -> None:
        job = self.store.submit(spec(), "one-claim").job

        def claim(worker: str):
            return JobStore(self.path, clock=self.clock).claim_next(worker, 30)

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(claim, ("worker-a", "worker-b")))
        claimed = [item for item in results if item is not None]
        self.assertEqual(len(claimed), 1)
        self.assertEqual(claimed[0].job_id, job.job_id)

    def test_unknown_database_schema_is_rejected(self) -> None:
        other = Path(self.temporary.name) / "future.sqlite3"
        connection = sqlite3.connect(other)
        connection.execute("PRAGMA user_version = 99")
        connection.close()
        with self.assertRaisesRegex(JobError, "unsupported job database"):
            JobStore(other)

    def test_database_symlink_is_rejected(self) -> None:
        link = Path(self.temporary.name) / "jobs-link.sqlite3"
        link.symlink_to(self.path)
        with self.assertRaisesRegex(JobError, "must not be a symlink"):
            JobStore(link)


if __name__ == "__main__":
    unittest.main()
