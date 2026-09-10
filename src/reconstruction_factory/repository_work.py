"""Durable Bash execution in operator-registered live Git worktrees.

The provider deliberately grants broad in-repository autonomy.  It records what
happened and leaves Git commits as reviewable checkpoints; it does not interpret
a successful command or commit as Oracle evidence.
"""

from __future__ import annotations

import base64
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import subprocess
import time
from typing import Any, Iterator
import uuid

from .errors import ReplayError, RepositoryWorkError
from .replay_identity import repository_lock
from .semantic_debt import scan_semantic_debt
from .service_config import RepositoryRegistration, ServiceConfig


REPOSITORY_COMMAND_SCHEMA_VERSION = 1
_COMMAND_ID = re.compile(r"^repository-command:([0-9a-f]{32})$")
_REPOSITORY_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]*$")
_MAX_SCRIPT_BYTES = 65536
_OUTPUT_PAGE_BYTES = 16384


class RepositoryWorkStore:
    """Persist commands and expose one serialized live worktree per repository."""

    def __init__(self, config: ServiceConfig) -> None:
        self.config = config
        self.policy = config.repository_work
        self.root = self.policy.root
        self.commands = self.root / "commands"
        self.locks = self.root / "locks"

    def status(self, repository_id: str) -> dict[str, Any]:
        self._require_enabled()
        registration = self.config.repository(repository_id)
        with self._repository_lock(repository_id), self._factory_repository_lock(
            registration, exclusive=False
        ):
            return _repository_status(registration)

    def semantic_debt_report(
        self,
        repository_id: str,
        *,
        relative_path: str,
        category: str,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        """Return a live-worktree-bound heuristic routing report."""

        self._require_enabled()
        registration = self.config.repository(repository_id)
        with self._repository_lock(repository_id), self._factory_repository_lock(
            registration, exclusive=False
        ):
            before = _repository_status(registration)
            report = scan_semantic_debt(
                registration.path,
                relative_path=relative_path,
                category=category,
                limit=limit,
                offset=offset,
            )
            after = _repository_status(registration)
            if (
                before["head_commit"] != after["head_commit"]
                or before["status_sha256"] != after["status_sha256"]
            ):
                raise RepositoryWorkError(
                    "repository changed during semantic-debt scan; retry against the new state"
                )
            report["repository_id"] = repository_id
            report["source_binding"] = {
                "head_commit": after["head_commit"],
                "status_sha256": after["status_sha256"],
                "dirty": after["dirty"],
            }
            return report

    def run_shell(
        self,
        repository_id: str,
        script: str,
        *,
        relative_cwd: str,
        timeout_seconds: int,
    ) -> dict[str, Any]:
        self._require_enabled()
        script_bytes = script.encode("utf-8")
        if not script_bytes or len(script_bytes) > _MAX_SCRIPT_BYTES or "\0" in script:
            raise RepositoryWorkError(
                "script must contain 1 through 65536 UTF-8 bytes"
            )
        if (
            not isinstance(timeout_seconds, int)
            or isinstance(timeout_seconds, bool)
            or not 1 <= timeout_seconds <= self.policy.command_timeout_seconds
        ):
            raise RepositoryWorkError(
                "timeout_seconds exceeds the configured repository-work command limit"
            )
        registration = self.config.repository(repository_id)
        repository = registration.path
        cwd = _safe_cwd(repository, relative_cwd)
        normalized_cwd = cwd.relative_to(repository).as_posix()
        if normalized_cwd == ".":
            normalized_cwd = "."

        with self._repository_lock(repository_id), self._factory_repository_lock(
            registration, exclusive=True
        ):
            before = _repository_status(registration)
            command_id = f"repository-command:{uuid.uuid4().hex}"
            directory = self._command_directory(repository_id, command_id)
            directory.mkdir(parents=True, mode=0o700)
            record: dict[str, Any] = {
                "schema_version": REPOSITORY_COMMAND_SCHEMA_VERSION,
                "command_id": command_id,
                "repository_id": repository_id,
                "script_sha256": hashlib.sha256(script_bytes).hexdigest(),
                "relative_cwd": normalized_cwd,
                "timeout_seconds": timeout_seconds,
                "started_at": _format_time(_now()),
                "finished_at": None,
                "state": "running",
                "exit_code": None,
                "timed_out": False,
                "filesystem_persisted": True,
                "stdout_captured_bytes": 0,
                "stdout_observed_bytes": 0,
                "stderr_captured_bytes": 0,
                "stderr_observed_bytes": 0,
                "output_truncated": False,
                "before": before,
                "after": None,
                "head_relation": None,
                "created_commits": [],
            }
            _write_json(directory / "record.json", record)
            try:
                outcome = self._execute_shell(
                    registration,
                    script,
                    cwd,
                    timeout_seconds,
                    directory,
                )
            except (OSError, RepositoryWorkError) as error:
                record["state"] = "interrupted"
                record["finished_at"] = _format_time(_now())
                _write_json(directory / "record.json", record)
                raise RepositoryWorkError(
                    f"repository command {command_id} could not complete: {error}; "
                    "inspect the live worktree before retrying because partial changes may persist"
                ) from error

            after = _repository_status(registration)
            relation, commits = _head_change(
                repository, before["head_commit"], after["head_commit"]
            )
            record.update(outcome)
            record["after"] = after
            record["head_relation"] = relation
            record["created_commits"] = commits
            record["state"] = "timed-out" if record["timed_out"] else "completed"
            record["finished_at"] = _format_time(_now())
            _write_json(directory / "record.json", record)
            result = _public_command(record)
            result["stdout"] = self._output_page_unlocked(
                directory, record, "stdout", 0, _OUTPUT_PAGE_BYTES
            )
            result["stderr"] = self._output_page_unlocked(
                directory, record, "stderr", 0, _OUTPUT_PAGE_BYTES
            )
            return result

    def command_output(
        self,
        repository_id: str,
        command_id: str,
        *,
        stream: str,
        offset: int,
        limit: int,
    ) -> dict[str, Any]:
        self._require_enabled()
        self.config.repository(repository_id)
        _page_bounds(limit, offset)
        if stream not in {"stdout", "stderr"}:
            raise RepositoryWorkError("stream must be stdout or stderr")
        with self._repository_lock(repository_id):
            directory = self._command_directory(repository_id, command_id)
            record = _read_record(directory / "record.json")
            if record.get("repository_id") != repository_id:
                raise RepositoryWorkError(
                    "repository command does not belong to this repository"
                )
            if record["state"] == "running":
                record["state"] = "interrupted"
                record["finished_at"] = _format_time(_now())
                _write_json(directory / "record.json", record)
            return self._output_page_unlocked(
                directory, record, stream, offset, limit
            )

    def _execute_shell(
        self,
        registration: RepositoryRegistration,
        script: str,
        cwd: Path,
        timeout_seconds: int,
        directory: Path,
    ) -> dict[str, Any]:
        bwrap = shutil.which("bwrap")
        nice = shutil.which("nice")
        if not bwrap or not nice:
            raise RepositoryWorkError(
                "repository work requires bubblewrap and nice"
            )
        argv = _sandbox_argv(
            bwrap,
            nice,
            registration.path,
            cwd,
            script,
            self.policy.git_author_name,
            self.policy.git_author_email,
            self.policy.shared_tool_roots,
            registration.work_environment,
            registration.work_state_roots,
        )
        try:
            process = subprocess.Popen(
                argv,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
        except OSError as error:
            raise RepositoryWorkError(
                "cannot start the isolated repository process"
            ) from error
        assert process.stdout is not None and process.stderr is not None
        paths = {
            process.stdout.fileno(): directory / "stdout.bin",
            process.stderr.fileno(): directory / "stderr.bin",
        }
        handles = {descriptor: path.open("wb") for descriptor, path in paths.items()}
        observed = {descriptor: 0 for descriptor in paths}
        captured = {descriptor: 0 for descriptor in paths}
        selector = selectors.DefaultSelector()
        for descriptor in paths:
            os.set_blocking(descriptor, False)
            selector.register(descriptor, selectors.EVENT_READ)
        output_total = 0
        timed_out = False
        deadline = time.monotonic() + timeout_seconds
        try:
            while selector.get_map():
                if process.poll() is None and time.monotonic() >= deadline:
                    timed_out = True
                    os.killpg(process.pid, signal.SIGKILL)
                for key, _ in selector.select(0.1):
                    try:
                        block = os.read(key.fd, 65536)
                    except BlockingIOError:
                        continue
                    if not block:
                        selector.unregister(key.fd)
                        continue
                    observed[key.fd] += len(block)
                    remaining = self.policy.max_command_output_bytes - output_total
                    if remaining > 0:
                        payload = block[:remaining]
                        handles[key.fd].write(payload)
                        captured[key.fd] += len(payload)
                        output_total += len(payload)
            returncode = process.wait()
        except Exception:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise
        finally:
            selector.close()
            for handle in handles.values():
                handle.close()
            process.stdout.close()
            process.stderr.close()
        stdout_fd, stderr_fd = paths
        return {
            "exit_code": returncode,
            "timed_out": timed_out,
            "stdout_captured_bytes": captured[stdout_fd],
            "stdout_observed_bytes": observed[stdout_fd],
            "stderr_captured_bytes": captured[stderr_fd],
            "stderr_observed_bytes": observed[stderr_fd],
            "output_truncated": output_total < sum(observed.values()),
        }

    def _output_page_unlocked(
        self,
        directory: Path,
        record: dict[str, Any],
        stream: str,
        offset: int,
        limit: int,
    ) -> dict[str, Any]:
        path = directory / f"{stream}.bin"
        size = path.stat().st_size if path.exists() else 0
        with path.open("rb") if path.exists() else open(os.devnull, "rb") as handle:
            handle.seek(offset)
            payload = handle.read(limit)
        result: dict[str, Any] = {
            "stream": stream,
            "captured_size": size,
            "observed_size": record[f"{stream}_observed_bytes"],
            "offset": offset,
            "bytes_returned": len(payload),
            "next_offset": offset + len(payload)
            if offset + len(payload) < size
            else None,
        }
        try:
            result["text"] = payload.decode("utf-8")
            result["encoding"] = "utf-8"
        except UnicodeDecodeError:
            result["base64"] = base64.b64encode(payload).decode("ascii")
            result["encoding"] = "base64"
        return result

    def _command_directory(self, repository_id: str, command_id: str) -> Path:
        _require_repository_id(repository_id)
        suffix = _command_suffix(command_id)
        return self.commands / repository_id / suffix

    def _require_enabled(self) -> None:
        if not self.policy.enabled:
            raise RepositoryWorkError(
                "live repository work is disabled by operator policy"
            )
        self._ensure_layout()

    def _ensure_layout(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        resolved = self.root.resolve(strict=True)
        if resolved != self.root:
            raise RepositoryWorkError(
                "repository-work root changed after configuration loading"
            )
        for path in (self.commands, self.locks):
            path.mkdir(exist_ok=True, mode=0o700)
            if path.is_symlink() or not path.is_dir():
                raise RepositoryWorkError(
                    "repository-work storage layout contains an unsafe link"
                )

    @contextmanager
    def _repository_lock(self, repository_id: str) -> Iterator[None]:
        _require_repository_id(repository_id)
        self._ensure_layout()
        with _file_lock(self.locks / f"{repository_id}.lock"):
            yield

    @contextmanager
    def _factory_repository_lock(
        self,
        registration: RepositoryRegistration,
        *,
        exclusive: bool,
    ) -> Iterator[None]:
        try:
            with repository_lock(registration.path, exclusive=exclusive):
                yield
        except ReplayError as error:
            raise RepositoryWorkError(
                "another Factory operation currently owns this repository"
            ) from error


def _repository_status(registration: RepositoryRegistration) -> dict[str, Any]:
    repository = registration.path
    top = Path(_git_text(repository, "rev-parse", "--show-toplevel")).resolve()
    if top != repository:
        raise RepositoryWorkError(
            "registered repository path must be the Git worktree root"
        )
    head = _git_text(repository, "rev-parse", "--verify", "HEAD")
    branch_process = subprocess.run(
        ["git", "-C", str(repository), "symbolic-ref", "--short", "-q", "HEAD"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    branch = branch_process.stdout.decode("utf-8", "replace").strip() or None
    status = _git_bytes(
        repository,
        "status",
        "--porcelain=v2",
        "--branch",
        "-z",
        "--untracked-files=all",
    )
    counts = _parse_porcelain_v2(status)
    return {
        "repository_id": registration.id,
        "source_mode": "live-including-ignored",
        "head_commit": head,
        "branch": branch,
        "detached_head": branch is None,
        "upstream_branch": counts.pop("upstream_branch"),
        "ahead": counts.pop("ahead"),
        "behind": counts.pop("behind"),
        "dirty": any(counts.values()),
        **counts,
        "status_sha256": hashlib.sha256(status).hexdigest(),
        "git_commit_is_checkpoint_only": True,
        "oracle_verification_required_for_exactness": True,
    }


def _parse_porcelain_v2(payload: bytes) -> dict[str, Any]:
    staged = unstaged = untracked = conflicted = 0
    upstream: str | None = None
    ahead = behind = 0
    fields = payload.split(b"\0")
    index = 0
    while index < len(fields):
        entry = fields[index]
        index += 1
        if not entry:
            continue
        if entry.startswith(b"# branch.upstream "):
            upstream = entry[len(b"# branch.upstream ") :].decode(
                "utf-8", "replace"
            )
        elif entry.startswith(b"# branch.ab "):
            parts = entry.split()
            if len(parts) == 4:
                ahead = int(parts[2][1:])
                behind = int(parts[3][1:])
        elif entry.startswith(b"? "):
            untracked += 1
        elif entry.startswith(b"u "):
            conflicted += 1
        elif entry.startswith((b"1 ", b"2 ")):
            parts = entry.split(b" ", 2)
            if len(parts) < 2 or len(parts[1]) != 2:
                raise RepositoryWorkError("Git emitted malformed porcelain-v2 status")
            xy = parts[1]
            if xy[0:1] != b".":
                staged += 1
            if xy[1:2] != b".":
                unstaged += 1
            if entry.startswith(b"2 "):
                index += 1
    return {
        "staged_changes": staged,
        "unstaged_changes": unstaged,
        "untracked_files": untracked,
        "conflicted_entries": conflicted,
        "upstream_branch": upstream,
        "ahead": ahead,
        "behind": behind,
    }


def _head_change(
    repository: Path, before: str, after: str
) -> tuple[str, list[dict[str, str]]]:
    if before == after:
        return "unchanged", []
    ancestor = subprocess.run(
        ["git", "-C", str(repository), "merge-base", "--is-ancestor", before, after],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        timeout=30,
    )
    if ancestor.returncode != 0:
        return "rewritten-or-diverged", []
    output = _git_text(
        repository,
        "log",
        "--reverse",
        "--format=%H%x00%s",
        "-z",
        f"{before}..{after}",
    )
    values = output.split("\0")
    commits = [
        {"commit": values[index], "subject": values[index + 1]}
        for index in range(0, len(values) - 1, 2)
        if values[index]
    ]
    return "advanced", commits


def _sandbox_argv(
    bwrap: str,
    nice: str,
    repository: Path,
    cwd: Path,
    script: str,
    author_name: str,
    author_email: str,
    shared_tool_roots: tuple[Path, ...],
    work_environment: tuple[tuple[str, str], ...],
    work_state_roots: tuple[Path, ...],
) -> list[str]:
    argv = [
        nice,
        "-n",
        "10",
        bwrap,
        "--unshare-all",
        "--die-with-parent",
        "--new-session",
        "--cap-drop",
        "ALL",
        "--clearenv",
        "--ro-bind",
        "/usr",
        "/usr",
        "--ro-bind",
        "/etc",
        "/etc",
        "--symlink",
        "usr/bin",
        "/bin",
        "--symlink",
        "usr/lib",
        "/lib",
        "--symlink",
        "usr/lib64",
        "/lib64",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--dir",
        "/run",
        "--tmpfs",
        "/tmp",
        "--dir",
        "/tmp/home",
    ]
    created = {Path("/run"), Path("/tmp"), Path("/tmp/home")}
    for optional in (Path("/sys"), Path("/opt"), Path("/var/cache/fontconfig")):
        if optional.exists():
            _add_parent_dirs(argv, optional, created)
            argv.extend(("--ro-bind", str(optional), str(optional)))
    for tool_root in shared_tool_roots:
        _add_parent_dirs(argv, tool_root, created)
        argv.extend(("--ro-bind", str(tool_root), str(tool_root)))
    for state_root in work_state_roots:
        _add_parent_dirs(argv, state_root, created)
        argv.extend(("--bind", str(state_root), str(state_root)))
    _add_parent_dirs(argv, repository, created)
    argv.extend(("--bind", str(repository), str(repository)))
    argv.extend(
        (
            "--symlink",
            str(repository),
            "/workspace",
            "--chdir",
            str(cwd),
            "--setenv",
            "HOME",
            "/tmp/home",
            "--setenv",
            "XDG_RUNTIME_DIR",
            "/run",
            "--setenv",
            "PATH",
            "/usr/local/bin:/usr/bin:/bin",
            "--setenv",
            "LANG",
            "C.UTF-8",
            "--setenv",
            "LC_ALL",
            "C.UTF-8",
            "--setenv",
            "TZ",
            "UTC",
            "--setenv",
            "GIT_AUTHOR_NAME",
            author_name,
            "--setenv",
            "GIT_AUTHOR_EMAIL",
            author_email,
            "--setenv",
            "GIT_COMMITTER_NAME",
            author_name,
            "--setenv",
            "GIT_COMMITTER_EMAIL",
            author_email,
            "--setenv",
            "GIT_TERMINAL_PROMPT",
            "0",
            "--setenv",
            "PAGER",
            "cat",
            "/bin/bash",
            "--noprofile",
            "--norc",
            "-lc",
            script,
        )
    )
    if work_environment:
        insertion = len(argv) - 5
        configured: list[str] = []
        for name, value in work_environment:
            configured.extend(("--setenv", name, value))
        argv[insertion:insertion] = configured
    return argv


def _add_parent_dirs(argv: list[str], path: Path, created: set[Path]) -> None:
    for parent in reversed(path.parents):
        if parent == Path("/") or parent in created:
            continue
        argv.extend(("--dir", str(parent)))
        created.add(parent)


def _safe_cwd(repository: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\0" in relative:
        raise RepositoryWorkError("relative_cwd must be a non-empty UTF-8 path")
    candidate = Path(relative)
    if candidate.is_absolute():
        raise RepositoryWorkError("relative_cwd must remain repository-relative")
    try:
        resolved = (repository / candidate).resolve(strict=True)
    except OSError as error:
        raise RepositoryWorkError("relative_cwd does not exist") from error
    if not resolved.is_relative_to(repository) or not resolved.is_dir():
        raise RepositoryWorkError(
            "relative_cwd must resolve to a directory inside the registered repository"
        )
    return resolved


def _git_text(repository: Path, *args: str) -> str:
    return _git_bytes(repository, *args).decode("utf-8", "replace").strip()


def _git_bytes(repository: Path, *args: str) -> bytes:
    try:
        return subprocess.check_output(
            ["git", "-C", str(repository), *args],
            stderr=subprocess.PIPE,
            timeout=60,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        detail = getattr(error, "stderr", b"") or b""
        raise RepositoryWorkError(
            "registered repository Git operation failed: "
            + detail.decode("utf-8", "replace").strip()
        ) from error


def _public_command(record: dict[str, Any]) -> dict[str, Any]:
    return {
        key: record[key]
        for key in (
            "command_id",
            "repository_id",
            "script_sha256",
            "relative_cwd",
            "timeout_seconds",
            "started_at",
            "finished_at",
            "state",
            "exit_code",
            "timed_out",
            "filesystem_persisted",
            "stdout_captured_bytes",
            "stdout_observed_bytes",
            "stderr_captured_bytes",
            "stderr_observed_bytes",
            "output_truncated",
            "before",
            "after",
            "head_relation",
            "created_commits",
        )
    }


def _read_record(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise RepositoryWorkError("unknown repository command ID") from error
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RepositoryWorkError("cannot read repository command record") from error
    if not isinstance(value, dict):
        raise RepositoryWorkError("repository command record is not an object")
    if value.get("schema_version") != REPOSITORY_COMMAND_SCHEMA_VERSION:
        raise RepositoryWorkError("unsupported repository command record schema")
    _command_suffix(value.get("command_id"))
    return value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
    try:
        temporary.write_text(payload, encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def _file_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open("a+b") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _command_suffix(command_id: Any) -> str:
    match = _COMMAND_ID.fullmatch(command_id) if isinstance(command_id, str) else None
    if match is None:
        raise RepositoryWorkError("invalid repository command ID")
    return match.group(1)


def _require_repository_id(repository_id: str) -> None:
    if not isinstance(repository_id, str) or _REPOSITORY_ID.fullmatch(repository_id) is None:
        raise RepositoryWorkError("invalid repository ID")


def _page_bounds(limit: int, offset: int) -> None:
    if (
        not isinstance(limit, int)
        or isinstance(limit, bool)
        or not 1 <= limit <= 65536
        or not isinstance(offset, int)
        or isinstance(offset, bool)
        or offset < 0
    ):
        raise RepositoryWorkError("output page bounds are invalid")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _format_time(value: datetime) -> str:
    return value.isoformat()
