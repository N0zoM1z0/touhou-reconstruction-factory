from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from reconstruction_factory.artifact_store import ArtifactStore
from reconstruction_factory.errors import ReplayError
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
from reconstruction_factory.replay_identity import file_sha256, repository_lock
from reconstruction_factory.replay_runner import ReplayRunner, verify_live_freshness


class FakeDriver(ReplayDriver):
    driver_id = "test-function-v1"
    adapter_id = "test-adapter"
    oracle_id = "test.function-exact"

    def __init__(self, *, mutate: str | None = None, coldness: Coldness = Coldness.FORCED_RECOMPILE) -> None:
        self.mutate = mutate
        self.coldness = coldness

    def supports(self, snapshot, claim):
        return True

    def prepare(self, root, snapshot, claim, subject, run_id):
        script = root / "scripts/oracle.py"
        return ReplayPlan(
            self.driver_id,
            self.oracle_id,
            self.coldness,
            (
                ReplayStagePlan(
                    "compare",
                    ("python3", "scripts/oracle.py", self.mutate or "exact"),
                    root,
                ),
            ),
            (script,),
            root / "resources/test.exe",
            (ComponentSpec("compiler", root / "toolchain/cl.exe", "$TEST/cl.exe"),),
            ("PATH",),
        )

    def decode(self, plan, claim, subject, executions):
        report = json.loads(executions[0].stdout)
        return NativeOutcome(Verdict.PASS, 4, report)


def snapshot(root: Path) -> RepositorySnapshot:
    target_path = root / "resources/test.exe"
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
        target_path.stat().st_size,
        file_sha256(target_path),
    )
    toolchain = ToolchainIdentity(
        "toolchain:test",
        project.id,
        "msvc7",
        "Test compiler",
        "b" * 64,
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


class ReplayRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        base = Path(self.temporary.name)
        self.root = base / "game"
        self.store = ArtifactStore(base / "store")
        (self.root / "resources").mkdir(parents=True)
        (self.root / "scripts").mkdir()
        (self.root / "toolchain").mkdir()
        (self.root / "resources/test.exe").write_bytes(b"TEST")
        (self.root / "source.txt").write_text("stable\n", encoding="utf-8")
        (self.root / "toolchain/cl.exe").write_bytes(b"compiler")
        (self.root / ".gitignore").write_text("resources/\ntoolchain/\n", encoding="utf-8")
        (self.root / "scripts/oracle.py").write_text(
            """import json, pathlib, sys
if sys.argv[1] == 'source':
    pathlib.Path('source.txt').write_text('changed\\n')
elif sys.argv[1] == 'target':
    pathlib.Path('resources/test.exe').write_bytes(b'EVIL')
elif sys.argv[1] == 'toolchain':
    pathlib.Path('toolchain/cl.exe').write_bytes(b'changed')
print(json.dumps({'result': 'exact', 'address': '0x00401000', 'size': 4}))
""",
            encoding="utf-8",
        )
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.root, check=True)
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=self.root, check=True)
        self.snapshot = snapshot(self.root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_with(self, driver: FakeDriver):
        with (
            patch("reconstruction_factory.replay_runner.inspect_repository", return_value=self.snapshot),
            patch("reconstruction_factory.replay_runner.select_driver", return_value=driver),
        ):
            return ReplayRunner(self.store, timeout_seconds=10).run(
                self.root,
                self.snapshot.claims[0].id,
            )

    def test_exact_run_persists_a_verifiable_receipt(self) -> None:
        driver = FakeDriver()
        run = self.run_with(driver)
        self.assertEqual(run.receipt.result.verdict, Verdict.PASS)
        self.assertTrue(run.receipt.target.matches)
        document = self.store.verify_receipt_document(run.receipt_path)
        self.assertEqual(document["receipt_id"], run.receipt.receipt_id)
        self.assertEqual(document["result"]["coverage"]["observed_units"], 4)
        with (
            patch(
                "reconstruction_factory.replay_runner.inspect_repository",
                return_value=self.snapshot,
            ),
            patch(
                "reconstruction_factory.replay_runner.select_driver",
                return_value=driver,
            ),
        ):
            self.assertEqual(verify_live_freshness(document, self.root), ())

    def test_source_mutation_overrides_native_pass(self) -> None:
        run = self.run_with(FakeDriver(mutate="source"))
        self.assertEqual(run.receipt.result.verdict, Verdict.ERROR)
        self.assertIn("source-mutated-during-replay", run.receipt.acceptance_errors)

    def test_target_mutation_overrides_native_pass(self) -> None:
        run = self.run_with(FakeDriver(mutate="target"))
        self.assertEqual(run.receipt.result.verdict, Verdict.ERROR)
        self.assertIn("target-mutated-during-replay", run.receipt.acceptance_errors)

    def test_toolchain_mutation_overrides_native_pass(self) -> None:
        run = self.run_with(FakeDriver(mutate="toolchain"))
        self.assertEqual(run.receipt.result.verdict, Verdict.ERROR)
        self.assertIn("toolchain-mutated-during-replay", run.receipt.acceptance_errors)

    def test_incremental_native_pass_remains_incomplete(self) -> None:
        run = self.run_with(FakeDriver(coldness=Coldness.INCREMENTAL))
        self.assertEqual(run.receipt.result.verdict, Verdict.INCOMPLETE)
        self.assertIn("replay-coldness-insufficient", run.receipt.acceptance_errors)

    def test_shared_registry_lock_cannot_overlap_exclusive_replay(self) -> None:
        with repository_lock(self.root, exclusive=True):
            with self.assertRaisesRegex(ReplayError, "another factory operation"):
                with repository_lock(self.root, exclusive=False):
                    self.fail("shared lock unexpectedly overlapped replay lock")


if __name__ == "__main__":
    unittest.main()
