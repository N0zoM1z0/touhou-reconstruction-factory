from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from reconstruction_factory.errors import ServiceConfigError
from reconstruction_factory.service_config import load_service_config


class ServiceConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "game").mkdir()
        source_policy = Path(__file__).parents[1] / "policies/strict-live-v1.json"
        (self.root / "policy.json").write_text(
            source_policy.read_text(encoding="utf-8"), encoding="utf-8"
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_config(self, repositories: str | None = None) -> Path:
        repository = (
            repositories
            or """
[[repositories]]
id = "th08"
path = "game"
adapter_id = "th08-vc7-ledgers-v1"
target_identity_ids = ["target:th08-v1.00d-original"]
"""
        )
        path = self.root / "service.toml"
        path.write_text(
            """schema_version = 1
state_directory = "state"
evidence_store = "evidence"
policy = "policy.json"
replay_timeout_seconds = 1800
worker_lease_seconds = 30
worker_poll_seconds = 1.0
"""
            + repository,
            encoding="utf-8",
        )
        return path

    def test_loads_paths_but_public_view_redacts_them(self) -> None:
        config = load_service_config(self.write_config())
        self.assertEqual(config.repository("th08").path, (self.root / "game").resolve())
        public = config.public_dict()
        rendered = json.dumps(public)
        self.assertNotIn(str(self.root), rendered)
        self.assertEqual(public["repositories"][0]["id"], "th08")
        self.assertEqual(len(public["configuration_sha256"]), 64)
        self.assertEqual(len(public["replay_configuration_sha256"]), 64)
        self.assertFalse(public["workspace"]["enabled"])
        self.assertNotIn("root", public["workspace"])
        self.assertFalse(public["repository_work"]["enabled"])
        self.assertEqual(public["repository_work"]["status"], "disabled")
        self.assertEqual(public["repository_work"]["git_commit"], "unavailable")
        self.assertEqual(public["repository_work"]["git_push"], "unavailable")
        self.assertNotIn("root", public["repository_work"])

    def test_explicit_workspace_policy_is_strict_and_state_contained(self) -> None:
        path = self.write_config()
        document = path.read_text(encoding="utf-8")
        document += """

[workspace]
enabled = true
root = "state/workspaces"
ttl_seconds = 3600
max_active = 2
max_snapshot_files = 100
max_snapshot_bytes = 1048576
max_file_bytes = 262144
command_timeout_seconds = 30
max_command_output_bytes = 65536
max_patch_bytes = 65536
"""
        path.write_text(document, encoding="utf-8")
        config = load_service_config(path)
        self.assertTrue(config.workspace.enabled)
        self.assertTrue(config.workspace.root.is_relative_to(config.state_directory))

        path.write_text(
            document.replace('root = "state/workspaces"', 'root = "outside"')
        )
        with self.assertRaisesRegex(ServiceConfigError, "strict child"):
            load_service_config(path)

    def test_configuration_identity_includes_policy_contents(self) -> None:
        path = self.write_config()
        first = load_service_config(path).sha256
        policy = json.loads((self.root / "policy.json").read_text(encoding="utf-8"))
        policy["description"] += " Changed."
        (self.root / "policy.json").write_text(json.dumps(policy), encoding="utf-8")
        second = load_service_config(path).sha256
        self.assertNotEqual(first, second)

    def test_workspace_limits_do_not_rebind_queued_replay_semantics(self) -> None:
        path = self.write_config()
        original = load_service_config(path)
        document = (
            path.read_text(encoding="utf-8")
            + """

[workspace]
enabled = true
root = "state/workspaces"
ttl_seconds = 3600
max_active = 2
max_snapshot_files = 100
max_snapshot_bytes = 1048576
max_file_bytes = 262144
command_timeout_seconds = 30
max_command_output_bytes = 65536
max_patch_bytes = 65536
"""
        )
        path.write_text(document, encoding="utf-8")
        changed = load_service_config(path)
        self.assertNotEqual(original.sha256, changed.sha256)
        self.assertEqual(original.replay_sha256, changed.replay_sha256)

    def test_live_repository_policy_is_opt_in_and_replay_independent(self) -> None:
        path = self.write_config()
        original = load_service_config(path)
        document = (
            path.read_text(encoding="utf-8")
            + """

[repository_work]
enabled = true
root = "state/repository-work"
command_timeout_seconds = 3600
max_command_output_bytes = 8388608
git_author_name = "gpt-web"
git_author_email = "gpt-web@example.invalid"
shared_tool_roots = []
"""
        )
        path.write_text(document, encoding="utf-8")
        changed = load_service_config(path)
        self.assertTrue(changed.repository_work.enabled)
        self.assertEqual(changed.repository_work.shared_tool_roots, ())
        self.assertNotEqual(original.sha256, changed.sha256)
        self.assertEqual(original.replay_sha256, changed.replay_sha256)

    def test_per_repository_work_state_is_redacted_and_replay_independent(self) -> None:
        work_state = self.root / "wine-prefix"
        work_state.mkdir()
        original = load_service_config(self.write_config())
        repositories = f'''
[[repositories]]
id = "th08"
path = "game"
adapter_id = "th08-vc7-ledgers-v1"
target_identity_ids = ["target:th08-v1.00d-original"]
work_environment = {{ WINEPREFIX = "{work_state.as_posix()}" }}
work_state_roots = ["{work_state.as_posix()}"]
'''
        changed = load_service_config(self.write_config(repositories))
        public = changed.repository("th08").public_dict()
        self.assertEqual(public["work_environment_names"], ["WINEPREFIX"])
        self.assertEqual(public["work_state_root_count"], 1)
        self.assertNotIn(str(work_state), json.dumps(public))
        self.assertEqual(original.replay_sha256, changed.replay_sha256)

    def test_analysis_provider_is_loopback_target_bound_and_replay_independent(
        self,
    ) -> None:
        path = self.write_config()
        original = load_service_config(path)
        document = (
            path.read_text(encoding="utf-8")
            + """

[[analysis_providers]]
id = "th08-ida"
repository_id = "th08"
target_identity_id = "target:th08-v1.00d-original"
backend = "attested-ida-proxy-v1"
endpoint = "http://127.0.0.1:8767/private-mcp-path"
upstream_tool = "ida_call"
timeout_seconds = 120
"""
        )
        path.write_text(document, encoding="utf-8")
        changed = load_service_config(path)
        public = changed.public_dict()["analysis_providers"][0]
        self.assertEqual(public["id"], "th08-ida")
        self.assertNotIn("endpoint", public)
        self.assertEqual(original.replay_sha256, changed.replay_sha256)

        path.write_text(
            document.replace(
                "http://127.0.0.1:8767/private-mcp-path",
                "https://analysis.example.com/mcp",
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ServiceConfigError, "loopback"):
            load_service_config(path)

    def test_native_ida_provider_owns_stdio_and_redacts_private_paths(self) -> None:
        command = self.root / "ida-python.exe"
        target = self.root / "target.exe"
        command.write_bytes(b"provider")
        target.write_bytes(b"target")
        path = self.write_config()
        original = load_service_config(path)
        document = (
            path.read_text(encoding="utf-8")
            + f'''

[[analysis_providers]]
id = "th08-ida-native"
repository_id = "th08"
target_identity_id = "target:th08-v1.00d-original"
backend = "attested-ida-stdio-v1"
command = "{command.as_posix()}"
arguments = ["D:\\\\Tools\\\\ida_pro_mcp\\\\server.py"]
target_path = "{target.as_posix()}"
timeout_seconds = 120
'''
        )
        path.write_text(document, encoding="utf-8")
        changed = load_service_config(path)
        provider = changed.analysis_provider("th08-ida-native")
        public = provider.public_dict()
        self.assertFalse(public["read_only"])
        self.assertTrue(public["database_metadata_writable"])
        self.assertFalse(public["target_bytes_writable"])
        self.assertNotIn(str(command), json.dumps(public))
        self.assertNotIn(str(target), json.dumps(public))
        self.assertEqual(original.replay_sha256, changed.replay_sha256)

        path.write_text(document + 'endpoint = "http://127.0.0.1:8767/mcp"\n')
        with self.assertRaisesRegex(ServiceConfigError, "extra=.*endpoint"):
            load_service_config(path)

    def test_analysis_provider_cannot_cross_repository_target(self) -> None:
        path = self.write_config()
        path.write_text(
            path.read_text(encoding="utf-8")
            + """

[[analysis_providers]]
id = "wrong-target"
repository_id = "th08"
target_identity_id = "target:another"
backend = "attested-ida-proxy-v1"
endpoint = "http://127.0.0.1:8767/private-mcp-path"
upstream_tool = "ida_call"
timeout_seconds = 120
""",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ServiceConfigError, "outside"):
            load_service_config(path)

    def test_target_identity_cannot_be_registered_twice(self) -> None:
        (self.root / "other").mkdir()
        repositories = """
[[repositories]]
id = "first"
path = "game"
adapter_id = "th08-vc7-ledgers-v1"
target_identity_ids = ["target:shared"]

[[repositories]]
id = "second"
path = "other"
adapter_id = "windows-pe-ledgers-v1"
target_identity_ids = ["target:shared"]
"""
        with self.assertRaisesRegex(ServiceConfigError, "exactly one registration"):
            load_service_config(self.write_config(repositories))

    def test_unknown_fields_fail_closed(self) -> None:
        path = self.write_config()
        path.write_text(path.read_text(encoding="utf-8") + "surprise = true\n")
        with self.assertRaisesRegex(ServiceConfigError, "fields differ"):
            load_service_config(path)

    def test_service_storage_cannot_overlap_a_registered_repository(self) -> None:
        path = self.write_config()
        document = path.read_text(encoding="utf-8").replace(
            'state_directory = "state"', 'state_directory = "game/.factory-state"'
        )
        path.write_text(document, encoding="utf-8")
        with self.assertRaisesRegex(ServiceConfigError, "must not overlap"):
            load_service_config(path)

    def test_canonical_repository_path_cannot_have_two_ids(self) -> None:
        repositories = """
[[repositories]]
id = "first"
path = "game"
adapter_id = "th08-vc7-ledgers-v1"
target_identity_ids = ["target:first"]

[[repositories]]
id = "second"
path = "game"
adapter_id = "th08-vc7-ledgers-v1"
target_identity_ids = ["target:second"]
"""
        with self.assertRaisesRegex(ServiceConfigError, "exactly one registration"):
            load_service_config(self.write_config(repositories))

    def test_state_and_evidence_storage_cannot_overlap(self) -> None:
        path = self.write_config()
        document = path.read_text(encoding="utf-8").replace(
            'evidence_store = "evidence"', 'evidence_store = "state/evidence"'
        )
        path.write_text(document, encoding="utf-8")
        with self.assertRaisesRegex(ServiceConfigError, "must not overlap"):
            load_service_config(path)


if __name__ == "__main__":
    unittest.main()
