#!/usr/bin/env python3
"""Shared tool installations with repository-owned mutable runtime state."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import tempfile


FACTORY = Path(__file__).resolve().parents[1]
TOOLS = FACTORY / ".factory/shared-tools"
SPEC = ".tools/shared-runtimes.json"


def configuration(repository: Path) -> tuple[Path, dict]:
    repository = repository.expanduser().resolve(strict=True)
    data = json.loads((repository / SPEC).read_text())
    if data.get("schema_version") != 1:
        raise ValueError("unsupported shared runtime configuration")
    if not data.get("owner_token"):
        raise ValueError("missing repository runtime owner token; provision shared tools first")
    return repository, data


def installation(name: str) -> Path:
    # Names select one provisioned distribution, never an arbitrary host path.
    if not name or Path(name).name != name or name in {".", ".."}:
        raise ValueError("invalid shared installation name")
    path = TOOLS / name
    if not path.is_dir():
        raise ValueError(f"shared installation {name!r} is missing; provision Factory tools first")
    return path.resolve()


def wine_prefix(repository: Path, spec: dict, override: Path | None = None) -> Path:
    selected = (repository / spec["wine_prefix"]).resolve()
    prefix = (repository / override).resolve() if override is not None else selected
    # Explicit local probe prefixes are useful. An outside legacy prefix must
    # be the one deliberately attached to this repository by the operator.
    if prefix != selected and not prefix.is_relative_to(repository):
        raise ValueError("Wine prefix belongs outside this repository; use its configured prefix")
    if prefix == repository or (prefix.exists() and not prefix.is_dir()):
        raise ValueError("Wine prefix must be a separate directory")
    marker = prefix / ".factory-runtime-owner.json"
    if marker.exists():
        owner = json.loads(marker.read_text())
        if owner.get("owner_token") != spec["owner_token"]:
            raise ValueError("Wine prefix is owned by another repository")
    return prefix


def prepare(repository: Path, tool: str, prefix: Path | None = None, *, describe: bool = False,
            ghidra_version: str | None = None):
    repository, spec = configuration(repository)
    environment = dict(os.environ)
    state = repository / ".analysis/factory-runtime"
    metadata = {"repository_id": spec["repository_id"], "repository": str(repository), "tool": tool}
    if tool in {"ghidra", "java"}:
        ghidra = installation(ghidra_version or spec["ghidra"])
        jdk = installation(spec["jdk"])
        home, temporary = state / "ghidra/home", state / "ghidra/tmp"
        environment.update(
            GHIDRA_HOME=str(ghidra), JAVA_HOME=str(jdk),
            PATH=str(jdk / "bin") + os.pathsep + environment.get("PATH", os.defpath),
            DISPLAY="", WAYLAND_DISPLAY="", TMPDIR=str(temporary),
            XDG_CONFIG_HOME=str(state / "ghidra/config"),
            XDG_CACHE_HOME=str(state / "ghidra/cache"),
            XDG_DATA_HOME=str(state / "ghidra/data"),
        )
        options = [f"-Duser.home={home}", f"-Djava.io.tmpdir={temporary}", "-Djava.awt.headless=true"]
        environment["JAVA_TOOL_OPTIONS"] = " ".join(
            [environment.get("JAVA_TOOL_OPTIONS", ""), *(shlex.quote(value) for value in options)]
        ).strip()
        environment.setdefault("GHIDRA_HEADLESS_MAXMEM", "768M")
        for variable in ("GHIDRA_JAVA_OPTIONS", "GHIDRA_HEADLESS_JAVA_OPTIONS"):
            if variable in environment:
                environment[variable] = shlex.join(value for value in shlex.split(environment[variable])
                    if not value.startswith(("-Duser.home=", "-Djava.io.tmpdir=")))
        executable = ghidra / "support/analyzeHeadless" if tool == "ghidra" else jdk / "bin/java"
        metadata.update(ghidra=str(ghidra), jdk=str(jdk), user_home=str(home),
                        temporary=str(temporary), cache=str(state / "ghidra/cache"))
        if not describe:
            for directory in [home, temporary, *(Path(environment[key]) for key in
                              ("XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME"))]:
                directory.mkdir(parents=True, exist_ok=True)
    else:
        prefix = wine_prefix(repository, spec, prefix)
        executable = installation("wine") / "bin" / tool
        environment.update(WINEPREFIX=str(prefix), WINEARCH=spec.get("wine_arch", "win32"))
        environment.setdefault("WINEDEBUG", "-all")
        # Wine's Unix socket paths must use /tmp, not a long caller TMPDIR.
        environment.pop("TMPDIR", None)
        environment.pop("WINELOADER", None)
        environment.pop("WINESERVER", None)
        shim_bin = repository / ".tools/factory-bin"
        environment["PATH"] = os.pathsep.join(value for value in environment.get("PATH", os.defpath).split(os.pathsep)
                                               if Path(value or ".").resolve() != shim_bin)
        overrides = environment.get("WINEDLLOVERRIDES", "")
        if "winemenubuilder.exe=" not in overrides:
            environment["WINEDLLOVERRIDES"] = "winemenubuilder.exe=d;" + overrides
        metadata.update(prefix=str(prefix), arch=environment["WINEARCH"])
        if not describe:
            prefix.mkdir(parents=True, exist_ok=True)
            marker = prefix / ".factory-runtime-owner.json"
            owner = {"owner_token": spec["owner_token"], "repository_id": spec["repository_id"]}
            if not marker.exists():
                # Publish a complete marker atomically. Concurrent first use
                # must not observe an empty, partially written JSON file.
                with tempfile.NamedTemporaryFile(mode="w", dir=prefix, prefix=".factory-owner-",
                                                  delete=False) as stream:
                    stream.write(json.dumps(owner))
                try:
                    try:
                        os.link(stream.name, marker)
                    except FileExistsError:
                        if json.loads(marker.read_text()).get("owner_token") != spec["owner_token"]:
                            raise ValueError("Wine prefix is owned by another repository")
                finally:
                    Path(stream.name).unlink(missing_ok=True)
    if not executable.is_file():
        raise ValueError(f"shared {tool} executable is missing")
    metadata["executable"] = str(executable)
    return executable, environment, metadata


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--prefix", type=Path, help="explicit repository-local Wine probe prefix")
    parser.add_argument("--describe", action="store_true", help="inspect selection without starting a tool")
    parser.add_argument("--ghidra", help="explicit installed Ghidra distribution name")
    parser.add_argument("tool", choices=("ghidra", "java", "wine", "winepath", "wineserver"))
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    try:
        executable, environment, metadata = prepare(args.repository, args.tool, args.prefix,
            describe=args.describe, ghidra_version=args.ghidra)
        if args.describe:
            print(json.dumps(metadata, indent=2))
            return 0
        arguments = args.arguments[1:] if args.arguments[:1] == ["--"] else args.arguments
        os.setpriority(os.PRIO_PROCESS, 0, max(10, os.getpriority(os.PRIO_PROCESS, 0)))
        if hasattr(os, "sched_setaffinity"):
            os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
        command = [str(executable), *arguments]
        if args.tool in {"ghidra", "java", "wineserver"}:
            # Recovery commands such as wineserver -k must not queue behind
            # the Wine process they are meant to stop. Prefix checks still run.
            os.execvpe(command[0], command, environment)
        # Keep the lock in this short-lived parent, not in the persistent
        # wineserver. A child must never inherit the lock descriptor.
        lock_path = Path(metadata["repository"]) / ".analysis/factory-runtime/wine.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a") as gate:
            fcntl.flock(gate, fcntl.LOCK_EX)
            child = subprocess.Popen(command, env=environment, close_fds=True)
            for sig in (signal.SIGINT, signal.SIGTERM):
                signal.signal(sig, lambda signum, frame: child.send_signal(signum) if child.poll() is None else None)
            status = child.wait()
            return status if status >= 0 else 128 - status
    except (OSError, ValueError, KeyError) as error:
        print(f"shared runtime: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
