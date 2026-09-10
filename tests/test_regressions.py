from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from reconstruction_factory.errors import RegressionFixtureError
from reconstruction_factory.ontology import Verdict
from reconstruction_factory.regressions import (
    DEFAULT_FIXTURE_DIRECTORY,
    FixtureProvenance,
    HistoricalFixture,
    RegressionContract,
    evaluate_fixture,
    load_fixture_suite,
    run_fixture_suite,
    verify_fixture_provenance,
)


class HistoricalRegressionTests(unittest.TestCase):
    def test_packaged_suite_matches_all_expected_verdicts(self) -> None:
        report = run_fixture_suite()
        self.assertTrue(report.passed)
        self.assertEqual(len(report.evaluations), 12)
        self.assertEqual(
            {item.project for item in report.evaluations},
            {"th04", "th08", "th095", "th105"},
        )

    def test_th095_open_and_closed_build_history_are_both_executable(self) -> None:
        evaluations = {
            item.fixture_id: item for item in run_fixture_suite().evaluations
        }
        self.assertEqual(
            evaluations["th095-whole-build-open"].outcome.verdict,
            Verdict.FAIL,
        )
        closed = evaluations["th095-whole-build-closed"].outcome
        self.assertEqual(closed.verdict, Verdict.PASS)
        self.assertEqual(closed.diagnostics, ())
        self.assertEqual(closed.facts["objects"], "88/88")
        self.assertEqual(closed.facts["exact_functions"], 696)

    def test_target_hash_beats_equal_version_labels(self) -> None:
        fixture = next(
            item for item in load_fixture_suite() if item.id == "th105-target-epoch-reset"
        )
        evaluation = evaluate_fixture(fixture)
        self.assertEqual(evaluation.outcome.verdict, Verdict.FAIL)
        self.assertTrue(evaluation.outcome.facts["version_labels_equal"])

    def test_missing_relocation_content_is_incomplete_not_pass(self) -> None:
        fixture = next(
            item
            for item in load_fixture_suite()
            if item.id == "th08-relocation-literal-content"
        )
        unknown_input = dict(fixture.input)
        unknown_input["target_data_hex"] = None
        evaluation = evaluate_fixture(replace(fixture, input=unknown_input))
        self.assertEqual(evaluation.outcome.verdict, Verdict.INCOMPLETE)
        self.assertEqual(
            evaluation.outcome.diagnostics,
            ("relocation-destination-content-unknown",),
        )

    def test_owned_extent_arithmetic_is_checked_independently(self) -> None:
        fixture = next(
            item
            for item in load_fixture_suite()
            if item.id == "th105-reimu-owned-extents"
        )
        wrong_input = dict(fixture.input)
        wrong_input["declared_owned_bytes"] = 46129
        evaluation = evaluate_fixture(replace(fixture, input=wrong_input))
        self.assertEqual(evaluation.outcome.verdict, Verdict.FAIL)
        self.assertEqual(evaluation.outcome.diagnostics, ("extent-arithmetic-mismatch",))

    def test_compiler_binary_alone_is_incomplete_toolchain_coverage(self) -> None:
        fixture = next(
            item
            for item in load_fixture_suite()
            if item.id == "th04-toolchain-surface-coverage"
        )
        narrow_input = dict(fixture.input)
        narrow_input["fingerprinted_surfaces"] = ["active-tcc"]
        evaluation = evaluate_fixture(replace(fixture, input=narrow_input))
        self.assertEqual(evaluation.outcome.verdict, Verdict.INCOMPLETE)
        self.assertEqual(
            evaluation.outcome.diagnostics,
            ("toolchain-surface-coverage-incomplete",),
        )
        self.assertEqual(len(evaluation.outcome.facts["missing_surfaces"]), 13)

    def test_different_codegen_context_does_not_override_equal_bytes(self) -> None:
        fixture = next(
            item
            for item in load_fixture_suite()
            if item.id == "th105-ltcg-context-mismatch"
        )
        exact_input = dict(fixture.input)
        exact_input["differing_bytes"] = 0
        evaluation = evaluate_fixture(replace(fixture, input=exact_input))
        self.assertEqual(evaluation.outcome.verdict, Verdict.PASS)
        self.assertEqual(evaluation.outcome.diagnostics, ())

    def test_shared_mutable_workspace_is_rejected(self) -> None:
        fixture = next(
            item
            for item in load_fixture_suite()
            if item.id == "th04-concurrent-workspace-isolation"
        )
        shared_input = dict(fixture.input)
        shared_input["workspace_names"] = ["TH04PROB", "TH04PROB"]
        evaluation = evaluate_fixture(replace(fixture, input=shared_input))
        self.assertEqual(evaluation.outcome.verdict, Verdict.FAIL)
        self.assertEqual(evaluation.outcome.diagnostics, ("workspace-collision",))

    def test_manifest_detects_fixture_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / "history"
            shutil.copytree(DEFAULT_FIXTURE_DIRECTORY, copied)
            fixture = copied / "th04-boundary-undercoverage.json"
            fixture.write_text(fixture.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            with self.assertRaisesRegex(RegressionFixtureError, "digest mismatch"):
                load_fixture_suite(copied)

    def test_manifest_must_cover_every_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / "history"
            shutil.copytree(DEFAULT_FIXTURE_DIRECTORY, copied)
            (copied / "unlisted.json").write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(RegressionFixtureError, "coverage mismatch"):
                load_fixture_suite(copied)

    def test_provenance_verifier_checks_remote_commit_and_blob(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(("git", "init", "-q"), cwd=root, check=True)
            subprocess.run(
                ("git", "config", "user.name", "Fixture Test"), cwd=root, check=True
            )
            subprocess.run(
                ("git", "config", "user.email", "fixture@example.invalid"),
                cwd=root,
                check=True,
            )
            subprocess.run(
                ("git", "remote", "add", "origin", "git@github.com:N0zoM1z0/test.git"),
                cwd=root,
                check=True,
            )
            (root / "evidence.txt").write_text("bounded evidence\n", encoding="utf-8")
            subprocess.run(("git", "add", "evidence.txt"), cwd=root, check=True)
            subprocess.run(("git", "commit", "-q", "-m", "Add evidence"), cwd=root, check=True)
            commit = subprocess.run(
                ("git", "rev-parse", "HEAD"),
                cwd=root,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            ).stdout.strip()
            fixture = HistoricalFixture(
                id="test-provenance",
                title="Test provenance",
                project="test",
                contract=RegressionContract.BOUNDARY_COVERAGE,
                provenance=FixtureProvenance(
                    repository="N0zoM1z0/test",
                    commit=commit,
                    paths=("evidence.txt",),
                    observation="The committed blob exists.",
                ),
                input={
                    "candidate_start": "0x1",
                    "candidate_size": 1,
                    "accepted_start": "0x1",
                    "accepted_size": 1,
                },
                expected_verdict=Verdict.PASS,
                expected_diagnostics=(),
            )
            report = verify_fixture_provenance({"test": root}, fixtures=(fixture,))
            self.assertTrue(report.passed)
            missing = replace(
                fixture,
                provenance=replace(fixture.provenance, paths=("missing.txt",)),
            )
            report = verify_fixture_provenance({"test": root}, fixtures=(missing,))
            self.assertFalse(report.passed)
            self.assertEqual(
                report.checks[0].diagnostics,
                ("provenance-path-missing:missing.txt",),
            )


if __name__ == "__main__":
    unittest.main()
