#!/usr/bin/env python3
"""Run the portable, fail-closed Factory release validation suite."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
import xml.etree.ElementTree as ElementTree


ROOT = Path(__file__).resolve().parents[1]


def _run(label: str, command: list[str]) -> None:
    print(f"[RUN ] {label}", flush=True)
    result = subprocess.run(command, cwd=ROOT, check=False)
    if result.returncode != 0:
        raise SystemExit(f"[FAIL] {label}: exit {result.returncode}")
    print(f"[PASS] {label}", flush=True)


def _tracked_files() -> tuple[Path, ...]:
    output = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
    ).decode("utf-8")
    return tuple(ROOT / value for value in output.split("\0") if value)


def _validate_documents() -> None:
    print("[RUN ] tracked JSON, TOML, and evaluation XML parsing", flush=True)
    counts = {"json": 0, "toml": 0, "xml": 0}
    for path in _tracked_files():
        if path.suffix == ".json":
            with path.open("r", encoding="utf-8") as handle:
                json.load(handle)
            counts["json"] += 1
        elif path.suffix == ".toml":
            with path.open("rb") as handle:
                tomllib.load(handle)
            counts["toml"] += 1
        elif path.suffix == ".xml" and "evaluations" in path.parts:
            ElementTree.parse(path)
            counts["xml"] += 1
    if not all(counts.values()):
        raise SystemExit(f"[FAIL] expected all document classes, observed {counts}")
    print(f"[PASS] parsed tracked documents: {counts}", flush=True)


def _require_tool(name: str) -> str:
    executable = shutil.which(name)
    if executable is None:
        raise SystemExit(f"[FAIL] required validation tool is unavailable: {name}")
    return executable


def main() -> int:
    if importlib.util.find_spec("mcp") is None:
        raise SystemExit(
            "[FAIL] MCP dependency is unavailable; run with the service environment, "
            "for example .venv/bin/python scripts/validate-release.py"
        )

    _run("Ruff", [_require_tool("ruff"), "check", "."])
    _run(
        "unit and integration tests",
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-v",
        ],
    )
    _run(
        "bytecode compilation",
        [
            sys.executable,
            "-m",
            "compileall",
            "-q",
            "src",
            "tests",
            "scripts",
        ],
    )
    _run("Git whitespace validation", [_require_tool("git"), "diff", "--check"])
    _validate_documents()

    for module in (
        "reconstruction_factory",
        "reconstruction_factory.service_cli",
        "reconstruction_factory.mcp_server",
    ):
        _run(f"{module} CLI help", [sys.executable, "-m", module, "--help"])

    with tempfile.TemporaryDirectory(prefix="factory-wheel-") as directory:
        _run(
            "isolated wheel build",
            [
                sys.executable,
                "-m",
                "pip",
                "wheel",
                "--disable-pip-version-check",
                "--no-deps",
                "--wheel-dir",
                directory,
                ".",
            ],
        )
        wheels = tuple(Path(directory).glob("*.whl"))
        if len(wheels) != 1:
            raise SystemExit(f"[FAIL] expected one wheel, observed {len(wheels)}")

    print("[PASS] complete portable release validation", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
