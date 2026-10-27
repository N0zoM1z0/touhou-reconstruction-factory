#!/usr/bin/env python3
"""Bind existing headless repository wrappers to the native Factory protocol.

All paths and marker names are operator configuration, never public arguments.
PE markers retain every independently checked field. MZ queries use a single
read-only process for complete database attestation and the requested query.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import uuid


def translate_pe_marker(stdout: str, marker: str) -> str:
    pattern = re.compile(
        r"> " + re.escape(marker) + r"(?P<fields>:[0-9a-fA-F]{64}:[0-9a-fA-F]{32}:"
        r"[0-9]+:[0-9a-fA-F]{8}:[0-9]+:[0-9a-fA-F]{8}:[0-9]+)"
        r"(?: \(GhidraScript\))?\s*$", re.MULTILINE,
    )
    matches = list(pattern.finditer(stdout))
    if len(matches) != 1 or "ERROR REPORT SCRIPT ERROR" in stdout:
        raise ValueError("expected exactly one successful repository attestation marker")
    return "FACTORY_GHIDRA_ATTESTATION_V1" + matches[0]["fields"]


def pe_call(args: argparse.Namespace) -> None:
    interpreter = args.interpreter or Path(sys.executable)
    result = subprocess.run(
        [str(interpreter), str(args.repository / "scripts/ghidra.py"),
         args.operation, *args.arguments], cwd=args.repository,
        capture_output=True, text=True, errors="replace", check=False,
    )
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    if result.returncode:
        raise ValueError(f"repository Ghidra wrapper exited with {result.returncode}")
    print(translate_pe_marker(result.stdout, args.marker))


def mz_call(args: argparse.Namespace) -> None:
    # Repository code is a hash-pinned, operator-selected local dependency.
    sys.path.insert(0, str(args.repository / "scripts"))
    from ghidra import environment, project_name
    from lib.analysis import load_analysis_config, repository_path
    from lib.ghidra import attest_mz_export
    from lib.pc98 import parse_mz
    from lib.targets import find_artifact, load_target_manifest, read_verified_artifact

    root = args.repository
    config = load_analysis_config(root / "config/analysis_toolchain.toml")
    artifact = find_artifact(load_target_manifest(root / "config/targets.toml"), args.mz_artifact)
    target = read_verified_artifact(root, artifact)
    image = parse_mz(target)
    env = environment(config)
    subprocess.run([sys.executable, "scripts/attest_analysis_toolchain.py"],
                   cwd=root, env=env, check=True)
    query = []
    output = None
    if args.operation != "check":
        if len(args.arguments) < 2:
            raise ValueError("query/decompile requires output and query arguments")
        output = Path(args.arguments[0]).resolve()
        if not output.is_relative_to(root / ".analysis/factory-native-ghidra"):
            raise ValueError("output must be inside the private Factory scratch directory")
        output.unlink(missing_ok=True)
        values = args.arguments[1:]
        if args.operation == "query":
            index = {"list_functions": 3, "search_strings": 2}.get(values[0])
            if index is not None and len(values) > index:
                values[index] = "text:" + values[index]
        script = "DecompileFunctions.java" if args.operation == "decompile" else "QueryProgram.java"
        query = ["-postScript", script, str(output), *values]
    scratch = root / ".analysis/factory-native-ghidra"
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="attest-", dir=scratch) as temporary:
        nonce = uuid.uuid4().hex
        analyzer = repository_path(root, config["ghidra"]["stable_path"]) / "support/analyzeHeadless"
        command = [str(analyzer), str(root / "ghidra-project"), project_name(args.mz_artifact),
                   "-process", Path(artifact["private_path"]).name,
                   "-readOnly", "-noanalysis", "-max-cpu", "1",
                   "-postScript", "ExportMzAttestation.java", temporary, str(len(target)),
                   str(image.header.header_size), str(image.header.declared_file_size), nonce,
                   *query, "-scriptPath", str(root / "scripts/ghidra")]
        result = subprocess.run(command, cwd=root, env=env, capture_output=True,
                                text=True, errors="replace", check=False)
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        if result.returncode or "ERROR REPORT SCRIPT ERROR" in result.stdout + result.stderr:
            raise ValueError("headless MZ database query failed")
        report = attest_mz_export(Path(temporary), target, artifact, config, expected_nonce=nonce)
        if not report["ready"] or (output is not None and not output.is_file()):
            raise ValueError("same-process MZ database attestation or query failed")
        if read_verified_artifact(root, artifact) != target:
            raise ValueError("private target changed during analysis")
        print("FACTORY_GHIDRA_MZ_ATTESTATION_V1:"
              f"{hashlib.sha256(target).hexdigest()}:"
              f"{hashlib.md5(target, usedforsecurity=False).hexdigest()}:"
              f"{len(target)}:{image.header.header_size}:{len(image.program_image)}:"
              f"{image.header.initial_relative_cs:04x}:{image.header.initial_ip:04x}:"
              f"{len(image.relocations)}:{hashlib.sha256(image.program_image).hexdigest()}:"
              f"{report['target']['relocated_load_module_sha256']}:{len(report['samples'])}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--interpreter", type=Path)
    kind = parser.add_mutually_exclusive_group(required=True)
    kind.add_argument("--marker")
    kind.add_argument("--mz-artifact")
    parser.add_argument("operation", choices=("check", "query", "decompile"))
    parser.add_argument("arguments", nargs="*")
    args = parser.parse_args()
    args.repository = args.repository.resolve(strict=True)
    scratch = args.repository / ".analysis/factory-native-ghidra"
    scratch.mkdir(parents=True, exist_ok=True)
    # Coordinate Factory calls across stateless server instances.
    with (scratch / "provider.lock").open("a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if args.mz_artifact:
            mz_call(args)
        else:
            pe_call(args)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
