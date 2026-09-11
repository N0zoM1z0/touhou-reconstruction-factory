from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

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
from reconstruction_factory.replay_drivers import RawExecution, Th09FunctionDriver


class Th09FunctionDriverTests(unittest.TestCase):
    def test_target_bound_unit_prepares_and_decodes_exact_replay(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in (
                "scripts",
                "config",
                "resources",
                ".tools/msvc710/Vc7/bin",
                ".tools/msvc710/Vc7/include",
                ".tools/msvc710/Vc7/PlatformSDK/Include",
            ):
                (root / relative).mkdir(parents=True, exist_ok=True)
            for relative in (
                "scripts/build-match-unit.py",
                "scripts/compare-coff-function.py",
            ):
                (root / relative).write_text("raise SystemExit(0)\n", encoding="utf-8")
            (root / "scripts/compile-probe.sh").write_text(
                "#!/usr/bin/env bash\nexit 0\n", encoding="utf-8"
            )
            (root / "config/match-units.toml").write_text(
                """schema_version = 1
[units.timer-tick]
target_address = 0x00401000
size = 4
""",
                encoding="utf-8",
            )
            (root / "config/target.toml").write_text(
                "[target]\nfilename = 'th09.exe'\n", encoding="utf-8"
            )
            (root / "config/tools.lock.toml").write_text(
                "[msvc71]\ncompiler_version = '13.10.3077'\n", encoding="utf-8"
            )
            (root / "resources/th09.exe").write_bytes(b"TARGET")
            (root / ".tools/msvc710/Vc7/bin/cl.exe").write_bytes(b"compiler")
            (root / ".tools/msvc710/Vc7/bin/c1xx.dll").write_bytes(b"frontend")
            (root / ".tools/msvc710/Vc7/include/test.h").write_bytes(b"include")
            (root / ".tools/msvc710/Vc7/PlatformSDK/Include/windows.h").write_bytes(
                b"sdk"
            )

            subject = Subject(
                "th09-main:function:00401000",
                "target:th09-main",
                SubjectKind.FUNCTION,
                "Timer::Tick",
                (Extent("pe-va", "0x00401000", 4),),
            )
            claim = Claim(
                "claim:th09-main:function:00401000:codegen-exact",
                subject.id,
                ClaimType.CODEGEN_EXACT,
                subject.target_identity_id,
                {"exact": True, "unit": "timer-tick"},
                EvidenceClass.CORROBORATED,
                "toolchain:th09-msvc71",
            )
            snapshot = SimpleNamespace(
                project=SimpleNamespace(id="th09"),
                adapter_id="windows-pe-ledgers-v1",
            )
            driver = Th09FunctionDriver()
            with patch.dict(
                "os.environ", {"TH09_MSVC71_ROOT": str(root / ".tools/msvc710")}
            ):
                plan = driver.prepare(root, snapshot, claim, subject, "test-run")

            self.assertTrue(driver.supports(snapshot, claim))
            self.assertEqual(plan.coldness, Coldness.FORCED_RECOMPILE)
            self.assertEqual(
                [stage.argv[-3:] for stage in plan.stages],
                [
                    ("scripts/build-match-unit.py", "--unit", "timer-tick"),
                    ("--unit", "timer-tick", "--json"),
                ],
            )
            report = {
                "unit": "timer-tick",
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
                        "compare", 0, False, 1, json.dumps(report).encode(), b""
                    ),
                ),
            )
            self.assertEqual(outcome.verdict, Verdict.PASS)
            self.assertEqual(outcome.observed_bytes, 4)


if __name__ == "__main__":
    unittest.main()
