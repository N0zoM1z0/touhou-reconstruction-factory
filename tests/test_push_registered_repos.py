from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/push-registered-repos.py"
spec = importlib.util.spec_from_file_location("push_registered_repos", SCRIPT)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class PushRegisteredRepositoriesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def git(self, path: Path, *arguments: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(path), *arguments], capture_output=True, text=True, check=True
        )
        return result.stdout.strip()

    def repository(self, name: str) -> tuple[Path, Path]:
        remote, worktree = self.root / (name + " remote.git"), self.root / (name + " worktree")
        remote.mkdir()
        self.git(remote, "init", "--bare", "-b", "main")
        worktree.mkdir()
        self.git(worktree, "init", "-b", "main")
        self.git(worktree, "config", "user.name", "Fixture")
        self.git(worktree, "config", "user.email", "fixture@example.invalid")
        self.commit(worktree, "initial")
        self.git(worktree, "remote", "add", "origin", str(remote))
        self.git(worktree, "push", "-u", "origin", "main")
        return worktree, remote

    def commit(self, worktree: Path, text: str) -> str:
        (worktree / "tracked.txt").write_text(text)
        self.git(worktree, "add", "tracked.txt")
        self.git(worktree, "commit", "-m", text)
        return self.git(worktree, "rev-parse", "HEAD")

    def config(self, repositories: list[tuple[str, Path]]) -> Path:
        config = self.root / "registration.toml"
        config.write_text("\n".join(
            f"[[repositories]]\nid = {json.dumps(rid)}\n"
            f"path = {json.dumps(os.path.relpath(path, self.root))}\n"
            for rid, path in repositories
        ))
        return config

    def invoke(self, config: Path, *arguments: str, **environment: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *arguments], cwd=self.root,
            env={**os.environ, "FACTORY_SERVICE_CONFIG": str(config), **environment},
            capture_output=True, text=True,
        )

    def test_topic_destination_dirty_work_and_inherited_proxy(self) -> None:
        worktree, remote = self.repository("topic")
        self.git(worktree, "checkout", "-b", "local-topic")
        self.git(worktree, "push", "-u", "origin", "local-topic:published-topic")
        expected = self.commit(worktree, "publish this commit")
        self.git(worktree, "config", "push.followTags", "true")
        self.git(worktree, "tag", "-a", "local-only", "-m", "leave this tag local")
        (worktree / "staged.txt").write_text("staged work")
        self.git(worktree, "add", "staged.txt")
        (worktree / "tracked.txt").write_text("uncommitted edit")
        (worktree / "untracked.txt").write_text("untracked work")
        before = self.git(worktree, "status", "--porcelain=v2")
        hooks = worktree / ".git/hooks"
        self.git(worktree, "config", "core.hooksPath", str(hooks))
        hook = hooks / "pre-push"
        hook.write_text('#!/bin/sh\nprintf %s "$HTTPS_PROXY" > "$PROXY_RECEIPT"\n')
        hook.chmod(0o755)
        receipt = self.root / "proxy.txt"
        proxy = "http://proxy.example.invalid:7890"
        result = self.invoke(self.config([("topic", worktree)]),
                             HTTPS_PROXY=proxy, PROXY_RECEIPT=str(receipt))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.git(remote, "rev-parse", "refs/heads/published-topic"), expected)
        self.assertEqual(self.git(remote, "tag", "--list"), "")
        self.assertEqual(self.git(worktree, "status", "--porcelain=v2"), before)
        self.assertEqual((worktree / "tracked.txt").read_text(), "uncommitted edit")
        self.assertEqual((worktree / "staged.txt").read_text(), "staged work")
        self.assertEqual((worktree / "untracked.txt").read_text(), "untracked work")
        self.assertEqual(receipt.read_text(), proxy)

    def test_push_remote_overrides_push_default_and_fetch_upstream(self) -> None:
        worktree, origin = self.repository("fork")
        old = self.git(origin, "rev-parse", "main")
        publish = self.root / "publish.git"
        publish.mkdir()
        self.git(publish, "init", "--bare", "-b", "main")
        self.git(worktree, "remote", "add", "publish", str(publish))
        self.git(worktree, "config", "remote.pushDefault", "missing-default")
        self.git(worktree, "config", "branch.main.pushRemote", "publish")
        expected = self.commit(worktree, "publish to fork")
        result = self.invoke(self.config([("fork", worktree)]))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.git(publish, "rev-parse", "main"), expected)
        self.assertEqual(self.git(origin, "rev-parse", "main"), old)

    def test_rejected_push_preserves_history_and_continues_other_repositories(self) -> None:
        worktree, remote = self.repository("diverged")
        peer = self.root / "peer"
        self.git(self.root, "clone", str(remote), str(peer))
        self.git(peer, "config", "user.name", "Peer")
        self.git(peer, "config", "user.email", "peer@example.invalid")
        remote_head = self.commit(peer, "remote changes")
        self.git(peer, "push")
        local_head = self.commit(worktree, "local changes")
        healthy, healthy_remote = self.repository("healthy")
        expected = self.commit(healthy, "healthy changes")
        result = self.invoke(self.config([("diverged", worktree), ("healthy", healthy)]))
        self.assertEqual(result.returncode, 1)
        self.assertIn("failed: diverged", result.stdout)
        self.assertEqual(self.git(remote, "rev-parse", "main"), remote_head)
        self.assertEqual(self.git(worktree, "rev-parse", "HEAD"), local_head)
        self.assertEqual(self.git(healthy_remote, "rev-parse", "main"), expected)

    def test_dry_run_and_config_override_do_not_publish_commits(self) -> None:
        worktree, remote = self.repository("preview")
        original = self.git(remote, "rev-parse", "main")
        self.commit(worktree, "not published by preview")
        config = self.config([("preview", worktree)])
        result = self.invoke(config, "--config", str(config), "--dry-run",
                             FACTORY_SERVICE_CONFIG=str(self.root / "missing.toml"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("1/1 succeeded (dry-run)", result.stdout)
        self.assertEqual(self.git(remote, "rev-parse", "main"), original)

    def test_live_discovery_ignores_other_checkouts_and_rejects_ambiguity(self) -> None:
        proc, checkout, other = self.root / "proc", self.root / "factory", self.root / "old"
        proc.mkdir()
        checkout.mkdir()
        other.mkdir()
        for pid, cwd, option in [("1", other, "old.toml"), ("2", checkout, "current.toml")]:
            process = proc / pid
            process.mkdir()
            (process / "cwd").symlink_to(cwd, target_is_directory=True)
            (process / "cmdline").write_bytes(
                b"python3\0-m\0reconstruction_factory.mcp_server\0--config\0" + os.fsencode(option) + b"\0"
            )
        self.assertEqual(helper.running_config(proc, checkout), checkout / "current.toml")
        process = proc / "3"
        process.mkdir()
        (process / "cwd").symlink_to(checkout, target_is_directory=True)
        (process / "cmdline").write_bytes(
            b"touhou-reconstruction-factory-mcp\0--config=another.toml\0"
        )
        with self.assertRaisesRegex(ValueError, "pass --config"):
            helper.running_config(proc, checkout)
