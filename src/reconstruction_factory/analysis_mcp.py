"""Read-only, target-bound gateway to operator-registered analysis bridges."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlsplit

import anyio
from mcp import Client

from .adapters import inspect_repository
from .errors import AnalysisError
from .ontology import TargetIdentity, to_primitive
from .oracle_receipts import canonical_sha256
from .replay_identity import repository_lock
from .service_config import AnalysisProviderRegistration, ServiceConfig


_MAX_ARGUMENT_BYTES = 65536
_MAX_OUTPUT_BYTES = 262144
_MAX_ACTIVE_ANALYSES = 2
_ACTIVE_PROVIDERS: set[str] = set()

_IDA_ALLOWED = frozenset(
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
    }
)
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
_ADDRESS = re.compile(r"^0x[0-9a-fA-F]{1,16}$")


class AnalysisGateway:
    """A provisional semantic-analysis surface with no mutation operations."""

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
        if provider.backend == "attested-ghidra-proxy-v1":
            operations = tuple(
                {
                    "name": name,
                    "description": description,
                    "input_schema": _ghidra_schema(name),
                }
                for name, description in _GHIDRA_OPERATIONS.items()
                if filter.lower() in f"{name} {description}".lower()
            )
            return {
                "analysis_provider": provider.public_dict(),
                "attestation_state": "not-probed",
                **_page(operations, limit, offset),
            }
        async with _analysis_slot(provider.id):
            target = await self._target(provider)
            metadata = await self._upstream(
                provider,
                "ida_call",
                {"tool": "get_metadata", "arguments_json": "{}"},
            )
            attestation = _validate_ida_metadata(metadata["structured"], target)
            tools = await self._ida_tool_inventory(provider, filter)
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
        async with _analysis_slot(provider.id):
            target = await self._target(provider)
            if provider.backend == "attested-ida-proxy-v1":
                if operation not in _IDA_ALLOWED:
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
            "output_completeness": "upstream-not-attested",
            "output": output,
        }

    async def _target(self, provider: AnalysisProviderRegistration) -> TargetIdentity:
        registration = self.config.repository(provider.repository_id)

        def load() -> TargetIdentity:
            with repository_lock(registration.path, exclusive=False):
                snapshot = inspect_repository(registration.path)
            if snapshot.adapter_id != registration.adapter_id:
                raise AnalysisError("analysis repository adapter binding changed")
            targets = [
                item
                for item in snapshot.targets
                if item.id == provider.target_identity_id
            ]
            if len(targets) != 1:
                raise AnalysisError(
                    "analysis target does not resolve to exactly one adapter identity"
                )
            return targets[0]

        return await anyio.to_thread.run_sync(load)

    async def _ida_tool_inventory(
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
                if not isinstance(tool, dict) or tool.get("name") not in _IDA_ALLOWED:
                    continue
                tools.append(
                    {
                        "name": tool["name"],
                        "description": tool.get("description"),
                        "input_schema": tool.get("inputSchema"),
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

    async def _upstream(
        self,
        provider: AnalysisProviderRegistration,
        tool: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
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
        text_blocks = [
            item.text
            for item in result.content
            if getattr(item, "type", None) == "text"
            and isinstance(getattr(item, "text", None), str)
        ]
        text = "\n".join(text_blocks)
        if result.is_error:
            detail = _redact(text, self.config).encode("utf-8")[:4096]
            raise AnalysisError(
                "registered analysis bridge rejected the request: "
                + detail.decode("utf-8", "ignore")
            )
        redacted = _redact(text, self.config)
        observed_payload = redacted.encode("utf-8")
        payload = observed_payload[:_MAX_OUTPUT_BYTES]
        redacted = payload.decode("utf-8", "ignore")
        truncated = len(observed_payload) > len(payload)
        structured = _redact_value(result.structured_content, self.config)
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


class _analysis_slot:
    def __init__(self, provider_id: str) -> None:
        self.provider_id = provider_id

    async def __aenter__(self) -> None:
        if (
            self.provider_id in _ACTIVE_PROVIDERS
            or len(_ACTIVE_PROVIDERS) >= _MAX_ACTIVE_ANALYSES
        ):
            raise AnalysisError(
                "analysis capacity is busy; retry the same bounded request later"
            )
        _ACTIVE_PROVIDERS.add(self.provider_id)

    async def __aexit__(self, *_args: Any) -> None:
        _ACTIVE_PROVIDERS.discard(self.provider_id)


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
            if not isinstance(value, str) or not _ADDRESS.fullmatch(value):
                raise AnalysisError(f"{key} must be a bounded hexadecimal address")
        if key == "offset":
            _bounded_integer(value, key, 0, 1_000_000)
        elif key in {"count", "limit"}:
            _bounded_integer(value, key, 1, 200)
        elif key == "size":
            if operation == "convert_number" and value is None:
                continue
            _bounded_integer(value, key, 1, 256)
    if operation == "read_memory_bytes":
        if set(arguments) != {"memory_address", "size"}:
            raise AnalysisError(
                "read_memory_bytes requires only memory_address and size"
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
    operation: str, arguments: dict[str, Any]
) -> dict[str, Any]:
    allowed = {"addresses", "query", "offset", "limit", "instruction_count"}
    if set(arguments) - allowed:
        raise AnalysisError("Ghidra arguments contain unsupported fields")
    result = dict(arguments)
    addresses = result.get("addresses", [])
    address_operations = {
        "decompile",
        "function",
        "disassemble",
        "callers",
        "callees",
        "xrefs_to",
        "xrefs_from",
    }
    if operation in address_operations:
        if (
            not isinstance(addresses, list)
            or not 1 <= len(addresses) <= 16
            or any(
                not isinstance(item, str) or not _ADDRESS.fullmatch(item)
                for item in addresses
            )
        ):
            raise AnalysisError(
                "Ghidra address operation requires 1 through 16 addresses"
            )
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


def _ghidra_schema(operation: str) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    required: list[str] = []
    if operation in {
        "decompile",
        "function",
        "disassemble",
        "callers",
        "callees",
        "xrefs_to",
        "xrefs_from",
    }:
        properties["addresses"] = {
            "type": "array",
            "minItems": 1,
            "maxItems": 16,
            "items": {"type": "string", "pattern": "^0x[0-9a-fA-F]{1,16}$"},
        }
        required.append("addresses")
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
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": required,
    }


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
        parsed = urlsplit(provider.endpoint)
        replacements.update({provider.endpoint, parsed.netloc, parsed.path})
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
