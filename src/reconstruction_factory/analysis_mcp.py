"""Target-bound gateway to operator-registered semantic analysis providers."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from functools import partial
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
import tomllib
import time
from typing import Any
from urllib.parse import urlsplit

import anyio
from mcp import Client, ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .errors import AnalysisError, ReplayError
from .ontology import TargetIdentity, to_primitive
from .oracle_receipts import canonical_sha256
from .replay_identity import repository_lock
from .service_config import AnalysisProviderRegistration, ServiceConfig


_MAX_ARGUMENT_BYTES = 65536
_MAX_OUTPUT_BYTES = 262144
_GHIDRA_PREVIEW_CHARS = 8000
_GHIDRA_PREVIEW_MAX = 65536
_MAX_IDA_MEMORY_BYTES = 65536
_MAX_ACTIVE_ANALYSES_PER_REPOSITORY = 2
_ACTIVE_PROVIDERS: dict[str, str] = {}

_IDA_READ_ALLOWED = frozenset(
    {
        "check_connection",
        "get_metadata",
        "get_function_by_name",
        "get_function_by_address",
        "get_current_address",
        "get_current_function",
        "convert_number",
        "list_functions",
        "list_globals_filter",
        "list_globals",
        "list_imports",
        "list_strings_filter",
        "list_strings",
        "list_local_types",
        "decompile_function",
        "disassemble_function",
        "get_xrefs_to",
        "get_xrefs_to_field",
        "get_callees",
        "get_callers",
        "get_entry_points",
        "get_global_variable_value_by_name",
        "get_global_variable_value_at_address",
        "get_stack_frame_variables",
        "get_defined_structures",
        "analyze_struct_detailed",
        "get_struct_at_address",
        "get_struct_info_simple",
        "search_structures",
        "read_memory_bytes",
        "data_read_byte",
        "data_read_word",
        "data_read_dword",
        "data_read_qword",
        "data_read_string",
    }
)
_IDA_METADATA_WRITE_ALLOWED = frozenset(
    {
        "set_comment",
        "rename_local_variable",
        "rename_global_variable",
        "set_global_variable_type",
        "rename_function",
        "set_function_prototype",
        "declare_c_type",
        "set_local_variable_type",
        "rename_stack_frame_variable",
        "create_stack_frame_variable",
        "set_stack_frame_variable_type",
        "delete_stack_frame_variable",
    }
)
_IDA_NATIVE_ALLOWED = _IDA_READ_ALLOWED | _IDA_METADATA_WRITE_ALLOWED
_GHIDRA_OPERATIONS = {
    "check": "Attest the configured Ghidra toolchain, project, and target.",
    "decompile": "Decompile one or more bounded function addresses.",
    "function": "Return function metadata for bounded addresses.",
    "disassemble": "Disassemble a bounded instruction count at addresses.",
    "callers": "Return callers of bounded function addresses.",
    "callees": "Return callees of bounded function addresses.",
    "xrefs_to": "Return bounded references to addresses.",
    "xrefs_from": "Return bounded references from addresses.",
    "list_functions": "Page functions with an optional name filter.",
    "search_strings": "Search strings with a bounded query and result limit.",
}
_NATIVE_GHIDRA_OPERATIONS = {
    **_GHIDRA_OPERATIONS,
    "function_context": "Return function metadata, callers, callees and decompilation in one Ghidra launch.",
}
_ADDRESS = re.compile(r"^0x[0-9a-fA-F]{1,16}$")
_SEGMENTED_ADDRESS = re.compile(r"^[0-9a-fA-F]{1,4}:[0-9a-fA-F]{1,4}$")


class AnalysisGateway:
    """A target-bound provisional semantic-analysis surface."""

    def __init__(self, config: ServiceConfig) -> None:
        self.config = config

    def list_providers(
        self, repository_id: str | None = None
    ) -> tuple[dict[str, Any], ...]:
        if repository_id is not None:
            self.config.repository(repository_id)
        return tuple(
            {
                **item.public_dict(),
                "availability": "not-probed",
                "provider_binding_sha256": canonical_sha256(item.identity_dict()),
            }
            for item in self.config.analysis_providers
            if repository_id is None or item.repository_id == repository_id
        )

    async def list_operations(
        self,
        provider_id: str,
        *,
        filter: str,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        _page_bounds(limit, offset)
        if not isinstance(filter, str) or len(filter.encode("utf-8")) > 128:
            raise AnalysisError("analysis operation filter exceeds 128 UTF-8 bytes")
        provider = self.config.analysis_provider(provider_id)
        if provider.backend in {"attested-ghidra-proxy-v1", "attested-ghidra-command-v1"}:
            target = (await self._target(provider)
                      if provider.backend == "attested-ghidra-command-v1" else None)
            operations = tuple(
                {
                    "name": name,
                    "description": description,
                    "input_schema": _ghidra_schema(
                        name, allow_segmented=target is not None and target.format.lower() == "mz",
                        preview=provider.backend == "attested-ghidra-command-v1",
                    ),
                    "mutates_analysis_database": False,
                }
                for name, description in (
                    _NATIVE_GHIDRA_OPERATIONS if target is not None else _GHIDRA_OPERATIONS
                ).items()
                if filter.lower() in f"{name} {description}".lower()
            )
            return {
                "analysis_provider": provider.public_dict(),
                "attestation_state": "not-probed",
                **({"target": to_primitive(target)} if target is not None else {}),
                **_page(operations, limit, offset),
            }
        async with _analysis_slot(provider.id, provider.repository_id, provider.timeout_seconds):
            target = await self._target(provider)
            if provider.backend == "attested-ida-stdio-v1":
                async with self._native_ida_session(provider) as session:
                    attestation, _ = await self._attest_native_ida(
                        provider, target, session
                    )
                    tools = await self._native_ida_tool_inventory(session, filter)
            else:
                metadata = await self._upstream(
                    provider,
                    "ida_call",
                    {"tool": "get_metadata", "arguments_json": "{}"},
                )
                attestation = _validate_ida_metadata(metadata["structured"], target)
                tools = await self._legacy_ida_tool_inventory(provider, filter)
        return {
            "analysis_provider": provider.public_dict(),
            "target": to_primitive(target),
            "attestation": attestation,
            **_page(tools, limit, offset),
        }

    async def call(
        self, provider_id: str, operation: str, arguments_json: str
    ) -> dict[str, Any]:
        provider = self.config.analysis_provider(provider_id)
        arguments = _arguments(arguments_json)
        async with _analysis_slot(provider.id, provider.repository_id, provider.timeout_seconds):
            target = await self._target(provider)
            if provider.backend == "attested-ghidra-command-v1":
                if operation not in _NATIVE_GHIDRA_OPERATIONS:
                    raise AnalysisError("unsupported Ghidra read-only operation")
                query_arguments = dict(arguments)
                preview_chars = query_arguments.pop("max_output_chars", _GHIDRA_PREVIEW_CHARS)
                _bounded_integer(preview_chars, "max_output_chars", 1, _GHIDRA_PREVIEW_MAX)
                forwarded = _validate_ghidra_arguments(
                    operation, query_arguments, allow_segmented=target.format.lower() == "mz"
                )
                attestation, output = await self._native_ghidra_call(
                    provider, target, operation, forwarded, max_output_chars=preview_chars
                )
            elif provider.backend == "attested-ida-stdio-v1":
                if operation not in _IDA_NATIVE_ALLOWED:
                    raise AnalysisError(
                        "IDA operation is not in the factory native allowlist"
                    )
                ida_arguments = dict(arguments)
                preview_chars = ida_arguments.pop("max_output_chars", _GHIDRA_PREVIEW_CHARS)
                _bounded_integer(preview_chars, "max_output_chars", 1, _GHIDRA_PREVIEW_MAX)
                _validate_ida_arguments(operation, ida_arguments)
                repository = self.config.repository(provider.repository_id).path
                async with self._native_ida_session(provider) as session:
                    attestation, metadata = await self._attest_native_ida(
                        provider, target, session
                    )
                    output = (
                        _native_ida_output(metadata["text"], metadata["structured"], self.config,
                                           repository, preview_chars)
                        if operation == "get_metadata"
                        else await self._native_ida_call(session, operation, ida_arguments,
                                                        repository=repository, max_output_chars=preview_chars)
                    )
            elif provider.backend == "attested-ida-proxy-v1":
                if operation not in _IDA_READ_ALLOWED:
                    raise AnalysisError(
                        "IDA operation is not in the factory read-only allowlist"
                    )
                _validate_ida_arguments(operation, arguments)
                metadata = await self._upstream(
                    provider,
                    "ida_call",
                    {"tool": "get_metadata", "arguments_json": "{}"},
                )
                attestation = _validate_ida_metadata(metadata["structured"], target)
                if operation == "get_metadata":
                    output = metadata
                else:
                    output = await self._upstream(
                        provider,
                        "ida_call",
                        {
                            "tool": operation,
                            "arguments_json": json.dumps(
                                arguments, separators=(",", ":"), sort_keys=True
                            ),
                        },
                    )
            else:
                if operation not in _GHIDRA_OPERATIONS:
                    raise AnalysisError("unsupported Ghidra read-only operation")
                forwarded = _validate_ghidra_arguments(operation, arguments)
                output = await self._upstream(
                    provider, "ghidra_call", {"operation": operation, **forwarded}
                )
                attestation = {
                    "status": "passed-by-registered-bridge",
                    "target_identity_id": target.id,
                    "expected_sha256": target.sha256,
                    "expected_size": target.size,
                }
        return {
            "analysis_provider": provider.public_dict(),
            "provider_binding_sha256": canonical_sha256(provider.identity_dict()),
            "target": to_primitive(target),
            "attestation": attestation,
            "operation": operation,
            "arguments_sha256": canonical_sha256(arguments),
            "observed_at": _now(),
            "authority": "provisional-semantic-analysis",
            "exactness_credit": "none",
            "output_completeness": (
                "factory-bounded-native-ghidra"
                if provider.backend == "attested-ghidra-command-v1"
                else "upstream-not-attested"
            ),
            "output": output,
        }

    async def _target(self, provider: AnalysisProviderRegistration) -> TargetIdentity:
        registration = self.config.repository(provider.repository_id)

        def load() -> TargetIdentity:
            try:
                with repository_lock(registration.path, exclusive=False):
                    single = registration.path / "config/target.toml"
                    if single.is_file():
                        manifest = tomllib.loads(single.read_text())
                        data = manifest["target"]
                        game = Path(data["filename"]).stem
                        product = f"{game}-main"
                        return TargetIdentity(
                            id=f"target:{product}", project_id=registration.id,
                            product_id=product, game=game, version=data.get("version", "unknown"),
                            region=data.get("region", "unknown"), format="pe",
                            size=data["size"], sha256=data["sha256"], md5=data.get("md5"),
                            canonicality="manifest-declared", metadata=manifest.get("pe", {}),
                        )
                    manifest = tomllib.loads((registration.path / "config/targets.toml").read_text())
                    data = next(item for item in manifest["artifacts"]
                                if f"target:{item['id']}" == provider.target_identity_id)
                    return TargetIdentity(
                        id=provider.target_identity_id, project_id=registration.id,
                        product_id=data["id"], game=data["game"], version="unknown",
                        region="unknown", format=data["format"], size=data["size"],
                        sha256=data["sha256"], md5=data.get("md5"),
                        canonicality="manifest-declared",
                    )
            except ReplayError as error:
                raise AnalysisError(
                    f"repository {provider.repository_id} cannot currently be read for "
                    f"provider {provider.id}; a repository writer or replay may be active. "
                    "Retry after that operation finishes; no other repository is blocked"
                ) from error

        return await anyio.to_thread.run_sync(load)

    async def _legacy_ida_tool_inventory(
        self, provider: AnalysisProviderRegistration, filter: str
    ) -> tuple[dict[str, Any], ...]:
        tools = []
        offset = 0
        observed_attestation = False
        while offset < 200:
            result = await self._upstream(
                provider,
                "ida_call",
                {
                    "tool": "list_tools",
                    "arguments_json": json.dumps(
                        {"filter": filter, "offset": offset, "limit": 20},
                        separators=(",", ":"),
                    ),
                },
            )
            document = result["structured"]
            if not isinstance(document, dict):
                try:
                    document = json.loads(result["text"])
                except json.JSONDecodeError as error:
                    raise AnalysisError(
                        "IDA provider returned a malformed operation inventory"
                    ) from error
            if document.get("idaAttested") is not True:
                raise AnalysisError("IDA provider did not attest its active target")
            observed_attestation = True
            page = document.get("tools")
            if not isinstance(page, list):
                raise AnalysisError("IDA operation inventory is missing its tools page")
            for tool in page:
                if (
                    not isinstance(tool, dict)
                    or tool.get("name") not in _IDA_READ_ALLOWED
                ):
                    continue
                tools.append(
                    {
                        "name": tool["name"],
                        "description": tool.get("description"),
                        "input_schema": _ida_input_schema(tool.get("inputSchema")),
                    }
                )
            if document.get("hasMore") is not True:
                break
            next_offset = document.get("offset", offset) + len(page)
            if next_offset <= offset:
                raise AnalysisError(
                    "IDA operation inventory pagination did not advance"
                )
            offset = next_offset
        if document.get("hasMore") is True:
            raise AnalysisError(
                "IDA operation inventory exceeds the factory discovery bound"
            )
        if not observed_attestation:
            raise AnalysisError("IDA operation inventory was empty")
        return tuple(tools)

    async def _native_ida_tool_inventory(
        self, session: ClientSession, filter: str
    ) -> tuple[dict[str, Any], ...]:
        try:
            result = await session.list_tools()
        except Exception as error:
            raise AnalysisError(
                f"native IDA tool discovery failed: {type(error).__name__}"
            ) from error
        tools = []
        query = filter.lower()
        for tool in result.tools:
            name = getattr(tool, "name", None)
            description = getattr(tool, "description", None)
            if name not in _IDA_NATIVE_ALLOWED:
                continue
            if query not in f"{name} {description or ''}".lower():
                continue
            tools.append(
                {
                    "name": name,
                    "description": description,
                    "input_schema": _ida_input_schema(_mcp_tool_input_schema(tool), preview=True),
                    "mutates_analysis_database": name
                    in _IDA_METADATA_WRITE_ALLOWED,
                }
            )
        return tuple(tools)

    @asynccontextmanager
    async def _native_ida_session(self, provider: AnalysisProviderRegistration):
        if provider.command is None or provider.target_path is None:
            raise AnalysisError("native IDA provider is missing private configuration")
        server = StdioServerParameters(
            command=str(provider.command),
            args=list(provider.arguments),
            cwd=str(self.config.repository(provider.repository_id).path),
        )
        diagnostics = tempfile.TemporaryFile()

        def connection_error(reason: str) -> AnalysisError:
            diagnostics.seek(0, os.SEEK_END)
            diagnostics.seek(max(0, diagnostics.tell() - 4096))
            detail = _redact(diagnostics.read().decode("utf-8", "replace"), self.config).strip()
            return AnalysisError(
                f"native IDA provider {provider.id} in repository {provider.repository_id} "
                f"could not complete its headless session ({reason}); verify its "
                "registered command/database and retry. Other games remain available"
                + (f". Provider diagnostic: {detail}" if detail else "")
            )
        try:
            with anyio.fail_after(provider.timeout_seconds):
                async with stdio_client(server, errlog=diagnostics) as (read_stream, write_stream):
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        yield session
        except AnalysisError:
            raise
        except BaseExceptionGroup as error:
            analysis_error = _contained_exception(error, AnalysisError)
            if analysis_error is not None:
                raise analysis_error from error
            if _contained_exception(error, TimeoutError) is not None:
                raise connection_error(f"timeout after {provider.timeout_seconds}s") from error
            raise connection_error("connection failed: ExceptionGroup") from error
        except TimeoutError as error:
            raise connection_error(f"timeout after {provider.timeout_seconds}s") from error
        except Exception as error:
            raise connection_error(type(error).__name__) from error
        finally:
            diagnostics.close()

    async def _native_ida_call(
        self, session: ClientSession, tool: str, arguments: dict[str, Any], *,
        repository: Path | None = None, max_output_chars: int = _GHIDRA_PREVIEW_CHARS,
    ) -> dict[str, Any]:
        try:
            result = await session.call_tool(tool, arguments)
        except Exception as error:
            raise AnalysisError(
                f"native IDA operation failed: {type(error).__name__}"
            ) from error
        return _bounded_output(
            content=result.content,
            structured=getattr(
                result,
                "structured_content",
                getattr(result, "structuredContent", None),
            ),
            is_error=bool(
                getattr(result, "is_error", getattr(result, "isError", False))
            ),
            config=self.config,
            rejection="native IDA provider rejected the request",
            repository=repository,
            max_output_chars=max_output_chars,
        )

    async def _attest_native_ida(
        self,
        provider: AnalysisProviderRegistration,
        target: TargetIdentity,
        session: ClientSession,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        metadata = await self._native_ida_call(session, "get_metadata", {})
        attestation = _validate_ida_metadata(metadata["structured"], target)
        attestation.update({"provider_transport": "factory-native-stdio",
                            "verification": "database-metadata-only"})
        return attestation, metadata

    async def _native_ghidra_call(
        self,
        provider: AnalysisProviderRegistration,
        target: TargetIdentity,
        operation: str,
        arguments: dict[str, Any],
        *,
        max_output_chars: int = _GHIDRA_PREVIEW_CHARS,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if provider.command is None or provider.target_path is None:
            raise AnalysisError("native Ghidra provider is missing private configuration")
        repository = self.config.repository(provider.repository_id).path
        try:
            result_text, output_path = await anyio.to_thread.run_sync(
                partial(
                    _run_native_ghidra_command,
                    provider,
                    repository,
                    operation,
                    arguments,
                )
            )
        except subprocess.TimeoutExpired as error:
            detail = _redact(str(error.stderr or ""), self.config)
            raise AnalysisError("native Ghidra provider timed out" + (f": {detail}" if detail else "")) from error
        except subprocess.CalledProcessError as error:
            detail = _redact((error.stderr or "")[:2048], self.config)
            raise AnalysisError(
                "native Ghidra provider rejected the request"
                + (f": {detail}" if detail else "")
            ) from error
        except OSError as error:
            raise AnalysisError(
                f"native Ghidra provider failed to start: {type(error).__name__}"
            ) from error
        output = _bounded_text_output(result_text, self.config, max_output_chars=max_output_chars,
                                      operation=operation)
        if output_path is not None:
            output["artifact_path"] = str(output_path.relative_to(repository))
        return {
            "status": "not-checked",
            "target_identity_id": target.id,
            "verification": "repository-selected-exploratory-analysis",
        }, output

    async def _upstream(
        self,
        provider: AnalysisProviderRegistration,
        tool: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        if provider.endpoint is None:
            raise AnalysisError("loopback analysis provider is missing its endpoint")
        if tool != provider.upstream_tool:
            raise AnalysisError(
                "analysis request tried to cross the registered tool boundary"
            )
        try:
            with anyio.fail_after(provider.timeout_seconds):
                async with Client(provider.endpoint) as client:
                    result = await client.call_tool(tool, arguments)
        except TimeoutError as error:
            raise AnalysisError("analysis provider timed out") from error
        except Exception as error:
            raise AnalysisError(
                f"analysis provider connection failed: {type(error).__name__}"
            ) from error
        return _bounded_output(
            content=result.content,
            structured=result.structured_content,
            is_error=bool(result.is_error),
            config=self.config,
            rejection="registered analysis bridge rejected the request",
        )


def _run_native_ghidra_command(
    provider: AnalysisProviderRegistration,
    repository: Path,
    operation: str,
    arguments: dict[str, Any],
) -> tuple[str, Path | None]:
    """Run one query and retain its complete text for direct repository reads."""

    if provider.command is None:
        raise AnalysisError("native Ghidra provider has no command")
    scratch_root = repository / ".analysis" / "factory-native-ghidra"
    scratch_root.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix="call-", dir=scratch_root))
    retained = False
    try:
        command = [str(provider.command), *provider.arguments]
        output_path = temporary / "result.txt"
        if operation == "check":
            command.append("check")
        elif operation in {"decompile", "function_context"}:
            command.extend(
                [operation, str(output_path), *arguments["addresses"]]
            )
        else:
            query_arguments: list[str]
            if operation in {"function", "callers", "callees"}:
                query_arguments = list(arguments["addresses"])
            elif operation == "disassemble":
                query_arguments = [
                    str(arguments.get("instruction_count", 80)),
                    *arguments["addresses"],
                ]
            elif operation in {"xrefs_to", "xrefs_from"}:
                query_arguments = [
                    str(arguments.get("limit", 100)),
                    *arguments["addresses"],
                ]
            elif operation == "list_functions":
                query_arguments = [
                    str(arguments.get("offset", 0)),
                    str(arguments.get("limit", 50)),
                    str(arguments.get("query", "")),
                ]
            elif operation == "search_strings":
                query_arguments = [
                    str(arguments.get("limit", 50)),
                    str(arguments["query"]),
                ]
            else:
                raise AnalysisError("unsupported native Ghidra operation")
            command.extend(["query", str(output_path), operation, *query_arguments])
        with subprocess.Popen(
            command,
            cwd=repository,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
            start_new_session=True,
        ) as process:
            try:
                stdout, stderr = process.communicate(timeout=provider.timeout_seconds)
            except subprocess.TimeoutExpired as error:
                # The wrapper launches Java. Killing only the wrapper leaves
                # an orphan analyzer holding the project lock after timeout.
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.communicate()
                if any(temporary.iterdir()):
                    retained = True
                    error.stderr = f"Partial output retained at {temporary.relative_to(repository)}"
                raise
            completed = subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
        if completed.returncode != 0:
            diagnostic = temporary / "provider.log"
            diagnostic.write_text(completed.stdout + "\n" + completed.stderr, encoding="utf-8")
            retained = True
            errors = list(dict.fromkeys(
                line.strip() for line in diagnostic.read_text(encoding="utf-8").splitlines()
                if line.lstrip().startswith(("ERROR", "Caused by:"))
            ))
            detail = ("\n".join(errors[:4]) or completed.stderr.strip()
                      or f"Provider exited with status {completed.returncode}")[:1000]
            detail += f"\nDiagnostics retained at {diagnostic.relative_to(repository)}"
            if output_path.is_file():
                detail += f"\nPartial output retained at {output_path.relative_to(repository)}"
            raise subprocess.CalledProcessError(
                completed.returncode,
                command,
                stderr=detail,
            )
        if operation == "check":
            result_text = "Native Ghidra wrapper completed; no full attestation was run."
            return result_text, None
        else:
            try:
                result_text = output_path.read_text(encoding="utf-8")
            except OSError as error:
                raise AnalysisError(
                    "native Ghidra operation produced no readable output"
                ) from error
        retained = True
        return result_text, output_path
    finally:
        if not retained:
            shutil.rmtree(temporary, ignore_errors=True)






def _bounded_text_output(
    text: str, config: ServiceConfig, *, max_output_chars: int = _GHIDRA_PREVIEW_CHARS,
    operation: str = "",
) -> dict[str, Any]:
    redacted = _redact(text, config)
    observed_payload = redacted.encode("utf-8")
    returned = redacted[:max_output_chars]
    truncated = len(returned) < len(redacted)
    # Keep complete lines when possible; long single lines still respect the budget.
    if truncated and "\n" in returned:
        returned = returned[:returned.rfind("\n") + 1]
    payload = returned.encode("utf-8")
    lines = redacted.split("\n")
    if lines[-1] == "":
        lines.pop()
    structured_payload = b"null"
    output = {
        "text": returned,
        "structured": None,
        "factory_output_truncated": truncated,
        "factory_structured_output_omitted": False,
        "observed_text_bytes": len(observed_payload),
        "returned_bytes": len(payload),
        "returned_sha256": hashlib.sha256(payload).hexdigest(),
        "structured_bytes": len(structured_payload),
        "structured_sha256": hashlib.sha256(structured_payload).hexdigest(),
        "total_chars": len(redacted),
        "total_lines": len(lines),
        "returned_chars": len(returned),
        "next_line": returned.count("\n") + 1 if truncated else None,
        "preview_ends_mid_line": truncated and not returned.endswith("\n"),
    }
    if operation in {"decompile", "function_context"} and truncated:
        headers = []
        for line_number, line in enumerate(lines, 1):
            match = re.fullmatch(r"/\* (.+) at ([^ ]+) \*/", line.removesuffix("\r"))
            if match:
                name = match[1] if len(match[1]) <= 160 else match[1][:157] + "..."
                headers.append({"name": name, "address": match[2],
                                "start_line": line_number})
        for index, header in enumerate(headers):
            end = headers[index + 1]["start_line"] - 1 if index + 1 < len(headers) else len(lines)
            header["end_line"] = end
        output["functions"] = headers[:16]
    return output


def _bounded_output(
    *,
    content: Any,
    structured: Any,
    is_error: bool,
    config: ServiceConfig,
    rejection: str,
    repository: Path | None = None,
    max_output_chars: int = _GHIDRA_PREVIEW_CHARS,
) -> dict[str, Any]:
    """Normalize one upstream MCP result into the Factory's bounded envelope."""

    text_blocks = [
        item.text
        for item in content
        if getattr(item, "type", None) == "text"
        and isinstance(getattr(item, "text", None), str)
    ]
    text = "\n".join(text_blocks)
    if is_error:
        detail = _redact(text, config).encode("utf-8")[:4096]
        raise AnalysisError(rejection + ": " + detail.decode("utf-8", "ignore"))
    if repository is not None:
        return _native_ida_output(text, structured, config, repository, max_output_chars)
    redacted = _redact(text, config)
    observed_payload = redacted.encode("utf-8")
    payload = observed_payload[:_MAX_OUTPUT_BYTES]
    redacted = payload.decode("utf-8", "ignore")
    truncated = len(observed_payload) > len(payload)
    structured = _redact_value(structured, config)
    try:
        structured_payload = json.dumps(
            structured,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise AnalysisError(
            "analysis provider returned non-JSON structured output"
        ) from error
    structured_omitted = len(structured_payload) > _MAX_OUTPUT_BYTES - len(payload)
    if structured_omitted:
        structured = None
    return {
        "text": redacted,
        "structured": structured,
        "factory_output_truncated": truncated,
        "factory_structured_output_omitted": structured_omitted,
        "observed_text_bytes": len(observed_payload),
        "returned_bytes": len(payload),
        "returned_sha256": hashlib.sha256(payload).hexdigest(),
        "structured_bytes": len(structured_payload),
        "structured_sha256": hashlib.sha256(structured_payload).hexdigest(),
    }


def _native_ida_output(
    text: str, structured: Any, config: ServiceConfig, repository: Path, max_output_chars: int,
) -> dict[str, Any]:
    """Retain complete oversized IDA results before reducing the inline context."""
    text = _redact(text, config)
    structured = _redact_value(structured, config)
    try:
        structured_text = json.dumps(structured, ensure_ascii=False, allow_nan=False,
                                     separators=(",", ":"), sort_keys=True)
    except (TypeError, ValueError) as error:
        raise AnalysisError("analysis provider returned non-JSON structured output") from error
    payload = structured_text.encode("utf-8")
    output = _bounded_text_output(text, config, max_output_chars=max_output_chars)
    omitted = output["factory_output_truncated"] or len(structured_text) > max_output_chars
    output.update(structured=None if omitted else structured,
                  factory_structured_output_omitted=omitted,
                  structured_bytes=len(payload), structured_sha256=hashlib.sha256(payload).hexdigest())
    if output["factory_output_truncated"] or omitted:
        root = repository / ".analysis/factory-native-ida"
        root.mkdir(parents=True, exist_ok=True)
        directory = Path(tempfile.mkdtemp(prefix="call-", dir=root))
        (directory / "result.txt").write_text(text, encoding="utf-8")
        (directory / "result.json").write_bytes(payload)
        output["artifact_path"] = str((directory / "result.txt").relative_to(repository))
        output["structured_artifact_path"] = str((directory / "result.json").relative_to(repository))
    return output




def _tool_result(value: Any) -> Any:
    if isinstance(value, dict) and "result" in value:
        return value["result"]
    return value






def _contained_exception(
    error: BaseExceptionGroup, expected: type[BaseException]
) -> BaseException | None:
    for child in error.exceptions:
        if isinstance(child, expected):
            return child
        if isinstance(child, BaseExceptionGroup):
            nested = _contained_exception(child, expected)
            if nested is not None:
                return nested
    return None


class _analysis_slot:
    def __init__(self, provider_id: str, repository_id: str, timeout_seconds: float) -> None:
        self.provider_id = provider_id
        self.repository_id = repository_id
        self.wait_seconds = min(timeout_seconds, 60)

    async def __aenter__(self) -> None:
        deadline = time.monotonic() + self.wait_seconds
        while (
            self.provider_id in _ACTIVE_PROVIDERS
            or sum(repo == self.repository_id for repo in _ACTIVE_PROVIDERS.values())
            >= _MAX_ACTIVE_ANALYSES_PER_REPOSITORY
        ):
            if time.monotonic() >= deadline:
                raise AnalysisError(
                    f"analysis queue timed out after {self.wait_seconds:g}s for "
                    f"provider {self.provider_id} in repository {self.repository_id}; "
                    "retry the same request after its active analysis finishes. "
                    "Other repositories have independent analysis capacity"
                )
            await anyio.sleep(min(0.05, max(0, deadline - time.monotonic())))
        # There is no await between the check and reservation. Waiting requests
        # never consume another repository's capacity or overlap this provider.
        _ACTIVE_PROVIDERS[self.provider_id] = self.repository_id

    async def __aexit__(self, *_args: Any) -> None:
        _ACTIVE_PROVIDERS.pop(self.provider_id, None)


def _arguments(raw: str) -> dict[str, Any]:
    if (
        not isinstance(raw, str)
        or not raw
        or len(raw.encode("utf-8")) > _MAX_ARGUMENT_BYTES
    ):
        raise AnalysisError("arguments_json must contain 1 through 65536 UTF-8 bytes")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as error:
        raise AnalysisError("arguments_json must encode one JSON object") from error
    if not isinstance(value, dict):
        raise AnalysisError("arguments_json must encode one JSON object")
    _validate_json_value(value, depth=0)
    return value


def _validate_json_value(value: Any, *, depth: int) -> None:
    if depth > 6:
        raise AnalysisError("analysis arguments exceed maximum nesting depth")
    if value is None or isinstance(value, (str, int, float, bool)):
        if isinstance(value, str) and len(value.encode("utf-8")) > 4096:
            raise AnalysisError("analysis argument string exceeds 4096 UTF-8 bytes")
        if isinstance(value, float) and not math.isfinite(value):
            raise AnalysisError("analysis arguments require finite JSON numbers")
        return
    if isinstance(value, list):
        if len(value) > 100:
            raise AnalysisError("analysis argument array exceeds 100 items")
        for item in value:
            _validate_json_value(item, depth=depth + 1)
        return
    if isinstance(value, dict):
        if len(value) > 64:
            raise AnalysisError("analysis argument object exceeds 64 fields")
        for key, item in value.items():
            if not isinstance(key, str) or not key or len(key) > 128:
                raise AnalysisError("analysis argument contains an invalid field name")
            _validate_json_value(item, depth=depth + 1)
        return
    raise AnalysisError("analysis arguments contain a non-JSON value")


def _validate_ida_arguments(operation: str, arguments: dict[str, Any]) -> None:
    forbidden_fields = {
        "command",
        "script",
        "path",
        "file",
        "filename",
        "python",
        "code",
    }
    if _contains_field(arguments, forbidden_fields):
        raise AnalysisError("analysis arguments contain a forbidden authority field")
    for key, value in arguments.items():
        if key in {"address", "start_address", "function_address", "memory_address"}:
            arguments[key] = _normalize_address(value, label=f"IDA {key}")
        if key == "offset":
            if operation == "create_stack_frame_variable":
                if not isinstance(value, str) or re.fullmatch(
                    r"-?(?:0x[0-9a-fA-F]{1,16}|[0-9]{1,20})", value
                ) is None:
                    raise AnalysisError("stack-frame offset must be a bounded integer string")
            else:
                _bounded_integer(value, key, 0, 1_000_000)
        elif key in {"count", "limit"}:
            _bounded_integer(value, key, 1, 200)
        elif key == "size":
            if operation == "convert_number" and value is None:
                continue
            _bounded_integer(value, key, 1, _MAX_IDA_MEMORY_BYTES if operation == "read_memory_bytes" else 256)
    if operation == "read_memory_bytes":
        if set(arguments) != {"memory_address", "size"}:
            raise AnalysisError(
                "read_memory_bytes requires only memory_address and size"
            )


def _mcp_tool_input_schema(tool: Any) -> Any:
    """Read an MCP tool schema across SDK field-name conventions."""
    schema = getattr(tool, "input_schema", None)
    if schema is not None:
        return schema
    return getattr(tool, "inputSchema", None)


def _ida_input_schema(schema: Any, *, preview: bool = False) -> Any:
    """Advertise Factory address normalization without changing upstream tools."""
    if not isinstance(schema, dict):
        return schema
    result = json.loads(json.dumps(schema))
    if preview:
        result.setdefault("properties", {})["max_output_chars"] = {
            "type": "integer", "minimum": 1, "maximum": _GHIDRA_PREVIEW_MAX,
            "default": _GHIDRA_PREVIEW_CHARS,
            "description": "Text preview budget. Oversized text/JSON is retained for repository Bash reads.",
        }
        if "memory_address" in result["properties"] and "size" in result["properties"]:
            result["properties"]["size"].update(minimum=1, maximum=_MAX_IDA_MEMORY_BYTES)
    for key, value in result.get("properties", {}).items():
        if key not in {"address", "start_address", "function_address", "memory_address"}:
            continue
        result["properties"][key] = {
            "anyOf": [
                {"type": "string", "minLength": 1, "maxLength": 64},
                {"type": "integer", "minimum": 0, "maximum": 0xFFFFFFFFFFFFFFFF},
            ],
            "description": (value.get("description", "") + " Hex (0x, A-F, or zero-padded 8/16 digits), decimal string, or unsigned integer; whitespace is trimmed.").strip(),
            **{field: item for field, item in value.items() if field in {"title", "default"}},
        }
    return result


def _normalize_address(value: Any, *, label: str, allow_segmented: bool = False) -> str:
    if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 0xFFFFFFFFFFFFFFFF:
        return f"0x{value:x}"
    if isinstance(value, str):
        value = value.strip()
        if value.startswith("0X"):
            value = "0x" + value[2:]
        elif re.fullmatch(r"[0-9a-fA-F]{1,16}", value) and (
            re.search(r"[a-fA-F]", value)
            or (len(value) in (8, 16) and value.startswith("0"))
        ):
            value = f"0x{int(value, 16):x}"
        elif value.isascii() and value.isdecimal() and len(value) <= 20:
            number = int(value, 10)
            if number <= 0xFFFFFFFFFFFFFFFF:
                value = f"0x{number:x}"
        if _ADDRESS.fullmatch(value) or (allow_segmented and _SEGMENTED_ADDRESS.fullmatch(value)):
            return value
    raise AnalysisError(
        f"{label} is invalid; use address or addresses with a hex string (0x, A-F, or zero-padded 8/16 digits), "
        "decimal string, or unsigned integer up to 64 bits"
        + (", or 16-bit segment:offset strings for MZ targets" if allow_segmented else "")
    )


def _contains_field(value: Any, names: set[str]) -> bool:
    if isinstance(value, dict):
        return any(
            key in names or _contains_field(item, names) for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_field(item, names) for item in value)
    return False


def _validate_ghidra_arguments(
    operation: str, arguments: dict[str, Any], *, allow_segmented: bool = False
) -> dict[str, Any]:
    allowed_by_operation = {
        "check": set(),
        "decompile": {"addresses"},
        "function_context": {"addresses"},
        "function": {"addresses"},
        "disassemble": {"addresses", "instruction_count"},
        "callers": {"addresses"},
        "callees": {"addresses"},
        "xrefs_to": {"addresses", "limit"},
        "xrefs_from": {"addresses", "limit"},
        "list_functions": {"query", "offset", "limit"},
        "search_strings": {"query", "limit"},
    }
    allowed = allowed_by_operation.get(operation)
    if allowed is None:
        raise AnalysisError("unsupported Ghidra read-only operation")
    result = dict(arguments)
    # Web callers often have a single displayed address rather than a list.
    if "address" in result and "addresses" in allowed and "addresses" not in result:
        result["addresses"] = [result.pop("address")]
    if set(result) - allowed:
        raise AnalysisError(
            "Ghidra arguments contain unsupported fields; "
            f"{operation} accepts: {', '.join(sorted(allowed)) or 'no arguments'}"
        )
    addresses = result.get("addresses", [])
    address_operations = {
        "decompile",
        "function_context",
        "function",
        "disassemble",
        "callers",
        "callees",
        "xrefs_to",
        "xrefs_from",
    }
    if operation in address_operations:
        if isinstance(addresses, (str, int)) and not isinstance(addresses, bool):
            addresses = [addresses]
        if isinstance(addresses, list):
            addresses = [_normalize_address(address, label="Ghidra address", allow_segmented=allow_segmented)
                         for address in addresses]
        if (
            not isinstance(addresses, list)
            or not 1 <= len(addresses) <= 16
            or any(
                not isinstance(item, str) or not (
                    _ADDRESS.fullmatch(item)
                    or (allow_segmented and _SEGMENTED_ADDRESS.fullmatch(item))
                )
                for item in addresses
            )
        ):
            raise AnalysisError(
                "Ghidra address operation requires 1 through 16 addresses; "
                "use address or addresses, with hex strings or integers"
                + (", or 16-bit segment:offset strings for MZ targets" if allow_segmented else "")
            )
        result["addresses"] = addresses
    elif addresses:
        raise AnalysisError("Ghidra operation does not accept addresses")
    if "query" in result and (
        not isinstance(result["query"], str)
        or len(result["query"].encode("utf-8")) > 1000
        or "\0" in result["query"]
    ):
        raise AnalysisError("Ghidra query exceeds its bounded text contract")
    if operation == "search_strings" and not result.get("query"):
        raise AnalysisError("search_strings requires a non-empty query")
    if "offset" in result:
        _bounded_integer(result["offset"], "offset", 0, 1_000_000)
    if "limit" in result:
        _bounded_integer(result["limit"], "limit", 1, 500)
    if "instruction_count" in result:
        _bounded_integer(result["instruction_count"], "instruction_count", 1, 500)
    return result


def _validate_ida_metadata(value: Any, target: TargetIdentity) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AnalysisError("IDA metadata is not structured")
    try:
        size = _number(value.get("filesize"))
    except (TypeError, ValueError) as error:
        raise AnalysisError("IDA metadata contains an invalid file size") from error
    sha256 = str(value.get("sha256", "")).lower()
    md5 = str(value.get("md5", "")).lower()
    if sha256 != target.sha256 or size != target.size:
        raise AnalysisError(
            "IDA metadata does not match the registered target identity"
        )
    if target.md5 is not None and md5 != target.md5:
        raise AnalysisError(
            "IDA metadata MD5 does not match the registered target identity"
        )
    return {
        "status": "passed",
        "target_identity_id": target.id,
        "observed_sha256": sha256,
        "observed_md5": md5 or None,
        "observed_size": size,
        "module": value.get("module"),
    }


def _number(value: Any) -> int:
    if isinstance(value, bool):
        raise TypeError("Boolean is not numeric")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value, 0)
    raise TypeError("value is not numeric")


def _bounded_integer(value: Any, name: str, minimum: int, maximum: int) -> None:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or not minimum <= value <= maximum
    ):
        raise AnalysisError(
            f"{name} must be an integer from {minimum} through {maximum}"
        )


def _ghidra_schema(
    operation: str, *, allow_segmented: bool = False, preview: bool = False,
) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    if preview:
        properties["max_output_chars"] = {
            "type": "integer", "minimum": 1, "maximum": _GHIDRA_PREVIEW_MAX,
            "default": _GHIDRA_PREVIEW_CHARS,
            "description": "Text preview budget. Read artifact_path with repository Bash for complete output.",
        }
    required: list[str] = []
    if operation in {
        "decompile",
        "function_context",
        "function",
        "disassemble",
        "callers",
        "callees",
        "xrefs_to",
        "xrefs_from",
    }:
        formats = r"0[xX][0-9a-fA-F]{1,16}|[0-9a-fA-F]{1,16}|[0-9]{1,20}"
        if allow_segmented:
            formats += r"|[0-9a-fA-F]{1,4}:[0-9a-fA-F]{1,4}"
        address = {"description": "Hex with 0x, A-F, or zero-padded 8/16 digits; other numeric strings are decimal. Integers are unsigned.", "anyOf": [
            {"type": "string", "pattern": r"^\s*(?:" + formats + r")\s*$"},
            {"type": "integer", "minimum": 0, "maximum": 0xFFFFFFFFFFFFFFFF},
        ]}
        properties["address"] = address
        properties["addresses"] = {"anyOf": [address, {
            "type": "array", "minItems": 1, "maxItems": 16, "items": address,
        }]}
    if operation in {"list_functions", "search_strings"}:
        properties["query"] = {"type": "string", "maxLength": 1000}
        if operation == "search_strings":
            required.append("query")
    if operation == "list_functions":
        properties["offset"] = {"type": "integer", "minimum": 0, "maximum": 1_000_000}
    if operation in {"xrefs_to", "xrefs_from", "list_functions", "search_strings"}:
        properties["limit"] = {"type": "integer", "minimum": 1, "maximum": 500}
    if operation == "disassemble":
        properties["instruction_count"] = {
            "type": "integer",
            "minimum": 1,
            "maximum": 500,
        }
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": required,
    }
    if "address" in properties:
        schema["oneOf"] = [{"required": ["address"]}, {"required": ["addresses"]}]
    return schema


def _page(
    values: tuple[dict[str, Any], ...], limit: int, offset: int
) -> dict[str, Any]:
    items = values[offset : offset + limit]
    return {
        "total": len(values),
        "offset": offset,
        "limit": limit,
        "next_offset": offset + len(items)
        if offset + len(items) < len(values)
        else None,
        "items": list(items),
    }


def _page_bounds(limit: int, offset: int) -> None:
    _bounded_integer(limit, "limit", 1, 100)
    _bounded_integer(offset, "offset", 0, 1_000_000)


def _redact(value: str, config: ServiceConfig) -> str:
    replacements = {
        str(config.path),
        str(config.path.parent),
        str(config.state_directory),
        str(config.evidence_store),
        str(config.policy_path),
        str(Path.home()),
        *(str(item.path) for item in config.repositories),
    }
    for provider in config.analysis_providers:
        if provider.endpoint is not None:
            parsed = urlsplit(provider.endpoint)
            replacements.update({provider.endpoint, parsed.netloc, parsed.path})
        if provider.command is not None:
            replacements.add(str(provider.command))
        if provider.target_path is not None:
            replacements.add(str(provider.target_path))
        replacements.update(provider.arguments)
    result = value
    for path in sorted(replacements, key=len, reverse=True):
        result = result.replace(path, "<analysis-host-path>")
    result = re.sub(
        r"(?i)\b[A-Z]:\\(?:[^\r\n\"']+\\)*[^\r\n\"']+",
        "<analysis-host-path>",
        result,
    )
    return result


def _redact_value(value: Any, config: ServiceConfig) -> Any:
    if isinstance(value, str):
        return _redact(value, config)
    if isinstance(value, list):
        return [_redact_value(item, config) for item in value]
    if isinstance(value, dict):
        return {
            _redact(key, config): _redact_value(item, config)
            for key, item in value.items()
        }
    return value


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
