from __future__ import annotations

import unittest

try:
    from reconstruction_factory.analysis_mcp import (
        _arguments,
        _validate_ghidra_arguments,
        _validate_ida_arguments,
        _validate_ida_metadata,
    )
except ImportError:
    _arguments = None

from reconstruction_factory.errors import AnalysisError
from reconstruction_factory.ontology import TargetIdentity


@unittest.skipIf(_arguments is None, "MCP v2 optional dependency is not installed")
class AnalysisGatewayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.target = TargetIdentity(
            id="target:fixture",
            project_id="fixture",
            product_id="fixture-main",
            game="fixture",
            version="1.0",
            region="original",
            format="pe",
            size=4096,
            sha256="1" * 64,
            md5="2" * 32,
        )

    def test_arguments_are_one_bounded_json_object(self) -> None:
        self.assertEqual(_arguments('{"address":"0x401000"}')["address"], "0x401000")
        for invalid in ("[]", "null", "{", '{"value":"' + "x" * 70000 + '"}'):
            with self.subTest(invalid=invalid[:20]):
                with self.assertRaises(AnalysisError):
                    _arguments(invalid)

    def test_ida_allowlisted_arguments_cannot_smuggle_host_authority(self) -> None:
        _validate_ida_arguments("get_function_by_address", {"address": "0x00401000"})
        with self.assertRaisesRegex(AnalysisError, "forbidden authority"):
            _validate_ida_arguments("decompile_function", {"path": "/etc/passwd"})
        with self.assertRaisesRegex(AnalysisError, "forbidden authority"):
            _validate_ida_arguments("decompile_function", {"options": {"script": "id"}})
        with self.assertRaisesRegex(AnalysisError, "1 through 200"):
            _validate_ida_arguments("list_functions", {"offset": 0, "count": 0})
        with self.assertRaisesRegex(AnalysisError, "1 through 256"):
            _validate_ida_arguments(
                "read_memory_bytes", {"memory_address": "0x401000", "size": 257}
            )

    def test_ghidra_operations_are_exact_and_bounded(self) -> None:
        forwarded = _validate_ghidra_arguments(
            "disassemble",
            {"addresses": ["0x10000"], "instruction_count": 80},
        )
        self.assertEqual(forwarded["addresses"], ["0x10000"])
        with self.assertRaisesRegex(AnalysisError, "unsupported fields"):
            _validate_ghidra_arguments("check", {"command": "id"})
        with self.assertRaisesRegex(AnalysisError, "1 through 16"):
            _validate_ghidra_arguments("function", {"addresses": []})

    def test_ida_metadata_must_match_factory_target_identity(self) -> None:
        attestation = _validate_ida_metadata(
            {
                "module": "fixture.exe",
                "sha256": "1" * 64,
                "md5": "2" * 32,
                "filesize": "0x1000",
            },
            self.target,
        )
        self.assertEqual(attestation["status"], "passed")
        with self.assertRaisesRegex(AnalysisError, "does not match"):
            _validate_ida_metadata(
                {
                    "sha256": "3" * 64,
                    "md5": "2" * 32,
                    "filesize": "0x1000",
                },
                self.target,
            )


if __name__ == "__main__":
    unittest.main()
