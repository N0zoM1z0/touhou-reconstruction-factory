#!/usr/bin/env python3
"""Render a minimal Factory-native Ghidra provider registration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]


def quoted(value: str | Path) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--repository", required=True, type=Path)
    result.add_argument("--repository-id", required=True)
    result.add_argument("--provider-id", required=True)
    result.add_argument("--target-identity-id", required=True)
    result.add_argument("--target-path", required=True, type=Path)
    result.add_argument(
        "--command",
        type=Path,
        default=Path(sys.executable),
        help="absolute Python command used to launch scripts/ghidra.py",
    )
    result.add_argument("--timeout-seconds", type=int, default=900)
    result.add_argument("--standalone-project", action="store_true")
    return result


def main() -> int:
    arguments = parser().parse_args()
    try:
        repository = arguments.repository.expanduser().resolve(strict=True)
        command = arguments.command.expanduser().resolve(strict=True)
        target = arguments.target_path.expanduser().resolve(strict=True)
        if not command.is_file() or not target.is_file():
            raise ValueError("command and target path must be regular files")
        if not 1 <= arguments.timeout_seconds <= 3600:
            raise ValueError("timeout-seconds must be from 1 through 3600")
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print("[[analysis_providers]]")
    print(f"id = {quoted(arguments.provider_id)}")
    print(f"repository_id = {quoted(arguments.repository_id)}")
    print(f"target_identity_id = {quoted(arguments.target_identity_id)}")
    print('backend = "attested-ghidra-command-v1"')
    print(f"command = {quoted(command)}")
    provider_args = [str(ROOT / "scripts/ghidra-repository-provider.py"), "--repository", str(repository)]
    if arguments.standalone_project:
        provider_args.append("--standalone-project")
    print("arguments = [" + ", ".join(quoted(value) for value in provider_args) + "]")
    print(f"target_path = {quoted(target)}")
    print(f"timeout_seconds = {arguments.timeout_seconds}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
