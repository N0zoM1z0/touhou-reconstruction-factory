from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from reconstruction_factory.errors import RepositoryWorkError
from reconstruction_factory.repository_work import RepositoryWorkStore
from reconstruction_factory.replay_identity import repository_lock
from reconstruction_factory.service_config import load_service_config


class RepositoryWorkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repository = self.root / "repository"
        self.repository.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.repository, check=True)
        (self.repository / "src").mkdir()
        (self.repository / ".gitignore").write_text(".tools/\n", encoding="utf-8")
        (self.repository / "README.md").write_text("fixture\n", encoding="utf-8")
        (self.repository / "src" / "SemanticFixture.cpp").write_text(
            """struct View { unsigned char unknown004[4]; };
void fixture(void *value) {
    (void)(reinterpret_cast<u8 *>(value) + 0x10);
    (void)reinterpret_cast<int *>(0x401000);
    unknown_fields(8);
}
""",
            encoding="utf-8",
        )
        subprocess.run(["git", "add", "."], cwd=self.repository, check=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=Fixture Author",
                "-c",
                "user.email=fixture@example.invalid",
                "commit",
                "-q",
                "-m",
                "fixture",
            ],
            cwd=self.repository,
            check=True,
        )
        (self.repository / ".tools").mkdir()
        (self.repository / ".tools" / "toolchain.txt").write_text(
            "repo-local toolchain\n", encoding="utf-8"
        )
        (self.repository / "untracked.txt").write_text("visible\n", encoding="utf-8")
        self.shared_tools = self.root / "shared-tools"
        self.shared_tools.mkdir()
        (self.shared_tools / "shared.txt").write_text("shared\n", encoding="utf-8")
        self.reference_repository = self.root / "reference-repository"
        self.reference_repository.mkdir()
        (self.reference_repository / "reference.txt").write_text(
            "adjacent hypothesis\n", encoding="utf-8"
        )
        self.wine_prefix = self.root / "operator-home" / ".wine-fixture"
        self.wine_prefix.mkdir(parents=True)
        policy_source = Path(__file__).parents[1] / "policies/strict-live-v1.json"
        (self.root / "policy.json").write_text(
            policy_source.read_text(encoding="utf-8"), encoding="utf-8"
        )
        self.config_path = self.root / "service.toml"
        self.config_path.write_text(
            f'''schema_version = 1
state_directory = "state"
evidence_store = "evidence"
policy = "policy.json"
replay_timeout_seconds = 60
worker_lease_seconds = 30
worker_poll_seconds = 1.0

[repository_work]
enabled = true
root = "state/repository-work"
command_timeout_seconds = 10
max_command_output_bytes = 1024
git_author_name = "gpt-web"
git_author_email = "gpt-web@example.invalid"
shared_tool_roots = ["{self.shared_tools.as_posix()}"]

[[repositories]]
id = "fixture"
path = "repository"
adapter_id = "windows-pe-ledgers-v1"
target_identity_ids = ["target:fixture"]
reference_repository_ids = ["reference"]
work_environment = {{ WINEPREFIX = "{self.wine_prefix.as_posix()}" }}
work_state_roots = ["{self.wine_prefix.as_posix()}"]

[[repositories]]
id = "reference"
path = "reference-repository"
adapter_id = "windows-pe-ledgers-v1"
target_identity_ids = ["target:reference"]
''',
            encoding="utf-8",
        )
        self.config = load_service_config(self.config_path)
        self.store = RepositoryWorkStore(self.config)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_status_reports_the_real_dirty_worktree(self) -> None:
        status = self.store.status("fixture")
        self.assertTrue(status["dirty"])
        self.assertEqual(status["untracked_files"], 1)
        self.assertEqual(status["staged_changes"], 0)
        self.assertEqual(status["unstaged_changes"], 0)
        self.assertEqual(status["source_mode"], "live-including-ignored")
        self.assertTrue(status["git_commit_is_checkpoint_only"])

    def test_semantic_debt_report_is_snapshot_bound_routing_only(self) -> None:
        report = self.store.semantic_debt_report(
            "fixture",
            relative_path="src",
            category="all",
            limit=2,
            offset=0,
        )
        self.assertTrue(report["routing_only"])
        self.assertFalse(report["completion_metric"])
        self.assertEqual(report["exactness_credit"], "none")
        self.assertEqual(report["semantic_evidence_credit"], "none")
        self.assertTrue(report["scope_complete"])
        self.assertEqual(
            report["category_counts"],
            {
                "raw-member-access": 1,
                "absolute-address": 1,
                "anonymous-identifier": 1,
                "opaque-storage": 1,
            },
        )
        self.assertEqual(report["findings"]["total"], 4)
        self.assertEqual(len(report["findings"]["items"]), 2)
        self.assertEqual(report["findings"]["next_offset"], 2)
        self.assertEqual(
            report["source_binding"]["head_commit"],
            self.store.status("fixture")["head_commit"],
        )
        self.assertTrue(report["source_binding"]["dirty"])

        filtered = self.store.semantic_debt_report(
            "fixture",
            relative_path="src/SemanticFixture.cpp",
            category="anonymous-identifier",
            limit=10,
            offset=0,
        )
        self.assertEqual(filtered["findings"]["total"], 1)
        self.assertEqual(
            filtered["findings"]["items"][0]["match"], "unknown004"
        )

    def test_semantic_debt_scope_cannot_leave_repository(self) -> None:
        with self.assertRaisesRegex(RepositoryWorkError, "repository-relative"):
            self.store.semantic_debt_report(
                "fixture",
                relative_path="/tmp",
                category="all",
                limit=20,
                offset=0,
            )

    @unittest.skipUnless(shutil.which("bwrap"), "bubblewrap is not installed")
    def test_shell_sees_tools_commits_and_persists_nonzero_changes(self) -> None:
        command = self.store.run_shell(
            "fixture",
            f'''set -eu
test "$(cat .tools/toolchain.txt)" = "repo-local toolchain"
test "$(cat {self.shared_tools.as_posix()}/shared.txt)" = shared
test "$(cat {self.reference_repository.as_posix()}/reference.txt)" = "adjacent hypothesis"
if printf 'forbidden\n' > {self.reference_repository.as_posix()}/reference.txt 2>/dev/null; then
  exit 91
fi
test "$WINEPREFIX" = "{self.wine_prefix.as_posix()}"
printf 'prefix-state\n' > "$WINEPREFIX/observed.txt"
test -f /etc/passwd
printf 'generated\n' > generated.txt
git add generated.txt
git commit -m 'gpt-web: checkpoint fixture'
printf 'checkpoint-created\n'
exit 7
''',
            relative_cwd=".",
            timeout_seconds=10,
        )
        self.assertEqual(command["exit_code"], 7)
        self.assertFalse(command["timed_out"])
        self.assertTrue(command["filesystem_persisted"])
        self.assertEqual(command["head_relation"], "advanced")
        self.assertEqual(
            [item["subject"] for item in command["created_commits"]],
            ["gpt-web: checkpoint fixture"],
        )
        self.assertIn("checkpoint-created", command["stdout"]["text"])
        self.assertTrue((self.repository / "generated.txt").is_file())
        self.assertEqual(
            (self.wine_prefix / "observed.txt").read_text(), "prefix-state\n"
        )
        author = subprocess.check_output(
            ["git", "log", "-1", "--format=%an <%ae>"],
            cwd=self.repository,
            text=True,
        ).strip()
        self.assertEqual(author, "gpt-web <gpt-web@example.invalid>")

        recovered = self.store.command_output(
            "fixture",
            command["command_id"],
            stream="stdout",
            offset=0,
            limit=1024,
        )
        self.assertIn("checkpoint-created", recovered["text"])

    @unittest.skipUnless(shutil.which("bwrap"), "bubblewrap is not installed")
    def test_timeout_and_output_truncation_do_not_roll_back_live_work(self) -> None:
        timed_out = self.store.run_shell(
            "fixture",
            "printf 'partial\\n' > partial.txt; sleep 2",
            relative_cwd=".",
            timeout_seconds=1,
        )
        self.assertTrue(timed_out["timed_out"])
        self.assertTrue(timed_out["filesystem_persisted"])
        self.assertEqual((self.repository / "partial.txt").read_text(), "partial\n")

        noisy = self.store.run_shell(
            "fixture",
            "python3 -c 'print(\"x\" * 200000)'; printf 'done\\n' > after-output.txt",
            relative_cwd=".",
            timeout_seconds=10,
        )
        self.assertEqual(noisy["exit_code"], 0)
        self.assertTrue(noisy["output_truncated"])
        self.assertTrue((self.repository / "after-output.txt").is_file())

    def test_relative_cwd_cannot_leave_the_registered_repository(self) -> None:
        with self.assertRaisesRegex(RepositoryWorkError, "repository-relative"):
            self.store.run_shell(
                "fixture", "true", relative_cwd="/tmp", timeout_seconds=1
            )
        with self.assertRaisesRegex(RepositoryWorkError, "inside"):
            self.store.run_shell(
                "fixture", "true", relative_cwd="..", timeout_seconds=1
            )

    def test_live_work_obeys_the_factory_replay_lock(self) -> None:
        with repository_lock(self.repository, exclusive=True):
            with self.assertRaisesRegex(
                RepositoryWorkError, "another Factory operation"
            ):
                self.store.status("fixture")


if __name__ == "__main__":
    unittest.main()
