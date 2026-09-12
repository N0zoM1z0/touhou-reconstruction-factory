#!/usr/bin/env python3
"""Validate one staged Factory-native analysis provider without server restart."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import anyio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from reconstruction_factory.analysis_mcp import AnalysisGateway  # noqa: E402
from reconstruction_factory.errors import FactoryError  # noqa: E402
from reconstruction_factory.service_config import load_service_config  # noqa: E402


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--config", required=True, type=Path)
    result.add_argument("--provider", required=True)
    result.add_argument(
        "--operation",
        help="Optional discovered operation to call after discovery",
    )
    result.add_argument(
        "--arguments-json",
        default="{}",
        help="JSON object for --operation (default: {})",
    )
    return result


async def validate(arguments: argparse.Namespace) -> dict[str, Any]:
    config = load_service_config(arguments.config)
    provider = config.analysis_provider(arguments.provider)
    if provider.backend not in {
        "attested-ghidra-command-v1",
        "attested-ida-stdio-v1",
    }:
        raise ValueError("selected provider is not Factory-native")
    gateway = AnalysisGateway(config)
    discovery = await gateway.list_operations(
        provider.id,
        filter="",
        limit=100,
        offset=0,
    )
    result: dict[str, Any] = {
        "status": "passed",
        "provider": provider.public_dict(),
        "attestation": discovery["attestation"],
        "operation_count": discovery["total"],
        "operation_names": [item["name"] for item in discovery["items"]],
    }
    if arguments.operation:
        result["call"] = await gateway.call(
            provider.id,
            arguments.operation,
            arguments.arguments_json,
        )
    return result


def main() -> int:
    arguments = parser().parse_args()
    try:
        result = anyio.run(validate, arguments)
    except (FactoryError, OSError, TypeError, ValueError) as error:
        print(
            json.dumps(
                {"status": "failed", "error": f"{type(error).__name__}: {error}"},
                sort_keys=True,
            )
        )
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
