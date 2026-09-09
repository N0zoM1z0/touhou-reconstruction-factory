"""Live source, target, environment, and toolchain observations for replay."""

from __future__ import annotations

from contextlib import contextmanager
import fcntl
import hashlib
import os
from pathlib import Path
import stat
import subprocess
from typing import Iterable, Iterator

from .errors import ReplayError
from .oracle_receipts import ComponentObservation, SourceBinding, canonical_sha256


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def environment_binding(names: Iterable[str]) -> tuple[tuple[str, ...], str]:
    ordered = tuple(sorted(set(names)))
    values = {name: os.environ.get(name) for name in ordered}
    return ordered, canonical_sha256(values)


def capture_source_binding(repository: Path) -> SourceBinding:
    root = repository.resolve(strict=True)
    git_root = Path(_git(root, "rev-parse", "--show-toplevel")).resolve(strict=True)
    if not root.is_relative_to(git_root):
        raise ReplayError("repository scope is outside its Git worktree")
    scope = root.relative_to(git_root).as_posix() or "."
    head = _git(git_root, "rev-parse", "HEAD")
    tree = _git(git_root, "rev-parse", "HEAD^{tree}")
    pathspec = "." if scope == "." else scope
    listed = _git_bytes(
        git_root,
        "ls-files",
        "-z",
        "--cached",
        "--others",
        "--exclude-standard",
        "--",
        pathspec,
    )
    relative_paths = sorted(
        item.decode("utf-8", "surrogateescape")
        for item in listed.split(b"\0")
        if item
    )
    index_raw = _git_bytes(
        git_root,
        "ls-files",
        "-s",
        "-z",
        "--",
        pathspec,
    )
    index_modes: dict[str, tuple[str, str]] = {}
    for item in index_raw.split(b"\0"):
        if not item:
            continue
        header, separator, raw_path = item.partition(b"\t")
        fields = header.split()
        if not separator or len(fields) != 3:
            raise ReplayError("git index emitted a malformed staged entry")
        index_modes[raw_path.decode("utf-8", "surrogateescape")] = (
            fields[0].decode("ascii"),
            fields[1].decode("ascii"),
        )
    untracked_raw = _git_bytes(
        git_root,
        "ls-files",
        "-z",
        "--others",
        "--exclude-standard",
        "--",
        pathspec,
    )
    untracked = sum(bool(item) for item in untracked_raw.split(b"\0"))
    digest = hashlib.sha256()
    digest.update(scope.encode("utf-8", "surrogateescape"))
    expanded_file_count = 0
    for relative in relative_paths:
        path = git_root / relative
        encoded = relative.encode("utf-8", "surrogateescape")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
        try:
            mode = path.lstat().st_mode
        except FileNotFoundError:
            digest.update(b"missing")
            expanded_file_count += 1
            continue
        if stat.S_ISLNK(mode):
            raise ReplayError(f"source snapshot rejects symlinked input: {relative}")
        index_mode = index_modes.get(relative)
        if stat.S_ISDIR(mode) and index_mode is not None and index_mode[0] == "160000":
            tree_sha256, tree_size, tree_files = _directory_digest(
                path,
                excluded_names={".git"},
            )
            digest.update(b"gitlink")
            digest.update(index_mode[1].encode("ascii"))
            digest.update(bytes.fromhex(tree_sha256))
            digest.update(tree_size.to_bytes(8, "big"))
            expanded_file_count += tree_files
            continue
        if not stat.S_ISREG(mode):
            raise ReplayError(f"source snapshot rejects non-file input: {relative}")
        payload_digest = file_sha256(path)
        digest.update(stat.S_IMODE(mode).to_bytes(4, "big"))
        digest.update(bytes.fromhex(payload_digest))
        expanded_file_count += 1
    status = _git_bytes(
        git_root,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
        "--",
        pathspec,
    )
    return SourceBinding(
        git_commit=head,
        git_tree=tree,
        repository_scope=scope,
        snapshot_sha256=digest.hexdigest(),
        file_count=expanded_file_count,
        dirty=bool(status),
        untracked_files=untracked,
    )


def observe_component(
    component_id: str,
    path: Path,
    *,
    logical_path: str,
    kind: str | None = None,
) -> ComponentObservation:
    resolved = path.expanduser().resolve(strict=True)
    if resolved.is_symlink():
        raise ReplayError(f"toolchain component must not be a symlink: {path}")
    if resolved.is_file():
        if kind not in {None, "file", "runtime", "native-attestation"}:
            raise ReplayError(f"component kind does not describe a file: {kind}")
        return ComponentObservation(
            id=component_id,
            kind=kind or "file",
            logical_path=logical_path,
            sha256=file_sha256(resolved),
            size=resolved.stat().st_size,
            file_count=1,
        )
    if not resolved.is_dir():
        raise ReplayError(f"toolchain component is not a file or directory: {path}")
    if kind not in {None, "directory-tree"}:
        raise ReplayError(f"component kind does not describe a directory: {kind}")
    tree_sha256, total_size, file_count = _directory_digest(resolved)
    if not file_count:
        raise ReplayError(f"toolchain component directory is empty: {path}")
    return ComponentObservation(
        id=component_id,
        kind="directory-tree",
        logical_path=logical_path,
        sha256=tree_sha256,
        size=total_size,
        file_count=file_count,
    )


def component_set_sha256(components: Iterable[ComponentObservation]) -> str:
    from .ontology import to_primitive

    return canonical_sha256(to_primitive(tuple(components)))


@contextmanager
def repository_lock(
    repository: Path,
    *,
    exclusive: bool,
) -> Iterator[None]:
    """Coordinate factory readers and replay writers through the Git directory."""

    root = repository.resolve(strict=True)
    try:
        raw_path = subprocess.check_output(
            [
                "git",
                "-C",
                str(root),
                "rev-parse",
                "--git-path",
                "reconstruction-factory-replay.lock",
            ],
            stderr=subprocess.PIPE,
            text=True,
        ).strip()
    except subprocess.CalledProcessError as error:
        detail = error.stderr.strip()
        raise ReplayError(f"cannot resolve repository replay lock: {detail}") from error
    path = Path(raw_path)
    if not path.is_absolute():
        path = root / path
    path.parent.mkdir(parents=True, exist_ok=True)
    operation = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
    with path.open("a+b") as stream:
        try:
            fcntl.flock(stream, operation | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ReplayError(f"another factory operation owns {root}") from error
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def _directory_digest(
    root: Path,
    *,
    excluded_names: set[str] | None = None,
) -> tuple[str, int, int]:
    excluded = excluded_names or set()
    digest = hashlib.sha256()
    total_size = 0
    file_count = 0
    for child in sorted(root.rglob("*")):
        relative_path = child.relative_to(root)
        if any(part in excluded for part in relative_path.parts):
            continue
        if child.is_symlink():
            raise ReplayError(f"directory snapshot rejects symlink: {child}")
        if not child.is_file():
            continue
        relative = relative_path.as_posix().encode("utf-8", "surrogateescape")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(bytes.fromhex(file_sha256(child)))
        total_size += child.stat().st_size
        file_count += 1
    return digest.hexdigest(), total_size, file_count


def _git(cwd: Path, *args: str) -> str:
    return _git_bytes(cwd, *args).decode("ascii").strip()


def _git_bytes(cwd: Path, *args: str) -> bytes:
    try:
        return subprocess.check_output(
            ["git", "-C", str(cwd), *args],
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as error:
        detail = error.stderr.decode("utf-8", "replace").strip()
        raise ReplayError(f"Git source identity failed: {detail}") from error
