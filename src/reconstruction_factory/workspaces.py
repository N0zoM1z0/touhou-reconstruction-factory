"""Capability-addressed, disposable source workspaces for remote collaboration.

The workspace provider deliberately separates composability from authority.  A
caller may run arbitrary Bash, but only against a bounded tmpfs copy of a
committed source snapshot.  The canonical repository, ignored build inputs,
operator home, credentials, network, and Truth Kernel stores are never mounted.
"""

from __future__ import annotations

import base64
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import fcntl
import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import resource
import selectors
import shlex
import shutil
import signal
import stat
import subprocess
import tarfile
import time
from typing import Any, Iterator
import uuid

from .errors import WorkspaceConflictError, WorkspaceError
from .oracle_receipts import canonical_sha256
from .replay_identity import repository_lock
from .service_config import RepositoryRegistration, ServiceConfig, WorkspacePolicy


WORKSPACE_SCHEMA_VERSION = 1
_WORKSPACE_ID = re.compile(r"^workspace:([0-9a-f]{32})$")
_COMMAND_ID = re.compile(r"^command:([0-9a-f]{32})$")
_MAX_SCRIPT_BYTES = 65536
_SEARCH_CAPTURE_BYTES = 8 * 1024 * 1024
_ARCHIVE_OVERHEAD_BYTES = 16 * 1024 * 1024
_WORKSPACE_PROCESS_HEADROOM = 512


class WorkspaceStore:
    """Persistent workspace records and isolated source-tree operations."""

    def __init__(self, config: ServiceConfig) -> None:
        self.config = config
        self.policy = config.workspace
        self.root = self.policy.root
        self.records = self.root / "records"
        self.trees = self.root / "trees"
        self.commands = self.root / "commands"
        self.locks = self.root / "locks"
        self.temporary = self.root / "tmp"

    def create(
        self, registration: RepositoryRegistration, idempotency_key: str
    ) -> dict[str, Any]:
        self._require_enabled()
        _validate_idempotency_key(idempotency_key)
        request_sha256 = canonical_sha256(
            {"repository_id": registration.id, "idempotency_key": idempotency_key}
        )
        self._ensure_layout()
        with self._global_lock():
            self._cleanup_expired()
            records = tuple(self._all_records())
            for record in records:
                if record["idempotency_key_sha256"] != _sha256_text(idempotency_key):
                    continue
                if record["request_sha256"] != request_sha256:
                    raise WorkspaceConflictError(
                        "workspace idempotency key is already bound to another request"
                    )
                return self._public(record)
            active = [
                item for item in records if self._effective_state(item) == "active"
            ]
            if len(active) >= self.policy.max_active:
                raise WorkspaceConflictError(
                    "workspace capacity is full; discard an owned workspace or wait for expiry"
                )

            suffix = uuid.uuid4().hex
            workspace_id = f"workspace:{suffix}"
            container = self.trees / suffix
            staging = self.temporary / f"create-{suffix}"
            source_tree = staging / "tree"
            metadata = staging / "git"
            staging.mkdir(mode=0o700)
            try:
                with repository_lock(registration.path, exclusive=False):
                    source = _source_identity(registration.path)
                    expected_counts = _validate_committed_snapshot(
                        registration.path,
                        source["git_commit"],
                        self.policy,
                    )
                    archive = staging / "source.tar"
                    _git_archive(
                        registration.path,
                        source["git_commit"],
                        archive,
                    )
                    counts = _extract_archive(archive, source_tree, self.policy)
                    if counts["file_count"] != expected_counts["file_count"]:
                        raise WorkspaceError(
                            "committed source archive omits entries from the validated Git tree"
                        )
                archive.unlink()
                _initialize_baseline(source_tree, metadata)
                os.replace(staging, container)
            except Exception:
                shutil.rmtree(staging, ignore_errors=True)
                raise

            now = _now()
            record = {
                "schema_version": WORKSPACE_SCHEMA_VERSION,
                "workspace_id": workspace_id,
                "repository_id": registration.id,
                "registration_sha256": canonical_sha256(registration.identity_dict()),
                "idempotency_key_sha256": _sha256_text(idempotency_key),
                "request_sha256": request_sha256,
                "created_at": _format_time(now),
                "expires_at": _format_time(
                    now + timedelta(seconds=self.policy.ttl_seconds)
                ),
                "state": "active",
                "source_mode": "committed-head",
                "source_git_commit": source["git_commit"],
                "source_git_tree": source["git_tree"],
                "source_worktree_dirty_observed": source["dirty"],
                "snapshot_file_count": counts["file_count"],
                "snapshot_bytes": counts["bytes"],
            }
            _write_json(self._record_path(workspace_id), record)
            return self._public(record)

    def get(self, workspace_id: str) -> dict[str, Any]:
        with self._workspace_lock(workspace_id):
            record = self._load_record(workspace_id)
            record = self._expire(record)
            return self._public(record)

    def list_files(
        self,
        workspace_id: str,
        *,
        glob: str,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        _page_bounds(limit, offset, 100)
        _validate_glob(glob)
        with self._workspace_lock(workspace_id):
            record, tree, _ = self._active(workspace_id)
            files, _, _ = _validate_tree(tree, self.policy)
            selected = tuple(path for path in files if fnmatch.fnmatchcase(path, glob))
            return {
                "workspace_id": workspace_id,
                "glob": glob,
                **_page(
                    len(selected), offset, limit, selected[offset : offset + limit]
                ),
                "source_git_commit": record["source_git_commit"],
            }

    def read_file(
        self,
        workspace_id: str,
        relative_path: str,
        *,
        offset: int,
        limit: int,
    ) -> dict[str, Any]:
        _page_bounds(limit, offset, 65536)
        with self._workspace_lock(workspace_id):
            _, tree, _ = self._active(workspace_id)
            path = _safe_path(tree, relative_path, require_file=True)
            size = path.stat().st_size
            if size > self.policy.max_file_bytes:
                raise WorkspaceError("workspace file exceeds the configured read limit")
            with path.open("rb") as stream:
                stream.seek(offset)
                payload = stream.read(limit)
            result: dict[str, Any] = {
                "workspace_id": workspace_id,
                "relative_path": relative_path,
                "size": size,
                "sha256": _file_sha256(path),
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

    def search(
        self,
        workspace_id: str,
        query: str,
        *,
        glob: str,
        literal: bool,
        case_sensitive: bool,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        _page_bounds(limit, offset, 100)
        if not isinstance(query, str) or not query or len(query.encode("utf-8")) > 512:
            raise WorkspaceError("query must contain 1 through 512 UTF-8 bytes")
        _validate_glob(glob)
        with self._workspace_lock(workspace_id):
            _, tree, _ = self._active(workspace_id)
            _validate_tree(tree, self.policy)
            executable = shutil.which("rg")
            if executable is None:
                raise WorkspaceError(
                    "repository search requires ripgrep on the service host"
                )
            argv = [
                executable,
                "--json",
                "--hidden",
                "--no-ignore",
                "--max-columns",
                "1000",
                "--max-columns-preview",
                "--max-filesize",
                str(self.policy.max_file_bytes),
                "--glob",
                glob,
                "--glob",
                "!.git/**",
            ]
            if literal:
                argv.append("--fixed-strings")
            if not case_sensitive:
                argv.append("--ignore-case")
            argv.extend(["--", query, "."])
            output, stderr, returncode, truncated = _capture_process(
                argv, tree, timeout=15, maximum=_SEARCH_CAPTURE_BYTES
            )
            if returncode not in {0, 1} and not truncated:
                detail = stderr.decode("utf-8", "replace").strip()
                raise WorkspaceError(f"repository search failed: {detail}")
            matches = []
            malformed_tail = False
            for raw_line in output.splitlines():
                try:
                    event = json.loads(raw_line)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    malformed_tail = True
                    continue
                if event.get("type") != "match":
                    continue
                data = event["data"]
                path = data["path"].get("text")
                lines = data["lines"].get("text")
                if not isinstance(path, str) or not isinstance(lines, str):
                    continue
                for submatch in data.get("submatches", []):
                    matches.append(
                        {
                            "relative_path": path.removeprefix("./"),
                            "line_number": data.get("line_number"),
                            "start_byte": submatch.get("start"),
                            "end_byte": submatch.get("end"),
                            "line": lines.rstrip("\r\n"),
                        }
                    )
                    if len(matches) >= 10000:
                        truncated = True
                        break
                if len(matches) >= 10000:
                    break
            truncated = truncated or malformed_tail
            items = tuple(matches[offset : offset + limit])
            has_more = offset + len(items) < len(matches)
            return {
                "workspace_id": workspace_id,
                "query": query,
                "glob": glob,
                "literal": literal,
                "case_sensitive": case_sensitive,
                "observed_matches": len(matches),
                "offset": offset,
                "limit": limit,
                "next_offset": offset + len(items) if has_more else None,
                "truncated": truncated,
                "items": list(items),
            }

    def apply_patch(self, workspace_id: str, patch: str) -> dict[str, Any]:
        payload = patch.encode("utf-8")
        if not payload or len(payload) > self.policy.max_patch_bytes:
            raise WorkspaceError("patch is empty or exceeds the configured byte limit")
        _validate_patch(patch)
        with self._workspace_lock(workspace_id):
            _, tree, metadata = self._active(workspace_id)
            candidate = self.temporary / f"patch-{uuid.uuid4().hex}"
            shutil.copytree(tree, candidate)
            try:
                _git_with_input(
                    metadata,
                    candidate,
                    None,
                    payload,
                    "apply",
                    "--check",
                    "--whitespace=nowarn",
                    "-",
                )
                _git_with_input(
                    metadata,
                    candidate,
                    None,
                    payload,
                    "apply",
                    "--whitespace=nowarn",
                    "-",
                )
                _validate_tree(candidate, self.policy)
                self._replace_tree(workspace_id, candidate)
            finally:
                shutil.rmtree(candidate, ignore_errors=True)
            result = self._status_unlocked(workspace_id)
            result["applied_patch_sha256"] = hashlib.sha256(payload).hexdigest()
            return result

    def status(self, workspace_id: str) -> dict[str, Any]:
        with self._workspace_lock(workspace_id):
            self._active(workspace_id)
            return self._status_unlocked(workspace_id)

    def diff(self, workspace_id: str, *, offset: int, limit: int) -> dict[str, Any]:
        _page_bounds(limit, offset, 65536)
        with self._workspace_lock(workspace_id):
            _, tree, metadata = self._active(workspace_id)
            _validate_tree(tree, self.policy)
            index_path = self.temporary / f"index-{uuid.uuid4().hex}"
            try:
                _prepare_index(metadata, tree, index_path)
                payload = _git_bytes(
                    metadata,
                    tree,
                    index_path,
                    "diff",
                    "--cached",
                    "--binary",
                    "--no-ext-diff",
                    "HEAD",
                    "--",
                )
            finally:
                index_path.unlink(missing_ok=True)
            if len(payload) > self.policy.max_patch_bytes:
                raise WorkspaceError(
                    "workspace diff exceeds max_patch_bytes; reduce the change set"
                )
            page = payload[offset : offset + limit]
            result: dict[str, Any] = {
                "workspace_id": workspace_id,
                "size": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "offset": offset,
                "bytes_returned": len(page),
                "next_offset": offset + len(page)
                if offset + len(page) < len(payload)
                else None,
            }
            try:
                result["text"] = page.decode("utf-8")
                result["encoding"] = "utf-8"
            except UnicodeDecodeError:
                result["base64"] = base64.b64encode(page).decode("ascii")
                result["encoding"] = "base64"
            return result

    def run_shell(
        self,
        workspace_id: str,
        script: str,
        *,
        relative_cwd: str,
        timeout_seconds: int,
    ) -> dict[str, Any]:
        script_bytes = script.encode("utf-8")
        if not script_bytes or len(script_bytes) > _MAX_SCRIPT_BYTES or "\0" in script:
            raise WorkspaceError("script must contain 1 through 65536 UTF-8 bytes")
        if (
            not isinstance(timeout_seconds, int)
            or isinstance(timeout_seconds, bool)
            or not 1 <= timeout_seconds <= self.policy.command_timeout_seconds
        ):
            raise WorkspaceError(
                "timeout_seconds exceeds the configured workspace command limit"
            )
        with self._workspace_lock(workspace_id):
            _, tree, metadata = self._active(workspace_id)
            cwd = _safe_path(tree, relative_cwd, require_directory=True)
            relative_cwd = cwd.relative_to(tree).as_posix()
            if relative_cwd == ".":
                relative_cwd = ""
            command_id = f"command:{uuid.uuid4().hex}"
            directory = self._command_directory(workspace_id, command_id)
            directory.mkdir(parents=True, mode=0o700)
            started = _now()
            record = {
                "schema_version": WORKSPACE_SCHEMA_VERSION,
                "command_id": command_id,
                "workspace_id": workspace_id,
                "script_sha256": hashlib.sha256(script_bytes).hexdigest(),
                "relative_cwd": relative_cwd or ".",
                "timeout_seconds": timeout_seconds,
                "started_at": _format_time(started),
                "finished_at": None,
                "state": "running",
                "exit_code": None,
                "timed_out": False,
                "workspace_committed": False,
                "workspace_validation_error": None,
                "stdout_captured_bytes": 0,
                "stdout_observed_bytes": 0,
                "stderr_captured_bytes": 0,
                "stderr_observed_bytes": 0,
                "output_truncated": False,
            }
            _write_json(directory / "record.json", record)
            try:
                outcome = self._execute_shell(
                    tree,
                    metadata,
                    script,
                    relative_cwd,
                    timeout_seconds,
                    directory,
                )
            except (OSError, WorkspaceError) as error:
                record["state"] = "interrupted"
                record["finished_at"] = _format_time(_now())
                record["workspace_validation_error"] = str(error)
                _write_json(directory / "record.json", record)
                raise WorkspaceError(
                    f"workspace command {command_id} could not complete: {error}"
                ) from error
            candidate = outcome.pop("candidate", None)
            validation_error = outcome.pop("validation_error", None)
            if candidate is not None:
                try:
                    _validate_tree(candidate, self.policy)
                    self._replace_tree(workspace_id, candidate)
                    record["workspace_committed"] = True
                except (OSError, WorkspaceError) as error:
                    validation_error = str(error)
                finally:
                    shutil.rmtree(candidate, ignore_errors=True)
            record.update(outcome)
            record["workspace_validation_error"] = validation_error
            record["state"] = "completed" if not record["timed_out"] else "timed-out"
            record["finished_at"] = _format_time(_now())
            _write_json(directory / "record.json", record)
            return self._public_command(record)

    def command_output(
        self,
        workspace_id: str,
        command_id: str,
        *,
        stream: str,
        offset: int,
        limit: int,
    ) -> dict[str, Any]:
        _page_bounds(limit, offset, 65536)
        if stream not in {"stdout", "stderr"}:
            raise WorkspaceError("stream must be stdout or stderr")
        with self._workspace_lock(workspace_id):
            self._active(workspace_id)
            directory = self._command_directory(workspace_id, command_id)
            record = _read_json(directory / "record.json", "command")
            _validate_command_record(record)
            if record.get("workspace_id") != workspace_id:
                raise WorkspaceError("command does not belong to this workspace")
            if record.get("state") == "running":
                record["state"] = "interrupted"
                record["finished_at"] = _format_time(_now())
                record["workspace_validation_error"] = (
                    "service process ended before the command transaction completed"
                )
                _write_json(directory / "record.json", record)
            path = directory / f"{stream}.bin"
            size = path.stat().st_size if path.exists() else 0
            with path.open("rb") if path.exists() else open(os.devnull, "rb") as handle:
                handle.seek(offset)
                payload = handle.read(limit)
            result: dict[str, Any] = {
                "workspace_id": workspace_id,
                "command": self._public_command(record),
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

    def discard(self, workspace_id: str) -> dict[str, Any]:
        self._ensure_layout()
        with self._global_lock():
            with self._workspace_lock(workspace_id):
                record = self._load_record(workspace_id)
                if record["state"] != "discarded":
                    record["state"] = "discarded"
                    record["discarded_at"] = _format_time(_now())
                    _write_json(self._record_path(workspace_id), record)
                self._remove_payload(workspace_id)
                return self._public(record)

    def _execute_shell(
        self,
        tree: Path,
        metadata: Path,
        script: str,
        relative_cwd: str,
        timeout_seconds: int,
        directory: Path,
    ) -> dict[str, Any]:
        bwrap = shutil.which("bwrap")
        prlimit = shutil.which("prlimit")
        nice = shutil.which("nice")
        if not bwrap or not prlimit or not nice:
            raise WorkspaceError("workspace shell requires bwrap, prlimit, and nice")

        stdout_read, stdout_write = os.pipe()
        stderr_read, stderr_write = os.pipe()
        archive_read, archive_write = os.pipe()
        static = f"""
set -eu
cp -a -- /source/. /workspace/
set +e
(
  exec {archive_write}>&-
  cd -- /workspace/{shlex.quote(relative_cwd)}
  /bin/bash --noprofile --norc -lc "$1"
) >&{stdout_write} 2>&{stderr_write}
command_status=$?
set -e
rm -rf -- /workspace/.git
tar --format=pax --numeric-owner -C /workspace -cf /dev/fd/{archive_write} .
exit "$command_status"
""".strip()
        tmpfs_bytes = self.policy.max_snapshot_bytes + _ARCHIVE_OVERHEAD_BYTES
        argv = [
            prlimit,
            f"--as={2 * 1024 * 1024 * 1024}",
            f"--cpu={timeout_seconds + 5}",
            f"--fsize={self.policy.max_file_bytes}",
            f"--nproc={_workspace_nproc_limit()}",
            "--nofile=256",
            "--",
            nice,
            "-n",
            "15",
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
            "--dir",
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
            "--ro-bind",
            str(tree),
            "/source",
            "--ro-bind",
            str(metadata),
            "/metadata",
            "--size",
            str(tmpfs_bytes),
            "--tmpfs",
            "/workspace",
            "--symlink",
            "/metadata",
            "/workspace/.git",
            "--setenv",
            "HOME",
            "/tmp/home",
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
            "GIT_CONFIG_NOSYSTEM",
            "1",
            "--setenv",
            "GIT_TERMINAL_PROMPT",
            "0",
            "--setenv",
            "GIT_OPTIONAL_LOCKS",
            "0",
            "--setenv",
            "PAGER",
            "cat",
            "/bin/bash",
            "--noprofile",
            "--norc",
            "-c",
            static,
            "factory-workspace",
            script,
        ]
        try:
            process = subprocess.Popen(
                argv,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=stderr_write,
                pass_fds=(stdout_write, stderr_write, archive_write),
                start_new_session=True,
            )
        except OSError as error:
            os.close(stdout_read)
            os.close(stderr_read)
            os.close(archive_read)
            raise WorkspaceError(
                "cannot start the isolated workspace process"
            ) from error
        finally:
            os.close(stdout_write)
            os.close(stderr_write)
            os.close(archive_write)

        output_paths = {
            stdout_read: directory / "stdout.bin",
            stderr_read: directory / "stderr.bin",
        }
        handles = {fd: path.open("wb") for fd, path in output_paths.items()}
        archive_path = self.temporary / f"command-{uuid.uuid4().hex}.tar"
        archive_handle = archive_path.open("wb")
        selector = selectors.DefaultSelector()
        for descriptor in (stdout_read, stderr_read, archive_read):
            os.set_blocking(descriptor, False)
            selector.register(descriptor, selectors.EVENT_READ)
        observed = {stdout_read: 0, stderr_read: 0}
        captured = {stdout_read: 0, stderr_read: 0}
        output_total = 0
        archive_bytes = 0
        archive_limit = self.policy.max_snapshot_bytes + _ARCHIVE_OVERHEAD_BYTES
        timed_out = False
        archive_overflow = False
        deadline = time.monotonic() + timeout_seconds
        open_descriptors = {stdout_read, stderr_read, archive_read}
        try:
            while selector.get_map():
                if process.poll() is None and time.monotonic() >= deadline:
                    timed_out = True
                    os.killpg(process.pid, signal.SIGKILL)
                events = selector.select(timeout=0.1)
                for key, _ in events:
                    descriptor = key.fd
                    try:
                        block = os.read(descriptor, 65536)
                    except BlockingIOError:
                        continue
                    if not block:
                        selector.unregister(descriptor)
                        os.close(descriptor)
                        open_descriptors.discard(descriptor)
                        continue
                    if descriptor == archive_read:
                        archive_bytes += len(block)
                        if archive_bytes <= archive_limit:
                            archive_handle.write(block)
                        else:
                            archive_overflow = True
                            if process.poll() is None:
                                os.killpg(process.pid, signal.SIGKILL)
                        continue
                    observed[descriptor] += len(block)
                    remaining = self.policy.max_command_output_bytes - output_total
                    if remaining > 0:
                        written = block[:remaining]
                        handles[descriptor].write(written)
                        captured[descriptor] += len(written)
                        output_total += len(written)
            returncode = process.wait()
        except Exception:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            archive_path.unlink(missing_ok=True)
            raise
        finally:
            selector.close()
            for descriptor in open_descriptors:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
            for handle in handles.values():
                handle.close()
            archive_handle.close()

        candidate = None
        validation_error = None
        if timed_out:
            validation_error = "command timed out; its partial filesystem was discarded"
        elif archive_overflow:
            validation_error = "workspace archive exceeded its configured bound"
        elif archive_bytes == 0:
            validation_error = "sandbox ended without a complete workspace snapshot"
        else:
            candidate = self.temporary / f"result-{uuid.uuid4().hex}"
            try:
                _extract_archive(archive_path, candidate, self.policy)
            except (OSError, tarfile.TarError, WorkspaceError) as error:
                shutil.rmtree(candidate, ignore_errors=True)
                candidate = None
                validation_error = str(error)
        archive_path.unlink(missing_ok=True)
        return {
            "candidate": candidate,
            "validation_error": validation_error,
            "exit_code": returncode,
            "timed_out": timed_out,
            "stdout_captured_bytes": captured[stdout_read],
            "stdout_observed_bytes": observed[stdout_read],
            "stderr_captured_bytes": captured[stderr_read],
            "stderr_observed_bytes": observed[stderr_read],
            "output_truncated": (
                observed[stdout_read] + observed[stderr_read]
                > self.policy.max_command_output_bytes
            ),
        }

    def _status_unlocked(self, workspace_id: str) -> dict[str, Any]:
        record, tree, metadata = self._active(workspace_id)
        files, size, _ = _validate_tree(tree, self.policy)
        index_path = self.temporary / f"index-{uuid.uuid4().hex}"
        try:
            _prepare_index(metadata, tree, index_path)
            raw = _git_bytes(
                metadata,
                tree,
                index_path,
                "diff",
                "--cached",
                "--name-status",
                "-z",
                "HEAD",
                "--",
            )
        finally:
            index_path.unlink(missing_ok=True)
        parts = [part.decode("utf-8", "replace") for part in raw.split(b"\0") if part]
        entries = []
        cursor = 0
        while cursor < len(parts):
            status_code = parts[cursor]
            cursor += 1
            path_count = 2 if status_code.startswith(("R", "C")) else 1
            if cursor + path_count > len(parts):
                raise WorkspaceError("workspace Git status emitted malformed name data")
            paths = parts[cursor : cursor + path_count]
            cursor += path_count
            entry: dict[str, Any] = {"status": status_code, "path": paths[-1]}
            if path_count == 2:
                entry["source_path"] = paths[0]
            entries.append(entry)
        return {
            "workspace_id": workspace_id,
            "state": record["state"],
            "source_git_commit": record["source_git_commit"],
            "file_count": len(files),
            "bytes": size,
            "changed_entries": entries,
            "changed_entry_count": len(entries),
        }

    def _replace_tree(self, workspace_id: str, candidate: Path) -> None:
        suffix = _workspace_suffix(workspace_id)
        tree = self.trees / suffix / "tree"
        backup = self.temporary / f"backup-{suffix}-{uuid.uuid4().hex}"
        os.replace(tree, backup)
        try:
            os.replace(candidate, tree)
        except Exception:
            os.replace(backup, tree)
            raise
        shutil.rmtree(backup, ignore_errors=True)

    def _active(self, workspace_id: str) -> tuple[dict[str, Any], Path, Path]:
        record = self._expire(self._load_record(workspace_id))
        if record["state"] != "active":
            raise WorkspaceError(
                f"workspace is {record['state']}; create a new workspace"
            )
        registration = self.config.repository(record["repository_id"])
        if (
            canonical_sha256(registration.identity_dict())
            != record["registration_sha256"]
        ):
            raise WorkspaceError(
                "repository registration changed after workspace creation"
            )
        suffix = _workspace_suffix(workspace_id)
        tree = self.trees / suffix / "tree"
        metadata = self.trees / suffix / "git"
        if not tree.is_dir() or not metadata.is_dir():
            raise WorkspaceError("workspace payload is missing or incomplete")
        return record, tree, metadata

    def _expire(self, record: dict[str, Any]) -> dict[str, Any]:
        if self._effective_state(record) != "expired":
            return record
        if record["state"] == "active":
            record["state"] = "expired"
            record["expired_at"] = _format_time(_now())
            _write_json(self._record_path(record["workspace_id"]), record)
            self._remove_payload(record["workspace_id"])
        return record

    def _cleanup_expired(self) -> None:
        for record in self._all_records():
            with self._workspace_lock(record["workspace_id"]):
                self._expire(self._load_record(record["workspace_id"]))

    def _remove_payload(self, workspace_id: str) -> None:
        suffix = _workspace_suffix(workspace_id)
        shutil.rmtree(self.trees / suffix, ignore_errors=True)
        shutil.rmtree(self.commands / suffix, ignore_errors=True)

    def _public(self, record: dict[str, Any]) -> dict[str, Any]:
        state = self._effective_state(record)
        result = {
            key: record[key]
            for key in (
                "workspace_id",
                "repository_id",
                "created_at",
                "expires_at",
                "source_mode",
                "source_git_commit",
                "source_git_tree",
                "source_worktree_dirty_observed",
                "snapshot_file_count",
                "snapshot_bytes",
            )
        }
        result["state"] = state
        result["isolation"] = "bubblewrap-source-only-v1"
        if state == "active":
            suffix = _workspace_suffix(record["workspace_id"])
            command_root = self.commands / suffix
            command_ids = []
            if command_root.is_dir():
                for path in sorted(command_root.glob("*/record.json")):
                    try:
                        command = _read_json(path, "command")
                        _validate_command_record(command)
                    except WorkspaceError:
                        continue
                    if command.get("workspace_id") == record["workspace_id"]:
                        command_ids.append(command.get("command_id"))
            result["recent_command_ids"] = command_ids[-20:]
        else:
            result["recent_command_ids"] = []
        return result

    @staticmethod
    def _public_command(record: dict[str, Any]) -> dict[str, Any]:
        return {
            key: record.get(key)
            for key in (
                "command_id",
                "workspace_id",
                "script_sha256",
                "relative_cwd",
                "timeout_seconds",
                "started_at",
                "finished_at",
                "state",
                "exit_code",
                "timed_out",
                "workspace_committed",
                "workspace_validation_error",
                "stdout_captured_bytes",
                "stdout_observed_bytes",
                "stderr_captured_bytes",
                "stderr_observed_bytes",
                "output_truncated",
            )
        }

    def _effective_state(self, record: dict[str, Any]) -> str:
        if record["state"] != "active":
            return record["state"]
        return "expired" if _parse_time(record["expires_at"]) <= _now() else "active"

    def _load_record(self, workspace_id: str) -> dict[str, Any]:
        record = _read_json(self._record_path(workspace_id), "workspace")
        _validate_workspace_record(record)
        if record.get("workspace_id") != workspace_id:
            raise WorkspaceError("workspace record identity mismatch")
        return record

    def _all_records(self) -> Iterator[dict[str, Any]]:
        if not self.records.is_dir():
            return
        for path in sorted(self.records.glob("*.json")):
            record = _read_json(path, "workspace")
            _validate_workspace_record(record)
            yield record

    def _record_path(self, workspace_id: str) -> Path:
        return self.records / f"{_workspace_suffix(workspace_id)}.json"

    def _command_directory(self, workspace_id: str, command_id: str) -> Path:
        return (
            self.commands
            / _workspace_suffix(workspace_id)
            / _command_suffix(command_id)
        )

    def _require_enabled(self) -> None:
        if not self.policy.enabled:
            raise WorkspaceError("workspace provider is disabled by operator policy")

    def _ensure_layout(self) -> None:
        self._require_enabled()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.root.resolve(strict=True) != self.root:
            raise WorkspaceError("workspace root changed after configuration loading")
        os.chmod(self.root, 0o700)
        for path in (
            self.records,
            self.trees,
            self.commands,
            self.locks,
            self.temporary,
        ):
            path.mkdir(exist_ok=True, mode=0o700)
            if path.resolve(strict=True) != path or not path.is_dir():
                raise WorkspaceError("workspace storage layout contains an unsafe link")
            os.chmod(path, 0o700)

    @contextmanager
    def _global_lock(self) -> Iterator[None]:
        self._ensure_layout()
        with _file_lock(self.root / "workspace.lock"):
            yield

    @contextmanager
    def _workspace_lock(self, workspace_id: str) -> Iterator[None]:
        self._ensure_layout()
        with _file_lock(self.locks / f"{_workspace_suffix(workspace_id)}.lock"):
            yield


def _source_identity(repository: Path) -> dict[str, Any]:
    root = repository.resolve(strict=True)
    top = Path(_host_git(root, "rev-parse", "--show-toplevel")).resolve(strict=True)
    if top != root:
        raise WorkspaceError(
            "workspace snapshots currently require a Git worktree root"
        )
    commit = _host_git(root, "rev-parse", "HEAD")
    return {
        "git_commit": commit,
        "git_tree": _host_git(root, "rev-parse", f"{commit}^{{tree}}"),
        "dirty": bool(
            _host_git_bytes(
                root, "status", "--porcelain=v1", "-z", "--untracked-files=all"
            )
        ),
    }


def _validate_committed_snapshot(
    repository: Path,
    commit: str,
    policy: WorkspacePolicy,
) -> dict[str, int]:
    raw = _host_git_bytes(
        repository,
        "ls-tree",
        "-rlz",
        "--full-tree",
        commit,
    )
    file_count = 0
    total_bytes = 0
    seen: set[str] = set()
    for entry in raw.split(b"\0"):
        if not entry:
            continue
        try:
            metadata, raw_path = entry.split(b"\t", 1)
            mode, kind, _object_id, raw_size = metadata.split()
            relative_path = raw_path.decode("utf-8")
        except (UnicodeDecodeError, ValueError) as error:
            raise WorkspaceError(
                "committed Git tree contains malformed or non-UTF-8 entries"
            ) from error
        _validate_relative(relative_path)
        if relative_path in seen:
            raise WorkspaceError("committed Git tree contains duplicate paths")
        seen.add(relative_path)
        if kind != b"blob" or mode not in {b"100644", b"100755"}:
            raise WorkspaceError(
                "workspaces require regular tracked files; symlinks and Git links are excluded"
            )
        try:
            size = int(raw_size)
        except ValueError as error:
            raise WorkspaceError(
                "committed Git tree contains a malformed file size"
            ) from error
        if size < 0 or size > policy.max_file_bytes:
            raise WorkspaceError("committed Git tree contains an oversized file")
        file_count += 1
        total_bytes += size
        if file_count > policy.max_snapshot_files:
            raise WorkspaceError("workspace snapshot file limit exceeded")
        if total_bytes > policy.max_snapshot_bytes:
            raise WorkspaceError("workspace snapshot byte limit exceeded")
    return {"file_count": file_count, "bytes": total_bytes}


def _workspace_nproc_limit() -> int:
    """Reserve bounded child headroom without counting host tasks as sandbox tasks."""

    uid = os.getuid()
    observed_tasks = 0
    try:
        processes = tuple(Path("/proc").iterdir())
    except OSError as error:
        raise WorkspaceError("cannot inspect operator task usage") from error
    for process in processes:
        if not process.name.isdigit():
            continue
        try:
            if process.stat().st_uid != uid:
                continue
            observed_tasks += sum(1 for _ in (process / "task").iterdir())
        except OSError:
            continue
    requested = observed_tasks + _WORKSPACE_PROCESS_HEADROOM
    _, hard = resource.getrlimit(resource.RLIMIT_NPROC)
    if hard != resource.RLIM_INFINITY:
        requested = min(requested, hard)
    if requested <= observed_tasks:
        raise WorkspaceError("operator process limit leaves no workspace task headroom")
    return requested


def _git_archive(repository: Path, commit: str, destination: Path) -> None:
    with destination.open("wb") as output:
        try:
            subprocess.run(
                ["git", "-C", str(repository), "archive", "--format=tar", commit],
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=subprocess.PIPE,
                check=True,
                timeout=60,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
            detail = getattr(error, "stderr", b"") or b""
            raise WorkspaceError(
                "cannot snapshot committed source: "
                + detail.decode("utf-8", "replace").strip()
            ) from error


def _extract_archive(
    archive: Path, destination: Path, policy: WorkspacePolicy
) -> dict[str, int]:
    destination.mkdir(mode=0o700)
    file_count = 0
    total_bytes = 0
    seen: set[str] = set()
    try:
        with tarfile.open(archive, "r:*") as bundle:
            members = bundle.getmembers()
            if len(members) > policy.max_snapshot_files * 2 + 1000:
                raise WorkspaceError("workspace archive contains too many members")
            for member in members:
                name = member.name.removeprefix("./")
                if not name or name == ".":
                    continue
                _validate_relative(name)
                if name in seen:
                    raise WorkspaceError("workspace archive contains duplicate paths")
                seen.add(name)
                if member.isdir():
                    continue
                if not member.isfile():
                    raise WorkspaceError(
                        "workspace archives permit regular files and directories only"
                    )
                if member.size > policy.max_file_bytes:
                    raise WorkspaceError("workspace archive contains an oversized file")
                file_count += 1
                total_bytes += member.size
                if file_count > policy.max_snapshot_files:
                    raise WorkspaceError("workspace snapshot file limit exceeded")
                if total_bytes > policy.max_snapshot_bytes:
                    raise WorkspaceError("workspace snapshot byte limit exceeded")
            for member in members:
                name = member.name.removeprefix("./")
                if not name or name == ".":
                    continue
                target = destination.joinpath(*PurePosixPath(name).parts)
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True, mode=0o755)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
                source = bundle.extractfile(member)
                if source is None:
                    raise WorkspaceError("workspace archive file payload is missing")
                with target.open("xb") as output:
                    shutil.copyfileobj(source, output, length=1024 * 1024)
                os.chmod(target, 0o755 if member.mode & 0o111 else 0o644)
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise
    return {"file_count": file_count, "bytes": total_bytes}


def _initialize_baseline(tree: Path, metadata: Path) -> None:
    env = _git_environment(None)
    _run_git(metadata, tree, None, "init", env=env)
    _run_git(metadata, tree, None, "config", "core.worktree", "/workspace", env=env)
    _run_git(metadata, tree, None, "config", "user.name", "Factory Workspace", env=env)
    _run_git(
        metadata,
        tree,
        None,
        "config",
        "user.email",
        "factory-workspace@example.invalid",
        env=env,
    )
    _run_git(metadata, tree, None, "add", "-A", "--", ".", env=env)
    _run_git(
        metadata, tree, None, "commit", "--allow-empty", "-q", "-m", "baseline", env=env
    )


def _prepare_index(metadata: Path, tree: Path, index_path: Path) -> None:
    _run_git(metadata, tree, index_path, "read-tree", "HEAD")
    _run_git(metadata, tree, index_path, "add", "-A", "--", ".")


def _run_git(
    metadata: Path,
    tree: Path,
    index_path: Path | None,
    *args: str,
    env: dict[str, str] | None = None,
) -> None:
    _git_bytes(metadata, tree, index_path, *args, env=env)


def _git_bytes(
    metadata: Path,
    tree: Path,
    index_path: Path | None,
    *args: str,
    env: dict[str, str] | None = None,
) -> bytes:
    command = ["git", f"--git-dir={metadata}", f"--work-tree={tree}", *args]
    try:
        return subprocess.check_output(
            command,
            cwd=tree,
            stderr=subprocess.PIPE,
            env=env or _git_environment(index_path),
        )
    except subprocess.CalledProcessError as error:
        detail = error.stderr.decode("utf-8", "replace").strip()
        raise WorkspaceError(f"workspace Git operation failed: {detail}") from error


def _git_with_input(
    metadata: Path,
    tree: Path,
    index_path: Path | None,
    payload: bytes,
    *args: str,
) -> None:
    try:
        subprocess.run(
            ["git", f"--git-dir={metadata}", f"--work-tree={tree}", *args],
            cwd=tree,
            input=payload,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=_git_environment(index_path),
            timeout=30,
            check=True,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        detail = getattr(error, "stderr", b"") or b""
        raise WorkspaceError(
            "workspace patch was rejected: " + detail.decode("utf-8", "replace").strip()
        ) from error


def _git_environment(index_path: Path | None) -> dict[str, str]:
    result = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": os.devnull,
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "TZ": "UTC",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_AUTHOR_NAME": "Factory Workspace",
        "GIT_AUTHOR_EMAIL": "factory-workspace@example.invalid",
        "GIT_COMMITTER_NAME": "Factory Workspace",
        "GIT_COMMITTER_EMAIL": "factory-workspace@example.invalid",
    }
    if index_path is not None:
        result["GIT_INDEX_FILE"] = str(index_path)
    return result


def _validate_tree(
    tree: Path, policy: WorkspacePolicy
) -> tuple[tuple[str, ...], int, int]:
    files = []
    total = 0
    directories = 0
    for path in sorted(tree.rglob("*")):
        relative = path.relative_to(tree).as_posix()
        if ".git" in PurePosixPath(relative).parts:
            raise WorkspaceError("workspace tree must not contain Git control files")
        mode = path.lstat().st_mode
        if stat.S_ISDIR(mode):
            directories += 1
            continue
        if not stat.S_ISREG(mode):
            raise WorkspaceError(
                "workspace tree permits regular files and directories only"
            )
        size = path.stat().st_size
        if size > policy.max_file_bytes:
            raise WorkspaceError("workspace tree contains an oversized file")
        files.append(relative)
        total += size
        if len(files) > policy.max_snapshot_files:
            raise WorkspaceError("workspace snapshot file limit exceeded")
        if total > policy.max_snapshot_bytes:
            raise WorkspaceError("workspace snapshot byte limit exceeded")
    return tuple(files), total, directories


def _safe_path(
    root: Path,
    relative: str,
    *,
    require_file: bool = False,
    require_directory: bool = False,
) -> Path:
    if relative == "." and require_directory:
        return root
    _validate_relative(relative)
    candidate = root.joinpath(*PurePosixPath(relative).parts)
    current = root
    for part in PurePosixPath(relative).parts:
        current = current / part
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError as error:
            raise WorkspaceError(
                "relative path does not exist in this workspace"
            ) from error
        if stat.S_ISLNK(mode):
            raise WorkspaceError("workspace paths must not traverse symlinks")
    if require_file and not candidate.is_file():
        raise WorkspaceError("relative path is not a regular file")
    if require_directory and not candidate.is_dir():
        raise WorkspaceError("relative_cwd is not a directory")
    return candidate


def _validate_relative(value: str) -> None:
    try:
        encoded_size = len(value.encode("utf-8")) if isinstance(value, str) else 0
    except UnicodeEncodeError as error:
        raise WorkspaceError("workspace paths must be valid UTF-8") from error
    if (
        not isinstance(value, str)
        or not value
        or encoded_size > 1024
        or "\0" in value
        or "\\" in value
    ):
        raise WorkspaceError("workspace paths must be bounded POSIX-relative paths")
    path = PurePosixPath(value)
    if path.is_absolute() or any(
        part in {"", ".", "..", ".git"} for part in path.parts
    ):
        raise WorkspaceError("workspace path escapes or addresses Git control data")


def _validate_glob(value: str) -> None:
    if not isinstance(value, str) or not value or len(value.encode("utf-8")) > 256:
        raise WorkspaceError("glob must contain 1 through 256 UTF-8 bytes")
    if (
        "\0" in value
        or "\\" in value
        or value.startswith("/")
        or ".." in PurePosixPath(value).parts
    ):
        raise WorkspaceError("glob must remain within the workspace")


def _validate_patch(patch: str) -> None:
    if "\0" in patch or "GIT binary patch" in patch:
        raise WorkspaceError("patch must be a text-only unified Git diff")
    if re.search(r"(?:old|new|deleted) (?:file )?mode (?:120000|160000)", patch):
        raise WorkspaceError("patch cannot introduce symlinks or Git links")
    if re.search(r"^(?:rename|copy) (?:from|to) ", patch, re.MULTILINE):
        raise WorkspaceError(
            "patch rename/copy metadata is not supported; use delete/add"
        )
    observed = 0
    for line in patch.splitlines():
        paths: tuple[str, ...] = ()
        if line.startswith("diff --git "):
            try:
                fields = shlex.split(line)
            except ValueError as error:
                raise WorkspaceError("patch contains malformed quoted paths") from error
            if len(fields) != 4:
                raise WorkspaceError("patch contains an ambiguous diff header")
            paths = (fields[2], fields[3])
        elif line.startswith("--- ") or line.startswith("+++ "):
            raw = line[4:].split("\t", 1)[0]
            paths = (raw,)
        for raw in paths:
            if raw == "/dev/null":
                continue
            if raw.startswith(("a/", "b/")):
                raw = raw[2:]
            _validate_relative(raw)
            observed += 1
    if observed < 2:
        raise WorkspaceError("patch does not contain a recognized unified diff")


def _capture_process(
    argv: list[str], cwd: Path, *, timeout: int, maximum: int
) -> tuple[bytes, bytes, int, bool]:
    process = subprocess.Popen(
        argv,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    assert process.stdout is not None and process.stderr is not None
    selector = selectors.DefaultSelector()
    descriptors = {
        process.stdout.fileno(): bytearray(),
        process.stderr.fileno(): bytearray(),
    }
    for descriptor in descriptors:
        os.set_blocking(descriptor, False)
        selector.register(descriptor, selectors.EVENT_READ)
    truncated = False
    deadline = time.monotonic() + timeout
    while selector.get_map():
        if process.poll() is None and time.monotonic() >= deadline:
            os.killpg(process.pid, signal.SIGKILL)
            truncated = True
        for key, _ in selector.select(0.1):
            block = os.read(key.fd, 65536)
            if not block:
                selector.unregister(key.fd)
                continue
            target = descriptors[key.fd]
            remaining = maximum - sum(len(item) for item in descriptors.values())
            if remaining > 0:
                target.extend(block[:remaining])
            if len(block) > remaining:
                truncated = True
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGKILL)
    stdout_fd = process.stdout.fileno()
    stderr_fd = process.stderr.fileno()
    result = (
        bytes(descriptors[stdout_fd]),
        bytes(descriptors[stderr_fd]),
        process.wait(),
        truncated,
    )
    process.stdout.close()
    process.stderr.close()
    selector.close()
    return result


def _host_git(cwd: Path, *args: str) -> str:
    return _host_git_bytes(cwd, *args).decode("ascii").strip()


def _host_git_bytes(cwd: Path, *args: str) -> bytes:
    try:
        return subprocess.check_output(
            ["git", "-C", str(cwd), *args], stderr=subprocess.PIPE, timeout=60
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        detail = getattr(error, "stderr", b"") or b""
        raise WorkspaceError(
            "registered repository Git operation failed: "
            + detail.decode("utf-8", "replace").strip()
        ) from error


@contextmanager
def _file_lock(path: Path) -> Iterator[None]:
    with path.open("a+b") as handle:
        os.chmod(path, 0o600)
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _read_json(path: Path, noun: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise WorkspaceError(f"unknown {noun} capability") from error
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise WorkspaceError(f"cannot load {noun} record") from error
    if not isinstance(value, dict):
        raise WorkspaceError(f"{noun} record must be an object")
    return value


def _validate_workspace_record(value: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "workspace_id",
        "repository_id",
        "registration_sha256",
        "idempotency_key_sha256",
        "request_sha256",
        "created_at",
        "expires_at",
        "state",
        "source_mode",
        "source_git_commit",
        "source_git_tree",
        "source_worktree_dirty_observed",
        "snapshot_file_count",
        "snapshot_bytes",
    }
    optional = {"expired_at", "discarded_at"}
    if set(value) - required - optional or required - set(value):
        raise WorkspaceError("workspace record fields differ from schema")
    if value["schema_version"] != WORKSPACE_SCHEMA_VERSION:
        raise WorkspaceError("unsupported workspace record schema")
    _workspace_suffix(value["workspace_id"])
    if value["state"] not in {"active", "expired", "discarded"}:
        raise WorkspaceError("workspace record contains an invalid state")
    if value["source_mode"] != "committed-head":
        raise WorkspaceError("workspace record contains an unsupported source mode")
    for field, length in (
        ("registration_sha256", 64),
        ("idempotency_key_sha256", 64),
        ("request_sha256", 64),
        ("source_git_commit", 40),
        ("source_git_tree", 40),
    ):
        if not isinstance(value[field], str) or not re.fullmatch(
            rf"[0-9a-f]{{{length}}}", value[field]
        ):
            raise WorkspaceError(f"workspace record contains an invalid {field}")
    if not isinstance(value["repository_id"], str) or not value["repository_id"]:
        raise WorkspaceError("workspace record contains an invalid repository ID")
    if not isinstance(value["source_worktree_dirty_observed"], bool):
        raise WorkspaceError("workspace record dirty observation must be Boolean")
    for field in ("snapshot_file_count", "snapshot_bytes"):
        if (
            not isinstance(value[field], int)
            or isinstance(value[field], bool)
            or value[field] < 0
        ):
            raise WorkspaceError(f"workspace record contains an invalid {field}")
    for field in ("created_at", "expires_at", "expired_at", "discarded_at"):
        if field in value:
            _parse_time(value[field])


def _validate_command_record(value: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "command_id",
        "workspace_id",
        "script_sha256",
        "relative_cwd",
        "timeout_seconds",
        "started_at",
        "finished_at",
        "state",
        "exit_code",
        "timed_out",
        "workspace_committed",
        "workspace_validation_error",
        "stdout_captured_bytes",
        "stdout_observed_bytes",
        "stderr_captured_bytes",
        "stderr_observed_bytes",
        "output_truncated",
    }
    if set(value) != required:
        raise WorkspaceError("command record fields differ from schema")
    if value["schema_version"] != WORKSPACE_SCHEMA_VERSION:
        raise WorkspaceError("unsupported command record schema")
    _command_suffix(value["command_id"])
    _workspace_suffix(value["workspace_id"])
    if not re.fullmatch(r"[0-9a-f]{64}", value["script_sha256"]):
        raise WorkspaceError("command record contains an invalid script digest")
    if value["state"] not in {"running", "completed", "timed-out", "interrupted"}:
        raise WorkspaceError("command record contains an invalid state")
    if value["relative_cwd"] != ".":
        _validate_relative(value["relative_cwd"])
    if (
        not isinstance(value["timeout_seconds"], int)
        or isinstance(value["timeout_seconds"], bool)
        or value["timeout_seconds"] <= 0
    ):
        raise WorkspaceError("command record contains an invalid timeout")
    _parse_time(value["started_at"])
    if value["finished_at"] is not None:
        _parse_time(value["finished_at"])
    if value["state"] == "running" and value["finished_at"] is not None:
        raise WorkspaceError("running command record cannot have a finish time")
    if value["state"] != "running" and value["finished_at"] is None:
        raise WorkspaceError("terminal command record must have a finish time")
    if value["exit_code"] is not None and (
        not isinstance(value["exit_code"], int) or isinstance(value["exit_code"], bool)
    ):
        raise WorkspaceError("command record contains an invalid exit code")
    if value["workspace_validation_error"] is not None and not isinstance(
        value["workspace_validation_error"], str
    ):
        raise WorkspaceError("command record contains an invalid validation error")
    for field in (
        "timed_out",
        "workspace_committed",
        "output_truncated",
    ):
        if not isinstance(value[field], bool):
            raise WorkspaceError(f"command record contains an invalid {field}")
    for field in (
        "stdout_captured_bytes",
        "stdout_observed_bytes",
        "stderr_captured_bytes",
        "stderr_observed_bytes",
    ):
        if (
            not isinstance(value[field], int)
            or isinstance(value[field], bool)
            or value[field] < 0
        ):
            raise WorkspaceError(f"command record contains an invalid {field}")
    if (
        value["stdout_captured_bytes"] > value["stdout_observed_bytes"]
        or value["stderr_captured_bytes"] > value["stderr_observed_bytes"]
    ):
        raise WorkspaceError("command record captured bytes exceed observed bytes")


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _workspace_suffix(workspace_id: str) -> str:
    match = (
        _WORKSPACE_ID.fullmatch(workspace_id) if isinstance(workspace_id, str) else None
    )
    if match is None:
        raise WorkspaceError("invalid workspace capability")
    return match.group(1)


def _validate_idempotency_key(value: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", value
    ):
        raise WorkspaceError("idempotency key must be a normalized 1-128 byte token")


def _command_suffix(command_id: str) -> str:
    match = _COMMAND_ID.fullmatch(command_id) if isinstance(command_id, str) else None
    if match is None:
        raise WorkspaceError("invalid command capability")
    return match.group(1)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _format_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as error:
        raise WorkspaceError(
            "workspace record contains an invalid timestamp"
        ) from error
    if parsed.tzinfo is None:
        raise WorkspaceError("workspace timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def _page_bounds(limit: int, offset: int, maximum: int) -> None:
    if (
        not isinstance(limit, int)
        or isinstance(limit, bool)
        or not 1 <= limit <= maximum
    ):
        raise WorkspaceError(f"limit must be an integer from 1 through {maximum}")
    if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
        raise WorkspaceError("offset must be a non-negative integer")


def _page(
    total: int, offset: int, limit: int, items: tuple[Any, ...]
) -> dict[str, Any]:
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "next_offset": offset + len(items) if offset + len(items) < total else None,
        "items": list(items),
    }
