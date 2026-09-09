from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from reconstruction_factory.job_service import FactoryService, ReplayWorker
from reconstruction_factory.jobs import JobState
from reconstruction_factory.ontology import (
    Claim,
    ClaimType,
    EvidenceClass,
    Extent,
    Product,
    Project,
    RepositorySnapshot,
    Subject,
    SubjectKind,
    TargetIdentity,
    ToolchainIdentity,
    Verdict,
)
from reconstruction_factory.oracle_receipts import Coldness
from reconstruction_factory.replay_drivers import (
    ComponentSpec,
    NativeOutcome,
    ReplayDriver,
    ReplayPlan,
    ReplayStagePlan,
)
from reconstruction_factory.replay_identity import file_sha256


class ServiceDriver(ReplayDriver):
    driver_id = "test-function-v1"
    adapter_id = "test-adapter"
    oracle_id = "test.function-exact"

    def supports(self, snapshot, claim):
        return True

    def prepare(self, root, snapshot, claim, subject, run_id):
        script = root / "oracle.py"
        return ReplayPlan(
            self.driver_id,
            self.oracle_id,
            Coldness.FORCED_RECOMPILE,
            (ReplayStagePlan("compare", ("python3", "oracle.py"), root),),
            (script,),
            root / "target.exe",
            (ComponentSpec("compiler", root / "compiler.exe", "$TEST/compiler.exe"),),
            ("PATH",),
        )

    def decode(self, plan, claim, subject, executions):
        return NativeOutcome(
            Verdict.PASS,
            4,
            json.loads(executions[0].stdout),
        )


def service_snapshot(root: Path) -> RepositorySnapshot:
    project = Project("test", "Test")
    product = Product("test-main", project.id, "gameplay", "target:test-main")
    target = TargetIdentity(
        "target:test-main",
        project.id,
        product.id,
        "test",
        "1.00",
        "test",
        "pe",
        4,
        file_sha256(root / "target.exe"),
    )
    toolchain = ToolchainIdentity(
        "toolchain:test", project.id, "test", "Test compiler", "b" * 64
    )
    subject = Subject(
        "test-main:function:00401000",
        target.id,
        SubjectKind.FUNCTION,
        "TestFunction",
        (Extent("pe-va", "0x00401000", 4),),
    )
    claim = Claim(
        "claim:test-main:function:00401000:codegen-exact",
        subject.id,
        ClaimType.CODEGEN_EXACT,
        target.id,
        {"exact": True, "unit": "test-unit"},
        EvidenceClass.CORROBORATED,
        toolchain.id,
    )
    return RepositorySnapshot(
        project,
        (product,),
        (target,),
        (toolchain,),
        (subject,),
        (claim,),
        adapter_id="test-adapter",
    )


class JobServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.repository = self.base / "repository"
        self.repository.mkdir()
        (self.repository / "target.exe").write_bytes(b"TEST")
        (self.repository / "compiler.exe").write_bytes(b"compiler")
        (self.repository / "oracle.py").write_text(
            "import json\nprint(json.dumps({'result': 'exact'}))\n",
            encoding="utf-8",
        )
        (self.repository / ".gitignore").write_text(
            "target.exe\ncompiler.exe\n", encoding="utf-8"
        )
        subprocess.run(["git", "init", "-q"], cwd=self.repository, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.invalid"],
            cwd=self.repository,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=self.repository,
            check=True,
        )
        subprocess.run(["git", "add", "."], cwd=self.repository, check=True)
        subprocess.run(
            ["git", "commit", "-qm", "fixture"], cwd=self.repository, check=True
        )
        self.snapshot = service_snapshot(self.repository)
        self.driver = ServiceDriver()
        policy = {
            "allow_dirty_source": False,
            "allowed_adapter_ids": ["test-adapter"],
            "allowed_claim_types": ["codegen_exact"],
            "allowed_coldness": ["forced-recompile"],
            "allowed_driver_ids": ["test-function-v1"],
            "allowed_oracle_ids": ["test.function-exact"],
            "description": "Test exact replay policy.",
            "driver_attestation_minimums": {},
            "id": "test-live-v1",
            "minimum_attestation": "observed",
            "require_complete_coverage": True,
            "require_empty_acceptance_errors": True,
            "require_live_freshness": True,
            "schema_version": 1,
        }
        (self.base / "policy.json").write_text(json.dumps(policy), encoding="utf-8")
        self.config = self.base / "service.toml"
        self.config.write_text(
            f'''schema_version = 1
state_directory = "state"
evidence_store = "evidence"
policy = "policy.json"
replay_timeout_seconds = 10
worker_lease_seconds = 30
worker_poll_seconds = 1.0

[[repositories]]
id = "test"
path = "{self.repository.as_posix()}"
adapter_id = "test-adapter"
target_identity_ids = ["target:test-main"]
''',
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def factory_patches(self):
        return (
            patch(
                "reconstruction_factory.job_service.inspect_repository",
                return_value=self.snapshot,
            ),
            patch(
                "reconstruction_factory.job_service.select_driver",
                return_value=self.driver,
            ),
            patch(
                "reconstruction_factory.replay_runner.inspect_repository",
                return_value=self.snapshot,
            ),
            patch(
                "reconstruction_factory.replay_runner.select_driver",
                return_value=self.driver,
            ),
        )

    def test_submit_restart_worker_acceptance_and_output_paging(self) -> None:
        patches = self.factory_patches()
        with patches[0], patches[1], patches[2], patches[3]:
            service = FactoryService.from_path(self.config)
            submitted = service.submit_replay(
                "test", self.snapshot.claims[0].id, "chat-turn-1"
            )
            duplicate = FactoryService.from_path(self.config).submit_replay(
                "test", self.snapshot.claims[0].id, "chat-turn-1"
            )
            self.assertFalse(submitted["reused"])
            self.assertTrue(duplicate["reused"])
            job_id = submitted["job"]["job_id"]
            completed = ReplayWorker(self.config, worker_id="worker-test").run_once()
            self.assertEqual(completed.job_id, job_id)
            self.assertEqual(completed.state, JobState.COMPLETED)
            self.assertEqual(completed.outcome.acceptance_decision, "accepted")
            reopened = FactoryService.from_path(self.config)
            self.assertEqual(reopened.get_job(job_id)["state"], "completed")
            manifest = reopened.artifact_page(job_id, None)
            artifact_id = manifest["artifacts"][0]["id"]
            first = reopened.artifact_page(job_id, artifact_id, offset=0, limit=2)
            second = reopened.artifact_page(
                job_id, artifact_id, offset=first["next_offset"], limit=64
            )
            self.assertEqual(first["text"] + second["text"], '{"result": "exact"}\n')
            facts = reopened.accepted_facts()
            self.assertEqual(facts["total"], 1)

    def test_source_change_after_submission_fails_without_receipt(self) -> None:
        patches = self.factory_patches()
        with patches[0], patches[1], patches[2], patches[3]:
            service = FactoryService.from_path(self.config)
            submitted = service.submit_replay(
                "test", self.snapshot.claims[0].id, "chat-turn-stale"
            )
            (self.repository / "oracle.py").write_text(
                "raise RuntimeError('must not run')\n", encoding="utf-8"
            )
            failed = ReplayWorker(self.config, worker_id="worker-test").run_once()
        self.assertEqual(failed.job_id, submitted["job"]["job_id"])
        self.assertEqual(failed.state, JobState.FAILED)
        self.assertRegex(failed.error_message, "driver version|source binding is stale")
        receipts = self.base / "evidence" / "receipts"
        self.assertFalse(receipts.exists())


if __name__ == "__main__":
    unittest.main()
