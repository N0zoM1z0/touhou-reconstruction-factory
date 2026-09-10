from __future__ import annotations

import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from reconstruction_factory.errors import WorkspaceConflictError, WorkspaceError
from reconstruction_factory.service_config import load_service_config
from reconstruction_factory.workspaces import WorkspaceStore


class WorkspaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repository = self.root / "repository"
        self.repository.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.repository, check=True)
        subprocess.run(
            ["git", "config", "user.name", "Factory Test"],
            cwd=self.repository,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "factory-test@example.invalid"],
            cwd=self.repository,
            check=True,
        )
        (self.repository / ".gitignore").write_text("private.bin\n", encoding="utf-8")
        (self.repository / "README.md").write_text("committed\n", encoding="utf-8")
        (self.repository / "src").mkdir()
        (self.repository / "src" / "main.c").write_text(
            "int main(void) { return 0; }\n", encoding="utf-8"
        )
        subprocess.run(["git", "add", "."], cwd=self.repository, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "fixture"],
            cwd=self.repository,
            check=True,
        )
        (self.repository / "README.md").write_text("dirty\n", encoding="utf-8")
        (self.repository / "untracked.txt").write_text("private\n", encoding="utf-8")
        (self.repository / "private.bin").write_bytes(b"original target")

        source_policy = Path(__file__).parents[1] / "policies/strict-live-v1.json"
        (self.root / "policy.json").write_text(
            source_policy.read_text(encoding="utf-8"), encoding="utf-8"
        )
        self.config_path = self.root / "service.toml"
        self.config_path.write_text(
            """schema_version = 1
state_directory = "state"
evidence_store = "evidence"
policy = "policy.json"
replay_timeout_seconds = 60
worker_lease_seconds = 30
worker_poll_seconds = 1.0

[workspace]
enabled = true
root = "state/workspaces"
ttl_seconds = 3600
max_active = 2
max_snapshot_files = 100
max_snapshot_bytes = 1048576
max_file_bytes = 262144
command_timeout_seconds = 10
max_command_output_bytes = 1024
max_patch_bytes = 65536

[[repositories]]
id = "fixture"
path = "repository"
adapter_id = "windows-pe-ledgers-v1"
target_identity_ids = ["target:fixture"]
""",
            encoding="utf-8",
        )
        self.config = load_service_config(self.config_path)
        self.store = WorkspaceStore(self.config)
        self.registration = self.config.repository("fixture")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def create(self, key: str = "test-create") -> dict:
        return self.store.create(self.registration, key)

    def test_snapshot_is_committed_head_and_capability_is_idempotent(self) -> None:
        created = self.create()
        reused = self.create()
        self.assertEqual(created["workspace_id"], reused["workspace_id"])
        self.assertTrue(created["source_worktree_dirty_observed"])
        self.assertEqual(created["source_mode"], "committed-head")
        self.assertRegex(created["workspace_id"], r"^workspace:[0-9a-f]{32}$")

        read = self.store.read_file(
            created["workspace_id"], "README.md", offset=0, limit=100
        )
        self.assertEqual(read["text"], "committed\n")
        listed = self.store.list_files(
            created["workspace_id"], glob="**", limit=100, offset=0
        )
        self.assertNotIn("untracked.txt", listed["items"])
        self.assertNotIn("private.bin", listed["items"])
        with self.assertRaisesRegex(WorkspaceError, "does not exist"):
            self.store.read_file(
                created["workspace_id"], "private.bin", offset=0, limit=100
            )

    def test_capacity_and_capability_boundaries_fail_closed(self) -> None:
        first = self.create("first")
        self.create("second")
        with self.assertRaisesRegex(WorkspaceConflictError, "capacity"):
            self.create("third")
        with self.assertRaisesRegex(WorkspaceError, "invalid workspace"):
            self.store.get("workspace:not-a-capability")
        with self.assertRaisesRegex(WorkspaceError, "escapes"):
            self.store.read_file(
                first["workspace_id"], "../README.md", offset=0, limit=1
            )

    def test_committed_git_links_fail_before_archive_creation(self) -> None:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=self.repository, text=True
        ).strip()
        subprocess.run(
            [
                "git",
                "update-index",
                "--add",
                "--cacheinfo",
                f"160000,{commit},vendor-link",
            ],
            cwd=self.repository,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-q", "-m", "add git link"],
            cwd=self.repository,
            check=True,
        )
        with self.assertRaisesRegex(WorkspaceError, "regular tracked files"):
            self.create()

    def test_export_ignore_cannot_silently_omit_committed_source(self) -> None:
        (self.repository / ".gitattributes").write_text(
            "README.md export-ignore\n", encoding="utf-8"
        )
        subprocess.run(
            ["git", "add", ".gitattributes"], cwd=self.repository, check=True
        )
        subprocess.run(
            ["git", "commit", "-q", "-m", "add archive rule"],
            cwd=self.repository,
            check=True,
        )
        with self.assertRaisesRegex(WorkspaceError, "omits entries"):
            self.create()

    def test_expiry_revokes_payload_access_and_releases_capacity(self) -> None:
        started = datetime(2026, 1, 1, tzinfo=timezone.utc)
        with patch("reconstruction_factory.workspaces._now", return_value=started):
            workspace_id = self.create()["workspace_id"]
        with patch(
            "reconstruction_factory.workspaces._now",
            return_value=started + timedelta(hours=2),
        ):
            expired = self.store.get(workspace_id)
            self.assertEqual(expired["state"], "expired")
            with self.assertRaisesRegex(WorkspaceError, "expired"):
                self.store.status(workspace_id)
            replacement = self.store.create(self.registration, "after-expiry")
        self.assertEqual(replacement["state"], "active")

    def test_search_patch_status_and_paged_diff_compose(self) -> None:
        workspace_id = self.create()["workspace_id"]
        result = self.store.search(
            workspace_id,
            "return 0",
            glob="*.c",
            literal=True,
            case_sensitive=True,
            limit=20,
            offset=0,
        )
        self.assertEqual(result["observed_matches"], 1)
        self.assertEqual(result["items"][0]["relative_path"], "src/main.c")

        patch = """diff --git a/README.md b/README.md
--- a/README.md
+++ b/README.md
@@ -1 +1 @@
-committed
+patched
"""
        status = self.store.apply_patch(workspace_id, patch)
        self.assertEqual(status["changed_entry_count"], 1)
        self.assertEqual(status["changed_entries"][0]["path"], "README.md")
        diff = self.store.diff(workspace_id, offset=0, limit=65536)
        self.assertIn("+patched", diff["text"])
        self.assertIsNone(diff["next_offset"])

    @unittest.skipUnless(shutil.which("bwrap"), "bubblewrap is not installed")
    def test_shell_is_composable_but_source_only_and_transactional(self) -> None:
        workspace_id = self.create()["workspace_id"]
        command = self.store.run_shell(
            workspace_id,
            """set -eu
test "$(cat README.md)" = committed
test ! -e untracked.txt
test ! -e private.bin
test ! -e /home
test ! -e /etc/passwd
python3 -c 'import socket; assert socket.socket().connect_ex(("1.1.1.1", 53)) != 0'
git status --short
printf 'generated from shell\\n' > generated.txt
printf 'visible-output\\n'
exit 7
""",
            relative_cwd=".",
            timeout_seconds=10,
        )
        self.assertEqual(command["exit_code"], 7)
        self.assertTrue(command["workspace_committed"])
        self.assertFalse(command["timed_out"])
        output = self.store.command_output(
            workspace_id,
            command["command_id"],
            stream="stdout",
            offset=0,
            limit=1024,
        )
        self.assertIn("visible-output", output["text"])
        generated = self.store.read_file(
            workspace_id, "generated.txt", offset=0, limit=1024
        )
        self.assertEqual(generated["text"], "generated from shell\n")

        timed_out = self.store.run_shell(
            workspace_id,
            "printf 'must-not-commit\\n' > timed-out.txt; sleep 2",
            relative_cwd=".",
            timeout_seconds=1,
        )
        self.assertTrue(timed_out["timed_out"])
        self.assertFalse(timed_out["workspace_committed"])
        with self.assertRaisesRegex(WorkspaceError, "does not exist"):
            self.store.read_file(workspace_id, "timed-out.txt", offset=0, limit=100)

        rejected = self.store.run_shell(
            workspace_id,
            "ln -s /etc/passwd escaped-link",
            relative_cwd=".",
            timeout_seconds=10,
        )
        self.assertEqual(rejected["exit_code"], 0)
        self.assertFalse(rejected["workspace_committed"])
        self.assertIn("regular files", rejected["workspace_validation_error"])
        with self.assertRaisesRegex(WorkspaceError, "does not exist"):
            self.store.read_file(workspace_id, "escaped-link", offset=0, limit=100)

        noisy = self.store.run_shell(
            workspace_id,
            'python3 -c \'print("x" * 2048, end="")\'',
            relative_cwd=".",
            timeout_seconds=10,
        )
        self.assertTrue(noisy["output_truncated"])
        self.assertEqual(noisy["stdout_captured_bytes"], 1024)
        self.assertEqual(noisy["stdout_observed_bytes"], 2048)

    def test_discard_removes_only_disposable_payload(self) -> None:
        workspace_id = self.create()["workspace_id"]
        discarded = self.store.discard(workspace_id)
        self.assertEqual(discarded["state"], "discarded")
        self.assertEqual(
            (self.repository / "README.md").read_text(encoding="utf-8"), "dirty\n"
        )
        with self.assertRaisesRegex(WorkspaceError, "discarded"):
            self.store.status(workspace_id)


if __name__ == "__main__":
    unittest.main()
