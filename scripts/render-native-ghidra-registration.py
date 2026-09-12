#!/usr/bin/env python3
"""Render a hash-bound Factory-native Ghidra provider registration."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from reconstruction_factory.oracle_receipts import canonical_sha256  # noqa: E402


IMPLEMENTATION_FILES = (
    "config/target.toml",
    "config/tools.lock.toml",
    "scripts/ghidra.py",
    "scripts/ghidra/DecompileFunctions.java",
    "scripts/ghidra/ExportArchitecture.java",
    "scripts/ghidra/ExportInventory.java",
    "scripts/ghidra/QueryProgram.java",
    "scripts/ghidra/VerifyTarget.java",
    "scripts/target_identity.py",
    "scripts/verify-analysis-tools.py",
    "scripts/verify-target.py",
)


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
        files = tuple(
            (repository / name).resolve(strict=True)
            for name in IMPLEMENTATION_FILES
        )
        if any(
            not path.is_file() or not path.is_relative_to(repository)
            for path in files
        ):
            raise ValueError("native Ghidra implementation file is invalid")
        files = tuple(sorted(files, key=str))
        file_hashes = tuple(
            hashlib.sha256(path.read_bytes()).hexdigest() for path in files
        )
        aggregate = canonical_sha256(file_hashes)
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print("[[analysis_providers]]")
    print(f"id = {quoted(arguments.provider_id)}")
    print(f"repository_id = {quoted(arguments.repository_id)}")
    print(f"target_identity_id = {quoted(arguments.target_identity_id)}")
    print('backend = "attested-ghidra-command-v1"')
    print(f"command = {quoted(command)}")
    print(f"arguments = [{quoted(repository / 'scripts' / 'ghidra.py')}]")
    print(f"target_path = {quoted(target)}")
    print("implementation_files = [")
    for path, digest in zip(files, file_hashes, strict=True):
        print(f"  {quoted(path)}, # sha256:{digest}")
    print("]")
    print(f"implementation_sha256 = {quoted(aggregate)}")
    print(f"timeout_seconds = {arguments.timeout_seconds}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
