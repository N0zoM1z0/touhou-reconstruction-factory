#!/usr/bin/env python3
"""Provision or verify the Factory's pinned VC7.1 SP1 compatibility payload."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import subprocess
import sys
import tomllib


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config" / "toolchains" / "msvc710-sp1.toml"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(*arguments: str, cwd: Path | None = None) -> str:
    return subprocess.check_output(
        ["git", *arguments],
        cwd=cwd,
        stderr=subprocess.STDOUT,
        text=True,
    ).strip()


def load() -> dict[str, object]:
    with MANIFEST.open("rb") as stream:
        manifest = tomllib.load(stream)
    if manifest.get("schema_version") != 1:
        raise ValueError("unsupported toolchain manifest schema")
    return manifest


def clone_if_needed(destination: Path, manifest: dict[str, object], check_only: bool) -> None:
    if destination.exists() or destination.is_symlink():
        if destination.is_symlink() or not (destination / ".git").is_dir():
            raise ValueError("toolchain destination exists but is not a regular Git checkout")
        return
    if check_only:
        raise ValueError("toolchain destination is absent")
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "git",
            "clone",
            "--filter=blob:none",
            "--no-checkout",
            str(manifest["repository"]),
            str(destination),
        ],
        check=True,
    )
    subprocess.run(
        ["git", "checkout", "--detach", str(manifest["commit"])],
        cwd=destination,
        check=True,
    )


def verify_checkout(destination: Path, manifest: dict[str, object]) -> None:
    head = git("rev-parse", "HEAD", cwd=destination)
    if head != manifest["commit"]:
        raise ValueError(f"toolchain checkout is {head}, expected {manifest['commit']}")
    if git("status", "--porcelain=v1", "--untracked-files=no", cwd=destination):
        raise ValueError("toolchain checkout has tracked modifications")
    expected_repository = str(manifest["repository"]).removesuffix(".git")
    remote = git("remote", "get-url", "origin", cwd=destination).removesuffix(".git")
    if remote != expected_repository:
        raise ValueError(f"toolchain origin is {remote!r}, expected {expected_repository!r}")
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("toolchain manifest has no file locks")
    for relative, expected in files.items():
        path = destination / str(relative)
        if not path.is_file():
            raise ValueError(f"toolchain component is missing: {relative}")
        actual = sha256(path)
        if actual != expected:
            raise ValueError(f"toolchain component differs: {relative}: {actual}")
    for relative in manifest.get("required_directories", []):
        if not (destination / str(relative)).is_dir():
            raise ValueError(f"toolchain directory is missing: {relative}")


def select_for_game(destination: Path, game_root: Path, check_only: bool) -> None:
    game = game_root.resolve(strict=True)
    if not (game / ".git").exists():
        raise ValueError("game root is not a Git worktree")
    tools = game / ".tools"
    selector = tools / "msvc710-sp1"
    if selector.is_symlink():
        if selector.resolve(strict=True) != destination.resolve(strict=True):
            raise ValueError(f"game selector points elsewhere: {selector}")
        return
    if selector.exists():
        raise ValueError(f"game selector exists and is not a symlink: {selector}")
    if check_only:
        raise ValueError(f"game selector is absent: {selector}")
    tools.mkdir(parents=True, exist_ok=True)
    selector.symlink_to(destination.resolve(strict=True), target_is_directory=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--game-root", type=Path)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    try:
        manifest = load()
        destination = args.destination.expanduser().absolute()
        clone_if_needed(destination, manifest, args.check_only)
        verify_checkout(destination, manifest)
        if args.game_root is not None:
            select_for_game(destination, args.game_root.expanduser(), args.check_only)
    except (OSError, KeyError, TypeError, ValueError, subprocess.CalledProcessError) as error:
        print(f"error: VC7.1 SP1 provisioning failed: {error}", file=sys.stderr)
        return 1
    print(
        f"VC7.1 SP1 payload OK: {manifest['id']} at {destination}"
        + (" (check only)" if args.check_only else "")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
