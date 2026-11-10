#!/usr/bin/env python3
"""Archive old terminal command captures for offline tool analysis (dry run by default)."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import tarfile
import tempfile


FILES = {"record.json", "stdout.bin", "stderr.bin"}
TERMINAL = {"completed", "timed-out"}


def signature(path):
    stat = path.lstat()
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns


def digest(stream):
    return hashlib.file_digest(stream, "sha256").hexdigest()


@contextmanager
def repository_lock(root, repository):
    # Use the writer's existing lock; never create a second locking convention.
    path = root / "locks" / f"{repository}.lock"
    if path.is_symlink():
        raise ValueError(f"unsafe lock: {path}")
    with path.open("a+b") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def candidates(directory, cutoff):
    selected = []
    skipped = {}
    for command in sorted(directory.iterdir()):
        reason = None
        if command.is_symlink() or not command.is_dir() or not re.fullmatch(r"[0-9a-f]{32}", command.name):
            reason = "unexpected-entry"
        else:
            entries = list(command.iterdir())
            if not entries:
                continue  # A previous archive's ID reservation.
            if {path.name for path in entries} != FILES or any(path.is_symlink() or not path.is_file() for path in entries):
                reason = "unexpected-files"
            else:
                try:
                    record = json.loads((command / "record.json").read_bytes())
                    if (record["schema_version"] != 1
                            or record["repository_id"] != directory.name
                            or record["command_id"] != f"repository-command:{command.name}"):
                        reason = "identity-mismatch"
                    elif record["state"] not in TERMINAL:
                        reason = "nonterminal"
                    elif datetime.fromisoformat(record["finished_at"].replace("Z", "+00:00")) >= cutoff:
                        reason = "recent"
                    elif any((command / f"{stream}.bin").stat().st_size != record[f"{stream}_captured_bytes"] for stream in ("stdout", "stderr")):
                        reason = "capture-size-mismatch"
                    else:
                        selected.append((command, record))
                except (ValueError, KeyError, TypeError, AttributeError):
                    reason = "invalid-record"
        if reason:
            skipped[reason] = skipped.get(reason, 0) + 1
    return selected, skipped


def verify_archive(archive, originals):
    """Read every compressed member and compare it to the still-present source."""
    seen = set()
    with tarfile.open(archive, "r|gz") as source:
        for member in source:
            if not member.isfile() or member.name not in originals or member.name in seen:
                raise ValueError(f"unexpected archive member: {member.name}")
            path, expected = originals[member.name]
            if signature(path) != expected:
                raise ValueError(f"source changed: {path}")
            with source.extractfile(member) as saved, path.open("rb") as live:
                if digest(saved) != digest(live):
                    raise ValueError(f"archive content mismatch: {path}")
            seen.add(member.name)
    if seen != originals.keys():
        raise ValueError("archive is missing command files")


def archive_repository(root, destination, repository, cutoff, *, apply=False):
    directory = root / "commands" / repository
    if directory.is_symlink() or not directory.is_dir() or not re.fullmatch(r"[a-z0-9][a-z0-9._:-]*", repository):
        raise ValueError(f"unsafe repository directory: {directory}")
    with repository_lock(root, repository):
        selected, skipped = candidates(directory, cutoff)
        originals = {
            f"{repository}/{command.name}/{name}": (command / name, signature(command / name))
            for command, _ in selected for name in sorted(FILES)
        }
        allocated = sum(path.stat().st_blocks * 512 for path, _ in originals.values())
        result = {"repository": repository, "commands": len(selected), "source_allocated_bytes": allocated, "skipped": skipped}
        if not apply or not selected:
            return result
        destination.mkdir(parents=True, exist_ok=True, mode=0o700)
        archive = destination / f"{repository}.tar.gz"
        index = destination / f"{repository}.jsonl.gz"
        if archive.exists() or index.exists():
            raise FileExistsError(f"archive already exists for {repository}; use a new destination")
        with tempfile.TemporaryDirectory(prefix=f".{repository}-", dir=destination) as temp:
            pending = Path(temp) / archive.name
            pending_index = Path(temp) / index.name
            with tarfile.open(pending, "w:gz", compresslevel=6) as target:
                for name, (path, _) in originals.items():
                    target.add(path, arcname=name, recursive=False)
            with gzip.open(pending_index, "wt", encoding="utf-8", compresslevel=6) as target:
                for command, record in selected:
                    target.write(json.dumps({"archive": archive.name, "member_prefix": f"{repository}/{command.name}", "record": record}, ensure_ascii=False) + "\n")
            verify_archive(pending, originals)
            with gzip.open(pending_index, "rt", encoding="utf-8") as source:
                for line, (command, record) in zip(source, selected, strict=True):
                    saved = json.loads(line)
                    if saved != {"archive": archive.name, "member_prefix": f"{repository}/{command.name}", "record": record}:
                        raise ValueError("command index differs from original record")
            # Persist both verified artifacts before deleting any capture.
            for path in (pending, pending_index):
                path.chmod(0o600)
                with path.open("rb") as stream:
                    os.fsync(stream.fileno())
            pending.rename(archive)
            pending_index.rename(index)
            fd = os.open(destination, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        # Keep each empty directory: run_shell must reject an old ID rather than
        # rerun a command whose live record is now available only in the archive.
        for path, expected in originals.values():
            if signature(path) != expected:
                raise ValueError(f"source changed before removal: {path}")
        for path, _ in originals.values():
            path.unlink()
        result["archive_bytes"] = archive.stat().st_size + index.stat().st_size
        result["archive"] = str(archive)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="existing repository-work storage root")
    parser.add_argument("--destination", type=Path, required=True, help="new offline archive directory")
    parser.add_argument("--older-than-days", type=int, default=7)
    parser.add_argument("--repository", action="append", help="limit to these repository IDs")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.older_than_days < 1:
        parser.error("--older-than-days must be positive")
    root, destination = args.root.resolve(strict=True), args.destination.resolve()
    if root == destination or root in destination.parents:
        parser.error("destination must be outside the live repository-work store")
    cutoff = datetime.now(timezone.utc) - timedelta(days=args.older_than_days)
    repositories = args.repository or sorted(path.name for path in (root / "commands").iterdir())
    for repository in repositories:
        try:
            result = archive_repository(root, destination, repository, cutoff, apply=args.apply)
        except BlockingIOError:
            result = {"repository": repository, "skipped": "writer-lock-busy"}
        print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
