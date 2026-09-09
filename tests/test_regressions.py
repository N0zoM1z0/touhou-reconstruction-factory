from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import shutil
import tempfile
import unittest

from reconstruction_factory.errors import RegressionFixtureError
from reconstruction_factory.ontology import Verdict
from reconstruction_factory.regressions import (
    DEFAULT_FIXTURE_DIRECTORY,
    evaluate_fixture,
    load_fixture_suite,
    run_fixture_suite,
)


class HistoricalRegressionTests(unittest.TestCase):
    def test_packaged_suite_matches_all_expected_verdicts(self) -> None:
        report = run_fixture_suite()
        self.assertTrue(report.passed)
        self.assertEqual(len(report.evaluations), 6)
        self.assertEqual(
            {item.project for item in report.evaluations},
            {"th04", "th08", "th095", "th105"},
        )

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


if __name__ == "__main__":
    unittest.main()
