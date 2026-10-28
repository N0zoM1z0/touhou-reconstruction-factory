#!/usr/bin/env python3
"""Push registered game branches, inheriting the caller's Git/proxy environment."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
import tomllib


FACTORY_ROOT = Path(__file__).resolve().parents[1]


def running_config(proc_root: Path = Path("/proc"), checkout: Path = FACTORY_ROOT) -> Path:
    """Find this checkout's running MCP configuration, without a stored binding."""
    configs = set()
    for process in proc_root.glob("[0-9]*"):
        try:
            cwd = (process / "cwd").resolve(strict=True)
            if cwd != checkout:
                continue
            argv = os.fsdecode((process / "cmdline").read_bytes()).split("\0")
            if "reconstruction_factory.mcp_server" not in argv and not any(
                Path(arg).name == "touhou-reconstruction-factory-mcp" for arg in argv[:2]
            ):
                continue
            for index, arg in enumerate(argv):
                if arg == "--config":
                    configs.add((cwd / Path(argv[index + 1]).expanduser()).resolve())
                elif arg.startswith("--config="):
                    configs.add((cwd / Path(arg.split("=", 1)[1]).expanduser()).resolve())
        except (OSError, IndexError):
            continue
    if len(configs) != 1:
        raise ValueError(
            "Cannot identify one running Factory configuration for this checkout; "
            "pass --config or export FACTORY_SERVICE_CONFIG."
        )
    return configs.pop()


def registered_repositories(config: Path) -> list[tuple[str, Path]]:
    config = config.expanduser().resolve()
    with config.open("rb") as handle:
        rows = tomllib.load(handle).get("repositories")
    if not isinstance(rows, list) or not rows:
        raise ValueError("The configuration has no registered repositories.")
    repositories = []
    for row in rows:
        if not isinstance(row, dict) or not all(
            isinstance(row.get(key), str) and row[key] for key in ("id", "path")
        ):
            raise ValueError("Each repository needs an id and a path.")
        repositories.append((row["id"], (config.parent / Path(row["path"]).expanduser()).resolve()))
    return repositories


def git(repository: Path, *arguments: str, optional: bool = False) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments], capture_output=True, text=True
    )
    if result.returncode and not (optional and result.returncode == 1):
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(arguments)} failed")
    return result.stdout.strip()


def push(repository_id: str, repository: Path, *, dry_run: bool) -> bool:
    try:
        if Path(git(repository, "rev-parse", "--show-toplevel")).resolve() != repository:
            raise ValueError("The registered path is not a Git worktree root.")
        branch = git(repository, "symbolic-ref", "--quiet", "--short", "HEAD", optional=True)
        if not branch:
            raise ValueError("HEAD is detached; switch to a branch before pushing.")

        def setting(key: str) -> str:
            return git(repository, "config", "--get", key, optional=True)

        upstream_remote = setting(f"branch.{branch}.remote")
        remote = (setting(f"branch.{branch}.pushRemote") or setting("remote.pushDefault")
                  or upstream_remote or "origin")
        if remote == ".":
            raise ValueError("The branch tracks a local repository; configure a push remote.")
        target = setting(f"branch.{branch}.merge") if remote == upstream_remote else ""
        target = target or f"refs/heads/{branch}"
        if not target.startswith("refs/heads/"):
            raise ValueError("The configured upstream is not a branch.")
        print(f"\n[{repository_id}] {branch} -> {remote}/{target.removeprefix('refs/heads/')}", flush=True)
        command = ["git", "-C", str(repository), "push", "--no-follow-tags"]
        if dry_run:
            command.append("--dry-run")
        command += ["--", remote, f"refs/heads/{branch}:{target}"]
        if subprocess.run(command).returncode:
            raise RuntimeError("Push failed; resolve the Git error above and rerun.")
        return True
    except (OSError, RuntimeError, ValueError) as error:
        print(f"[{repository_id}] FAILED: {error}", file=sys.stderr, flush=True)
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, help="Factory service TOML (or FACTORY_SERVICE_CONFIG)")
    parser.add_argument("--dry-run", action="store_true", help="Check pushes without updating remote refs")
    args = parser.parse_args(argv)
    try:
        selected = args.config or os.environ.get("FACTORY_SERVICE_CONFIG")
        repositories = registered_repositories(Path(selected) if selected else running_config())
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f"{'DRY RUN' if args.dry_run else 'PUSH'}: {len(repositories)} registered repositories", flush=True)
    failed = [rid for rid, path in repositories if not push(rid, path, dry_run=args.dry_run)]
    print(f"\n{len(repositories) - len(failed)}/{len(repositories)} succeeded"
          f"{' (dry-run)' if args.dry_run else ''}; failed: {', '.join(failed) or 'none'}", flush=True)
    return int(bool(failed))


if __name__ == "__main__":
    raise SystemExit(main())
