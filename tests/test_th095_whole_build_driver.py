from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from reconstruction_factory.ontology import (
    Claim,
    ClaimType,
    EvidenceClass,
    Subject,
    SubjectKind,
    Verdict,
)
from reconstruction_factory.oracle_receipts import Coldness
from reconstruction_factory.replay_drivers import (
    RawExecution,
    Th095WholeBuildDriver,
)
from reconstruction_factory.replay_identity import file_sha256


class Th095WholeBuildDriverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        for relative in (
            "scripts",
            "config",
            "resources",
            ".tools/msvc710/Vc7/bin",
            ".tools/msvc710/Vc7/include",
            ".tools/msvc710/Vc7/lib",
            ".tools/msvc710/Vc7/PlatformSDK/Include",
            ".tools/msvc710/Vc7/PlatformSDK/Lib",
        ):
            (self.root / relative).mkdir(parents=True, exist_ok=True)
        (self.root / "scripts/build-whole.py").write_text(
            "raise SystemExit(0)\n", encoding="utf-8"
        )
        (self.root / "config/match-units.toml").write_text(
            "schema_version = 1\n", encoding="utf-8"
        )
        (self.root / "config/target.toml").write_text(
            "[target]\nfilename = 'th095.exe'\n", encoding="utf-8"
        )
        (self.root / "config/tools.lock.toml").write_text(
            "[msvc71]\n", encoding="utf-8"
        )
        (self.root / "resources/th095.exe").write_bytes(b"TARGET")
        self.compiler = self.root / ".tools/msvc710/Vc7/bin/cl.exe"
        self.linker = self.root / ".tools/msvc710/Vc7/bin/link.exe"
        self.compiler.write_bytes(b"compiler")
        self.linker.write_bytes(b"linker")
        for relative in (
            ".tools/msvc710/Vc7/include/test.h",
            ".tools/msvc710/Vc7/lib/test.lib",
            ".tools/msvc710/Vc7/PlatformSDK/Include/windows.h",
            ".tools/msvc710/Vc7/PlatformSDK/Lib/kernel32.lib",
        ):
            (self.root / relative).write_bytes(b"surface")

        self.subject = Subject(
            "th095-main:product",
            "target:th095-main",
            SubjectKind.PRODUCT,
            "TH095 production product",
        )
        self.claim = Claim(
            "claim:th095-main:product:whole-build-closed",
            self.subject.id,
            ClaimType.WHOLE_BUILD_CLOSED,
            self.subject.target_identity_id,
            {
                "closed": True,
                "source_count": 88,
                "profile_count": 2,
                "compile_machine": "i386-coff",
                "link_output": "pe32-i386-windows-gui",
                "zero_unresolved_required": True,
                "whole_image_exact": False,
            },
            EvidenceClass.UNKNOWN,
            "toolchain:th095-msvc71",
        )
        self.driver = Th095WholeBuildDriver()
        with patch.dict(
            "os.environ", {"TH095_MSVC71_ROOT": str(self.root / ".tools/msvc710")}
        ):
            self.plan = self.driver.prepare(
                self.root,
                None,  # prepare uses only the normalized claim and subject.
                self.claim,
                self.subject,
                "factory-20260910T000000Z-000000000000",
            )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def report(self, *, linked: bool = True) -> dict[str, object]:
        report: dict[str, object] = {
            "schema_version": 1,
            "target_sha256": file_sha256(self.root / "resources/th095.exe"),
            "source_count": 88,
            "profile_count": 2,
            "compile": {
                "status": "passed",
                "object_count": 88,
                "machine": "i386-coff",
            },
            "toolchain": {
                "compiler_version": "13.10.3077",
                "compiler_sha256": file_sha256(self.compiler),
                "linker_version": "7.10.3077",
                "linker_sha256": file_sha256(self.linker),
            },
        }
        if linked:
            output = self.root / "build/whole-validation/th095-reconstructed.exe"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(b"MZ-RECONSTRUCTED")
            report["link"] = {
                "status": "passed",
                "flags": ["/SUBSYSTEM:WINDOWS", "/OPT:NOREF"],
                "artifact": {
                    "format": "PE32",
                    "machine": "i386",
                    "subsystem": "windows-gui",
                    "size": output.stat().st_size,
                    "sha256": file_sha256(output),
                },
            }
        else:
            report["link"] = {
                "status": "failed",
                "unresolved_unique_count": 5,
            }
        report_path = self.root / "build/whole-validation/report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report), encoding="utf-8")
        return report

    def execution(self, exit_code: int) -> RawExecution:
        return RawExecution("whole-build", exit_code, False, 10, b"", b"")

    def test_prepare_declares_product_scope_and_cold_output_graph(self) -> None:
        self.assertEqual(self.plan.coldness, Coldness.CLEAN_OUTPUT_GRAPH)
        self.assertEqual(self.plan.stages[0].argv[1], "scripts/build-whole.py")
        self.assertEqual(
            self.plan.metadata["coverage_domain"], "production-translation-units"
        )
        self.assertFalse(self.plan.metadata["whole_image_exact"])

    def test_decode_accepts_complete_zero_unresolved_build(self) -> None:
        report = self.report()
        outcome = self.driver.decode(
            self.plan, self.claim, self.subject, (self.execution(0),)
        )
        self.assertEqual(outcome.verdict, Verdict.PASS)
        self.assertEqual(outcome.report, report)
        self.assertTrue(outcome.coverage and outcome.coverage.complete)
        self.assertEqual(outcome.coverage.observed_units, 88)
        self.assertEqual(outcome.diagnostics, ())

    def test_decode_preserves_complete_link_failure_as_failure(self) -> None:
        self.report(linked=False)
        outcome = self.driver.decode(
            self.plan, self.claim, self.subject, (self.execution(1),)
        )
        self.assertEqual(outcome.verdict, Verdict.FAIL)
        self.assertTrue(outcome.coverage and outcome.coverage.complete)
        self.assertIn("native-whole-build-unresolved-symbols", outcome.diagnostics)

    def test_decode_rejects_force_link_policy_even_on_success(self) -> None:
        report = self.report()
        link_report = report["link"]
        self.assertIsInstance(link_report, dict)
        assert isinstance(link_report, dict)
        flags = link_report["flags"]
        self.assertIsInstance(flags, list)
        assert isinstance(flags, list)
        flags.append("/FORCE:UNRESOLVED")
        self.plan.native_report_path.write_text(json.dumps(report), encoding="utf-8")
        outcome = self.driver.decode(
            self.plan, self.claim, self.subject, (self.execution(0),)
        )
        self.assertEqual(outcome.verdict, Verdict.ERROR)
        self.assertIn("native-link-policy-unsafe", outcome.diagnostics)


if __name__ == "__main__":
    unittest.main()
