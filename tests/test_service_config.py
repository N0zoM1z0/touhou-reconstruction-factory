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

    def test_configuration_identity_includes_policy_contents(self) -> None:
        path = self.write_config()
        first = load_service_config(path).sha256
        policy = json.loads((self.root / "policy.json").read_text(encoding="utf-8"))
        policy["description"] += " Changed."
        (self.root / "policy.json").write_text(json.dumps(policy), encoding="utf-8")
        second = load_service_config(path).sha256
        self.assertNotEqual(first, second)

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
