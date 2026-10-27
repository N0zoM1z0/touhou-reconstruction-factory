from __future__ import annotations

import unittest
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace

try:
    import anyio

    from reconstruction_factory.analysis_mcp import (
        _arguments,
        _analysis_slot,
        _bounded_text_output,
        _ghidra_schema,
        _run_native_ghidra_command,
        _ACTIVE_PROVIDERS,
        _ida_input_schema,
        _mcp_tool_input_schema,
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

    def test_native_ghidra_discovery_exposes_optional_preview_budget(self) -> None:
        schema = _ghidra_schema("decompile", preview=True)
        self.assertEqual(schema["properties"]["max_output_chars"]["default"], 8000)
        self.assertNotIn("max_output_chars", schema["required"])
        self.assertNotIn("max_output_chars", _ghidra_schema("decompile")["properties"])

    def test_analysis_capacity_is_independent_between_repositories(self) -> None:
        async def check():
            async with _analysis_slot("other-main", "other", 1):
                async with _analysis_slot("other-op", "other", 1):
                    async with _analysis_slot("th03-main", "th03", 1):
                        self.assertEqual(len(_ACTIVE_PROVIDERS), 3)
                        with self.assertRaisesRegex(AnalysisError, "other-extra.*other"):
                            async with _analysis_slot("other-extra", "other", 0.01):
                                self.fail("same repository exceeded its limit")
            self.assertEqual(_ACTIVE_PROVIDERS, {})
        anyio.run(check)

    def test_overlapping_provider_waits_then_runs_without_overlap(self) -> None:
        async def check():
            entered = anyio.Event()
            finished = anyio.Event()
            async def first():
                async with _analysis_slot("th03-main", "th03", 1):
                    entered.set()
                    await anyio.sleep(0.1)
                finished.set()
            async def second():
                await entered.wait()
                async with _analysis_slot("th03-main", "th03", 1):
                    self.assertTrue(finished.is_set())
            async with anyio.create_task_group() as tasks:
                tasks.start_soon(first)
                tasks.start_soon(second)
            self.assertEqual(_ACTIVE_PROVIDERS, {})
        anyio.run(check)

    def test_cancelled_waiter_and_owner_do_not_leak_analysis_capacity(self) -> None:
        async def check():
            with self.assertRaisesRegex(RuntimeError, "owner failed"):
                async with _analysis_slot("th03-main", "th03", 1):
                    with anyio.move_on_after(0.02) as scope:
                        async with _analysis_slot("th03-main", "th03", 1):
                            self.fail("same provider overlapped")
                    self.assertTrue(scope.cancel_called)
                    self.assertEqual(_ACTIVE_PROVIDERS, {"th03-main": "th03"})
                    raise RuntimeError("owner failed")
            self.assertEqual(_ACTIVE_PROVIDERS, {})
            async with _analysis_slot("th03-main", "th03", 1):
                pass
        anyio.run(check)

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

    def test_ida_normalizes_addresses_for_native_and_legacy_calls(self) -> None:
        for address in (4198400, "4198400", " 0X401000 ", "0x401000", "00401000", "0000000000401000"):
            for field in ("address", "start_address", "function_address", "memory_address"):
                arguments = {field: address}
                _validate_ida_arguments("get_function_by_address", arguments)
                self.assertEqual(int(arguments[field], 16), 0x401000)
        for address in (True, -1, 1 << 64, "10000:0000", "0x1; id", "", {}):
            with self.subTest(address=address):
                with self.assertRaisesRegex(AnalysisError, "IDA address is invalid; use"):
                    _validate_ida_arguments("get_function_by_address", {"address": address})

    def test_ida_discovery_advertises_normalization_without_mutating_upstream(self) -> None:
        schema = {"type": "object", "properties": {
            "address": {"type": "string", "title": "Address"},
            "size": {"type": "integer"}}, "required": ["address", "size"]}
        advertised = _ida_input_schema(schema)
        self.assertEqual(schema["properties"]["address"], {"type": "string", "title": "Address"})
        self.assertEqual(advertised["properties"]["address"]["anyOf"][1]["type"], "integer")
        self.assertEqual(advertised["properties"]["size"], schema["properties"]["size"])
        self.assertEqual(advertised["required"], schema["required"])

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
        with self.assertRaisesRegex(AnalysisError, "unsupported fields"):
            _validate_ghidra_arguments("check", {"limit": 1})

    def test_ghidra_accepts_web_address_representations(self) -> None:
        for arguments in ({"address": " 0X1EA5D "}, {"addresses": "0x1EA5D"},
                          {"addresses": 125533}, {"addresses": ["125533"]},
                          {"address": "0001ea5d"}, {"address": "1EA5D"}):
            forwarded = _validate_ghidra_arguments("function", arguments)
            self.assertEqual(int(forwarded["addresses"][0], 16), 0x1EA5D)
        segmented = _validate_ghidra_arguments(
            "function", {"address": "1e8f:016d"}, allow_segmented=True
        )
        self.assertEqual(segmented["addresses"], ["1e8f:016d"])
        with self.assertRaises(AnalysisError):
            _validate_ghidra_arguments("function", {"address": "1e8f:016d"})

    def test_ghidra_recovers_formatting_without_accepting_invalid_addresses(self) -> None:
        for address in (True, -1, 1 << 64, "10000:0000", "0000:10000", "0x1; id", {}, ""):
            with self.subTest(address=address):
                with self.assertRaisesRegex(AnalysisError, "use address or addresses"):
                    _validate_ghidra_arguments("function", {"address": address}, allow_segmented=True)
        with self.assertRaisesRegex(AnalysisError, "function accepts: addresses"):
            _validate_ghidra_arguments("function", {"addresses": ["0x1"], "typo": 1})

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

    def test_native_mcp_tool_schema_uses_sdk_python_field_name(self) -> None:
        class Tool:
            input_schema = {
                "type": "object",
                "properties": {"address": {"type": "string"}},
                "required": ["address"],
            }

        self.assertEqual(
            _mcp_tool_input_schema(Tool()),
            Tool.input_schema,
        )


@unittest.skipIf(_arguments is None, "MCP v2 optional dependency is not installed")
class GhidraOutputTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.config = SimpleNamespace(
            path=self.root / "operator/service.toml", state_directory=self.root / "state",
            evidence_store=self.root / "evidence", policy_path=self.root / "policy.json",
            repositories=(), analysis_providers=(),
        )

    def test_large_batch_keeps_navigation_to_functions_beyond_the_preview(self) -> None:
        first = "/* First at 00401000 */\n" + "  update();\n" * 1000
        text = first + "/* Second at 00402000 */\n  return;\n"
        result = _bounded_text_output(text, self.config, operation="decompile")
        self.assertLessEqual(len(result["text"]), 8000)
        self.assertTrue(result["text"].endswith("\n"))
        self.assertTrue(result["factory_output_truncated"])
        self.assertNotIn("Second", result["text"])
        self.assertEqual(result["total_chars"], len(text))
        self.assertEqual(result["next_line"], result["text"].count("\n") + 1)
        self.assertEqual(result["functions"][1], {
            "name": "Second", "address": "00402000", "start_line": 1002, "end_line": 1003,
        })

    def test_unicode_long_lines_and_complete_small_results_have_honest_offsets(self) -> None:
        text = "界" * 10 + "\u2028tail"
        result = _bounded_text_output(text, self.config, max_output_chars=5)
        self.assertEqual(result["text"], "界" * 5)
        self.assertEqual(result["returned_bytes"], 15)
        self.assertEqual(result["total_lines"], 1)
        self.assertEqual(result["next_line"], 1)
        self.assertTrue(result["preview_ends_mid_line"])
        small = _bounded_text_output("one\ntwo\n", self.config)
        self.assertEqual(small["text"], "one\ntwo\n")
        self.assertFalse(small["factory_output_truncated"])
        self.assertIsNone(small["next_line"])

    def test_full_and_partial_query_files_survive_without_retaining_startup_noise(self) -> None:
        script = self.root / "query.py"
        text = "λ output\n" * 3000
        script.write_text(
            "import sys\nfrom pathlib import Path\nprint('startup noise')\n"
            f"if sys.argv[1] != 'check': Path(sys.argv[2]).write_text({text!r})\n"
            "if '0xdead' in sys.argv: raise SystemExit(9)\n"
        )
        provider = SimpleNamespace(command=Path(sys.executable), arguments=(str(script),), timeout_seconds=5)
        result, path = _run_native_ghidra_command(provider, self.root, "decompile", {"addresses": ["0x1"]})
        self.assertEqual(result, text)
        self.assertEqual(path.read_text(), text)
        context, context_path = _run_native_ghidra_command(
            provider, self.root, "function_context", {"addresses": ["0x1"]}
        )
        self.assertEqual(context, text)
        context_path.unlink()
        context_path.parent.rmdir()
        with self.assertRaises(subprocess.CalledProcessError) as raised:
            _run_native_ghidra_command(provider, self.root, "decompile", {"addresses": ["0xdead"]})
        self.assertIn("Partial output retained at .analysis/", raised.exception.stderr)
        self.assertEqual(len(list((self.root / ".analysis/factory-native-ghidra").glob("*/result.txt"))), 2)
        _, check_path = _run_native_ghidra_command(provider, self.root, "check", {})
        self.assertIsNone(check_path)
        self.assertEqual(len(list((self.root / ".analysis/factory-native-ghidra").iterdir())), 2)

    def test_timeout_stops_analyzer_children_and_keeps_partial_output(self) -> None:
        import fcntl

        script = self.root / "slow-provider.py"
        child = (
            "import fcntl,time\nfrom pathlib import Path\n"
            "gate=Path('analyzer.lock').open('a+')\n"
            "fcntl.flock(gate,fcntl.LOCK_EX)\n"
            "Path('analyzer-ready').touch()\ntime.sleep(60)\n"
        )
        script.write_text(
            "import subprocess,sys,time\nfrom pathlib import Path\n"
            f"subprocess.Popen([sys.executable,'-c',{child!r}])\n"
            "while not Path('analyzer-ready').exists(): time.sleep(.01)\n"
            "Path(sys.argv[2]).write_text('partial decompilation')\ntime.sleep(60)\n"
        )
        provider = SimpleNamespace(command=Path(sys.executable), arguments=(str(script),), timeout_seconds=1)
        with self.assertRaises(subprocess.TimeoutExpired) as raised:
            _run_native_ghidra_command(provider, self.root, "decompile", {"addresses": ["0x1"]})
        self.assertIn("Partial output retained at .analysis/", raised.exception.stderr)
        path = next((self.root / ".analysis/factory-native-ghidra").glob("*/result.txt"))
        self.assertEqual(path.read_text(), "partial decompilation")
        with (self.root / "analyzer.lock").open("a+") as gate:
            # An orphan analyzer would keep this lock and block the next query.
            fcntl.flock(gate, fcntl.LOCK_EX | fcntl.LOCK_NB)


if __name__ == "__main__":
    unittest.main()
