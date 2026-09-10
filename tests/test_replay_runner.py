from __future__ import annotations

import ast
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import reconstruction_factory.replay_runner as replay_runner_module
from reconstruction_factory.artifact_store import ArtifactStore
from reconstruction_factory.errors import ReplayCancelled, ReplayError
from reconstruction_factory.ontology import (
    Claim,
    ClaimType,
    Coverage,
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
    driver_version,
)
from reconstruction_factory.replay_identity import (
    capture_source_binding,
    file_sha256,
    repository_lock,
)
from reconstruction_factory.replay_runner import (
    FreshnessObservationCache,
    ReplayExpectation,
    ReplayRunner,
    _RUNNER_IMPLEMENTATION_RELATIVE_PATHS,
    runner_implementation_sha256,
    verify_live_freshness,
)
from reconstruction_factory.oracle_receipts import canonical_sha256
from reconstruction_factory.ontology import to_primitive


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


class FakeProductDriver(FakeDriver):
    driver_id = "test-whole-build-v1"
    oracle_id = "test.whole-build-closed"

    def decode(self, plan, claim, subject, executions):
        report = json.loads(executions[0].stdout)
        return NativeOutcome(
            Verdict.PASS,
            0,
            report,
            coverage=Coverage(
                "production-translation-units",
                88,
                88,
                True,
                "The complete declared product source graph was compiled.",
            ),
        )


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


def product_snapshot(root: Path) -> RepositorySnapshot:
    base = snapshot(root)
    subject = Subject(
        "test-main:product",
        base.targets[0].id,
        SubjectKind.PRODUCT,
        "Test production product",
    )
    claim = Claim(
        "claim:test-main:product:whole-build-closed",
        subject.id,
        ClaimType.WHOLE_BUILD_CLOSED,
        base.targets[0].id,
        {"closed": True},
        EvidenceClass.UNKNOWN,
        base.toolchains[0].id,
    )
    return RepositorySnapshot(
        base.project,
        base.products,
        base.targets,
        base.toolchains,
        (subject,),
        (claim,),
        adapter_id=base.adapter_id,
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
            """import json, pathlib, sys, time
if sys.argv[1] == 'source':
    pathlib.Path('source.txt').write_text('changed\\n')
elif sys.argv[1] == 'target':
    pathlib.Path('resources/test.exe').write_bytes(b'EVIL')
elif sys.argv[1] == 'toolchain':
    pathlib.Path('toolchain/cl.exe').write_bytes(b'changed')
elif sys.argv[1] == 'sleep':
    time.sleep(30)
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

    def expectation(self, driver: FakeDriver) -> ReplayExpectation:
        claim = self.snapshot.claims[0]
        subject = self.snapshot.subjects[0]
        plan = driver.prepare(
            self.root,
            self.snapshot,
            claim,
            subject,
            "factory-20260909T000000Z-000000000000",
        )
        return ReplayExpectation(
            repository_adapter_id=self.snapshot.adapter_id,
            target_identity_id=claim.target_identity_id,
            claim_id=claim.id,
            claim_sha256=canonical_sha256(to_primitive(claim)),
            subject_id=subject.id,
            subject_sha256=canonical_sha256(to_primitive(subject)),
            source_binding=capture_source_binding(self.root),
            driver_id=driver.driver_id,
            driver_version_sha256=driver_version(plan),
            oracle_id=driver.oracle_id,
            runner_implementation_sha256=runner_implementation_sha256(),
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

    def test_freshness_snapshot_reuses_expensive_live_observations(self) -> None:
        driver = FakeDriver()
        run = self.run_with(driver)
        document = self.store.verify_receipt_document(run.receipt_path)
        observations = FreshnessObservationCache()
        with (
            patch(
                "reconstruction_factory.replay_runner.inspect_repository",
                return_value=self.snapshot,
            ) as inspection,
            patch(
                "reconstruction_factory.replay_runner.select_driver",
                return_value=driver,
            ),
            patch(
                "reconstruction_factory.replay_runner.capture_source_binding",
                wraps=capture_source_binding,
            ) as source_observation,
            patch(
                "reconstruction_factory.replay_runner.driver_version",
                wraps=driver_version,
            ) as version_observation,
        ):
            self.assertEqual(
                verify_live_freshness(
                    document,
                    self.root,
                    observations=observations,
                ),
                (),
            )
            self.assertEqual(
                verify_live_freshness(
                    document,
                    self.root,
                    observations=observations,
                ),
                (),
            )
        inspection.assert_called_once_with(self.root.resolve(strict=True))
        source_observation.assert_called_once_with(self.root.resolve(strict=True))
        version_observation.assert_called_once()

    def test_stale_runner_short_circuits_repository_observation(self) -> None:
        driver = FakeDriver()
        run = self.run_with(driver)
        document = self.store.verify_receipt_document(run.receipt_path)
        document["runner_implementation_sha256"] = "0" * 64
        with patch(
            "reconstruction_factory.replay_runner.inspect_repository"
        ) as inspection:
            self.assertEqual(
                verify_live_freshness(
                    document,
                    self.root,
                    stop_on_runner_mismatch=True,
                ),
                ("runner-implementation-stale",),
            )
        inspection.assert_not_called()

    def test_runner_fingerprint_has_an_auditable_execution_scope(self) -> None:
        paths = set(_RUNNER_IMPLEMENTATION_RELATIVE_PATHS)
        self.assertIn("replay_runner.py", paths)
        self.assertIn("replay_drivers.py", paths)
        self.assertIn("oracle_receipts.py", paths)
        self.assertIn("adapters/windows.py", paths)
        self.assertNotIn("mcp_server.py", paths)
        self.assertNotIn("acceptance.py", paths)
        self.assertNotIn("workspaces.py", paths)

        package_root = Path(replay_runner_module.__file__).parent
        missing = set()
        for relative in paths:
            source = package_root / relative
            package_parts = ["reconstruction_factory", *Path(relative).parts[:-1]]
            for node in ast.walk(ast.parse(source.read_text(encoding="utf-8"))):
                if not isinstance(node, ast.ImportFrom):
                    continue
                if node.level:
                    prefix = package_parts[: len(package_parts) - node.level + 1]
                    module = prefix + (node.module or "").split(".")
                elif node.module and node.module.startswith("reconstruction_factory"):
                    module = node.module.split(".")
                else:
                    continue
                if module[0] != "reconstruction_factory":
                    continue
                module_path = "/".join(module[1:])
                candidates = (f"{module_path}.py", f"{module_path}/__init__.py")
                for candidate in candidates:
                    if (package_root / candidate).is_file() and candidate not in paths:
                        missing.add((relative, candidate))
        self.assertEqual(missing, set())

    def test_product_replay_uses_driver_declared_nonbyte_coverage(self) -> None:
        self.snapshot = product_snapshot(self.root)
        driver = FakeProductDriver()
        run = self.run_with(driver)
        coverage = run.receipt.result.coverage
        self.assertEqual(run.receipt.result.verdict, Verdict.PASS)
        self.assertEqual(coverage.domain, "production-translation-units")
        self.assertEqual((coverage.observed_units, coverage.expected_units), (88, 88))
        self.assertTrue(coverage.complete)
        self.assertEqual(run.receipt.claim.extents, ())

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

    def test_stale_queue_expectation_stops_before_native_process(self) -> None:
        driver = FakeDriver()
        expected = self.expectation(driver)
        expected = replace(expected, claim_sha256="0" * 64)
        with (
            patch(
                "reconstruction_factory.replay_runner.inspect_repository",
                return_value=self.snapshot,
            ),
            patch(
                "reconstruction_factory.replay_runner.select_driver",
                return_value=driver,
            ),
            self.assertRaisesRegex(ReplayError, "claim digest"),
        ):
            ReplayRunner(self.store, expectation=expected).run(
                self.root, self.snapshot.claims[0].id
            )
        self.assertFalse(self.store.receipts.exists())

    def test_cancellation_terminates_process_group_without_receipt(self) -> None:
        driver = FakeDriver(mutate="sleep")
        requested = False
        process_ids: list[int] = []

        def progress(_stage, pid):
            nonlocal requested
            if pid is not None:
                process_ids.append(pid)
                requested = True

        with (
            patch(
                "reconstruction_factory.replay_runner.inspect_repository",
                return_value=self.snapshot,
            ),
            patch(
                "reconstruction_factory.replay_runner.select_driver",
                return_value=driver,
            ),
            self.assertRaises(ReplayCancelled),
        ):
            ReplayRunner(
                self.store,
                expectation=self.expectation(driver),
                cancel_requested=lambda: requested,
                on_stage_process=progress,
                poll_seconds=0.01,
                cancellation_grace_seconds=0.1,
            ).run(self.root, self.snapshot.claims[0].id)
        self.assertTrue(process_ids)
        with self.assertRaises(ProcessLookupError):
            os.kill(process_ids[0], 0)
        self.assertFalse(self.store.receipts.exists())

    def test_shared_registry_lock_cannot_overlap_exclusive_replay(self) -> None:
        with repository_lock(self.root, exclusive=True):
            with self.assertRaisesRegex(ReplayError, "another factory operation"):
                with repository_lock(self.root, exclusive=False):
                    self.fail("shared lock unexpectedly overlapped replay lock")


if __name__ == "__main__":
    unittest.main()
