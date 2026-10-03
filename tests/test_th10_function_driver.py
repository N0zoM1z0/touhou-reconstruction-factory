from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from reconstruction_factory.errors import ReplayError
from reconstruction_factory.ontology import (
    Claim,
    ClaimType,
    EvidenceClass,
    Extent,
    Subject,
    SubjectKind,
    Verdict,
)
from reconstruction_factory.oracle_receipts import Coldness
from reconstruction_factory.replay_drivers import (
    RawExecution,
    Th10FunctionDriver,
    Th10LinkedPeFunctionDriver,
)


class Th10FunctionDriverTests(unittest.TestCase):
    def test_normal_coff_unit_prepares_and_decodes_exact_replay(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in (
                "scripts",
                "config",
                "resources",
                ".tools/msvc710-sp1/Vc7/bin",
                ".tools/msvc710-sp1/Vc7/include",
                ".tools/msvc710-sp1/Vc7/PlatformSDK/Include",
            ):
                (root / relative).mkdir(parents=True, exist_ok=True)
            for relative in (
                "scripts/build-match-unit.py",
                "scripts/compare-coff-function.py",
                "scripts/msvc_symbols.py",
            ):
                (root / relative).write_text(
                    "raise SystemExit(0)\n", encoding="utf-8"
                )
            for relative in (
                "scripts/compile-probe.sh",
                "scripts/run-headless-wine.sh",
            ):
                (root / relative).write_text(
                    "#!/usr/bin/env bash\nexit 0\n", encoding="utf-8"
                )
            (root / "config/match-units.toml").write_text(
                """schema_version = 1
[units.normal-c]
artifact_kind = "coff"
profile = ["/O2", "/Gy"]
target_address = 0x00401000
size = 4
""",
                encoding="utf-8",
            )
            (root / "config/target.toml").write_text(
                "[target]\nfilename = 'th10.exe'\n", encoding="utf-8"
            )
            (root / "config/tools.lock.toml").write_text(
                "[msvc71]\ncompiler_version = '13.10.6030'\n",
                encoding="utf-8",
            )
            (root / "resources/th10.exe").write_bytes(b"TARGET")
            tool_root = root / ".tools/msvc710-sp1"
            for relative, payload in (
                ("Vc7/bin/cl.exe", b"compiler"),
                ("Vc7/bin/c1.dll", b"c frontend"),
                ("Vc7/bin/c1xx.dll", b"cpp frontend"),
                ("Vc7/bin/c2.dll", b"optimizer"),
                ("Vc7/include/test.h", b"include"),
                ("Vc7/PlatformSDK/Include/windows.h", b"sdk"),
            ):
                (tool_root / relative).parent.mkdir(parents=True, exist_ok=True)
                (tool_root / relative).write_bytes(payload)

            subject = Subject(
                "th10-main:function:00401000",
                "target:th10-main",
                SubjectKind.FUNCTION,
                "NormalC",
                (Extent("pe-va", "0x00401000", 4),),
            )
            claim = Claim(
                "claim:th10-main:function:00401000:codegen-exact",
                subject.id,
                ClaimType.CODEGEN_EXACT,
                subject.target_identity_id,
                {"exact": True, "unit": "normal-c", "artifact_kind": "coff"},
                EvidenceClass.CORROBORATED,
                "toolchain:th10-msvc71",
            )
            snapshot = SimpleNamespace(
                project=SimpleNamespace(id="th10"),
                adapter_id="windows-pe-ledgers-v1",
            )
            driver = Th10FunctionDriver()
            with patch.dict(
                "os.environ", {"TH10_MSVC71_ROOT": str(tool_root)}
            ):
                plan = driver.prepare(
                    root, snapshot, claim, subject, "test-run"
                )

            self.assertTrue(driver.supports(snapshot, claim))
            self.assertEqual(plan.coldness, Coldness.FORCED_RECOMPILE)
            self.assertEqual(plan.oracle_id, "windows.msvc71.normal-coff-function-exact")
            self.assertEqual(plan.metadata["artifact_kind"], "coff")
            report = {
                "unit": "normal-c",
                "artifact_kind": "coff",
                "result": "exact",
                "target_address": "0x00401000",
                "size": 4,
                "matched_bytes": 4,
                "relocations": [],
            }
            outcome = driver.decode(
                plan,
                claim,
                subject,
                (
                    RawExecution("compile", 0, False, 1, b"built\n", b""),
                    RawExecution(
                        "compare",
                        0,
                        False,
                        1,
                        json.dumps(report).encode(),
                        b"",
                    ),
                ),
            )
            self.assertEqual(outcome.verdict, Verdict.PASS)
            self.assertEqual(outcome.observed_bytes, 4)

    def test_ltcg_profile_is_not_accepted_as_normal_coff(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in ("scripts", "config", "resources"):
                (root / relative).mkdir(parents=True, exist_ok=True)
            for relative in (
                "scripts/build-match-unit.py",
                "scripts/compare-coff-function.py",
                "scripts/compile-probe.sh",
                "scripts/run-headless-wine.sh",
            ):
                (root / relative).write_text("input\n", encoding="utf-8")
            (root / "config/match-units.toml").write_text(
                """[units.ltcg]
artifact_kind = "coff"
profile = ["/O2", "/GL"]
target_address = 0x00401000
size = 4
""",
                encoding="utf-8",
            )
            (root / "config/target.toml").write_text(
                "[target]\nfilename = 'th10.exe'\n", encoding="utf-8"
            )
            (root / "config/tools.lock.toml").write_text(
                "[msvc71]\ncompiler_version = '13.10.6030'\n",
                encoding="utf-8",
            )
            (root / "resources/th10.exe").write_bytes(b"TARGET")
            subject = Subject(
                "th10-main:function:00401000",
                "target:th10-main",
                SubjectKind.FUNCTION,
                "Ltcg",
                (Extent("pe-va", "0x00401000", 4),),
            )
            claim = Claim(
                "claim:th10-main:function:00401000:codegen-exact",
                subject.id,
                ClaimType.CODEGEN_EXACT,
                subject.target_identity_id,
                {"exact": True, "unit": "ltcg", "artifact_kind": "coff"},
                EvidenceClass.CORROBORATED,
                "toolchain:th10-msvc71",
            )
            snapshot = SimpleNamespace(
                project=SimpleNamespace(id="th10"),
                adapter_id="windows-pe-ledgers-v1",
            )
            with self.assertRaisesRegex(ReplayError, "normal-COFF"):
                Th10FunctionDriver().prepare(
                    root, snapshot, claim, subject, "test-run"
                )

    def test_linked_pe_unit_has_distinct_route_and_exact_decoder(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in ("scripts", "config", "resources"):
                (root / relative).mkdir(parents=True, exist_ok=True)
            for relative in (
                "scripts/build-match-unit.py",
                "scripts/ltcg_link.py",
                "scripts/runtime_archive.py",
                "scripts/compile-probe.sh",
                "scripts/run-headless-wine.sh",
                "scripts/compare-linked-function.py",
                "scripts/linked_image.py",
            ):
                (root / relative).write_text("input\n", encoding="utf-8")
            capstone_root = root / ".tools/capstone/capstone"
            for relative in (
                "__init__.py",
                "x86.py",
                "x86_const.py",
                "lib/libcapstone.so",
            ):
                path = capstone_root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"capstone")
            (root / "scripts/repo-python").write_text(
                "#!/usr/bin/env bash\n"
                f"printf '%s\\n%s\\n' /usr/bin/python3 {capstone_root / '__init__.py'}\n",
                encoding="utf-8",
            )
            (root / "scripts/repo-python").chmod(0o755)
            (root / "config/match-units.toml").write_text(
                """[units.linked]
artifact_kind = "linked-pe"
profile = ["/TP", "/O2", "/GL"]
link_profile = ["/ltcg", "/nodefaultlib"]
target_address = 0x00401000
size = 4
""",
                encoding="utf-8",
            )
            (root / "config/target.toml").write_text(
                "[target]\nfilename = 'th10.exe'\n", encoding="utf-8"
            )
            (root / "config/tools.lock.toml").write_text(
                "[msvc71]\ncompiler_version = '13.10.6030'\n",
                encoding="utf-8",
            )
            (root / "resources/th10.exe").write_bytes(b"TARGET")
            subject = Subject(
                "th10-main:function:00401000",
                "target:th10-main",
                SubjectKind.FUNCTION,
                "Linked",
                (Extent("pe-va", "0x00401000", 4),),
            )
            claim = Claim(
                "claim:th10-main:function:00401000:codegen-exact",
                subject.id,
                ClaimType.CODEGEN_EXACT,
                subject.target_identity_id,
                {
                    "exact": True,
                    "unit": "linked",
                    "artifact_kind": "linked-pe",
                },
                EvidenceClass.CORROBORATED,
                "toolchain:th10-msvc71",
            )
            snapshot = SimpleNamespace(
                project=SimpleNamespace(id="th10"),
                adapter_id="windows-pe-ledgers-v1",
            )
            driver = Th10LinkedPeFunctionDriver()
            plan = driver.prepare(root, snapshot, claim, subject, "test-run")

            self.assertTrue(driver.supports(snapshot, claim))
            self.assertFalse(Th10FunctionDriver().supports(snapshot, claim))
            self.assertEqual(plan.coldness, Coldness.FORCED_RECOMPILE)
            self.assertEqual(
                plan.oracle_id, "windows.msvc71.linked-pe-function-exact"
            )
            self.assertIn(
                "vc71sp1-linker", {item.id for item in plan.toolchain_components}
            )
            report = {
                "unit": "linked",
                "artifact_kind": "linked-pe",
                "result": "exact",
                "target_address": "0x00401000",
                "size": 4,
                "matched_bytes": 4,
                "compared_size": 4,
                "matched_compared_bytes": 4,
                "normalization_complete": True,
                "linkages": [],
                "data_spans": [],
            }
            outcome = driver.decode(
                plan,
                claim,
                subject,
                (
                    RawExecution("compile-link", 0, False, 1, b"built\n", b""),
                    RawExecution(
                        "compare",
                        0,
                        False,
                        1,
                        json.dumps(report).encode(),
                        b"",
                    ),
                ),
            )
            self.assertEqual(outcome.verdict, Verdict.PASS)
            self.assertEqual(outcome.observed_bytes, 4)
            self.assertEqual(
                outcome.normalizations, ("linked-pe-symbolic-field-replay-v1",)
            )

            del report["linkages"]
            incomplete = driver.decode(
                plan,
                claim,
                subject,
                (
                    RawExecution("compile-link", 0, False, 1, b"built\n", b""),
                    RawExecution(
                        "compare",
                        0,
                        False,
                        1,
                        json.dumps(report).encode(),
                        b"",
                    ),
                ),
            )
            self.assertEqual(incomplete.verdict, Verdict.INCOMPLETE)
            self.assertIn("native-linked-report-incomplete", incomplete.diagnostics)


if __name__ == "__main__":
    unittest.main()
