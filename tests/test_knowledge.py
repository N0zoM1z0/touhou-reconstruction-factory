from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from reconstruction_factory.errors import GameKnowledgeError, RegressionFixtureError
from reconstruction_factory.game_knowledge import (
    GAME_KNOWLEDGE_SCHEMA_URI,
    GameKnowledgeStatus,
    load_game_knowledge,
)
from reconstruction_factory.knowledge import (
    DEFAULT_KNOWLEDGE_CATALOG,
    KnowledgeStatus,
    load_knowledge_catalog,
)


class KnowledgeCatalogTests(unittest.TestCase):
    def test_catalog_links_verified_rules_to_fixture_evidence(self) -> None:
        catalog = load_knowledge_catalog()
        self.assertEqual(len(catalog.entries), 13)
        verified = [entry for entry in catalog.entries if entry.status is KnowledgeStatus.VERIFIED]
        provisional = [
            entry
            for entry in catalog.entries
            if entry.status is KnowledgeStatus.PROVISIONAL
        ]
        unknown = [entry for entry in catalog.entries if entry.status is KnowledgeStatus.UNKNOWN]
        self.assertEqual(len(verified), 10)
        self.assertEqual(len(provisional), 1)
        self.assertEqual(len(unknown), 2)
        self.assertTrue(all(entry.evidence_fixture_ids for entry in verified))
        self.assertTrue(all(not entry.consequences for entry in unknown))
        self.assertEqual(
            provisional[0].id,
            "semantic-reconstruction-needs-native-product-baseline",
        )

    def test_unknown_entry_cannot_impose_verified_consequences(self) -> None:
        document = json.loads(DEFAULT_KNOWLEDGE_CATALOG.read_text(encoding="utf-8"))
        entry = next(item for item in document["entries"] if item["status"] == "unknown")
        entry["consequences"] = ["Pretend the unknown is resolved."]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaisesRegex(RegressionFixtureError, "cannot impose"):
                load_knowledge_catalog(path)

    def test_verified_entry_requires_fixture_evidence(self) -> None:
        document = json.loads(DEFAULT_KNOWLEDGE_CATALOG.read_text(encoding="utf-8"))
        entry = next(item for item in document["entries"] if item["status"] == "verified")
        entry["evidence_fixture_ids"] = []
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaisesRegex(RegressionFixtureError, "requires fixture evidence"):
                load_knowledge_catalog(path)


class GameKnowledgeInputTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "scripts").mkdir()
        (self.root / "scripts" / "inspect.py").write_text(
            "print('bounded inspection')\n", encoding="utf-8"
        )
        self.path = self.root / ".reconstruction" / "game-knowledge.json"
        self.path.parent.mkdir()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def document(self) -> dict:
        return {
            "$schema": GAME_KNOWLEDGE_SCHEMA_URI,
            "schema_version": 1,
            "document_type": "game-knowledge-input",
            "authority": "game-local",
            "factory_publication": "none",
            "repository_id": "th105",
            "entries": [
                {
                    "id": "bounded-inspection-recipe",
                    "kind": "recipe",
                    "status": "reproduced",
                    "statement": "Run the repository script for this bounded inspection.",
                    "scopes": ["game:th105", "subsystem:inspection"],
                    "evidence": [
                        {
                            "kind": "repository-path",
                            "reference": "scripts/inspect.py",
                            "note": "The maintained script implements the procedure.",
                        }
                    ],
                    "validations": [
                        {
                            "method": "python3 scripts/inspect.py",
                            "result": "passed",
                            "note": "The focused workspace check exited successfully.",
                        }
                    ],
                    "limitations": [
                        "This records a game-local procedure and grants no exactness credit."
                    ],
                    "superseded_by": [],
                },
                {
                    "id": "unresolved-owner-boundary",
                    "kind": "unknown",
                    "status": "unknown",
                    "statement": "The physical owner boundary remains unknown.",
                    "scopes": ["game:th105", "target:th105-main"],
                    "evidence": [],
                    "validations": [],
                    "limitations": ["No accepted receipt covers the requested extent."],
                    "superseded_by": [],
                },
            ],
        }

    def write(self, document: dict) -> None:
        self.path.write_text(json.dumps(document), encoding="utf-8")

    def test_game_local_input_validates_without_publication_authority(self) -> None:
        self.write(self.document())
        catalog = load_game_knowledge(
            self.path,
            repository_root=self.root,
            expected_repository_id="th105",
        )
        self.assertEqual(catalog.authority, "game-local")
        self.assertEqual(catalog.factory_publication, "none")
        self.assertEqual(len(catalog.entries), 2)
        self.assertEqual(
            catalog.to_dict()["status_counts"][GameKnowledgeStatus.REPRODUCED.value],
            1,
        )

    def test_web_input_cannot_request_factory_publication(self) -> None:
        document = self.document()
        document["factory_publication"] = "requested"
        self.write(document)
        with self.assertRaisesRegex(GameKnowledgeError, "cannot request Factory publication"):
            load_game_knowledge(self.path)

    def test_boolean_schema_version_is_rejected(self) -> None:
        document = self.document()
        document["schema_version"] = True
        self.write(document)
        with self.assertRaisesRegex(GameKnowledgeError, "unsupported.*schema version"):
            load_game_knowledge(self.path)

    def test_cross_game_or_verified_vocabulary_is_rejected(self) -> None:
        for field, value, message in (
            ("status", "verified", "unsupported kind or status"),
            ("scopes", ["all", "game:th105"], "only normalized"),
        ):
            with self.subTest(field=field):
                document = self.document()
                document["entries"][0][field] = value
                self.write(document)
                with self.assertRaisesRegex(GameKnowledgeError, message):
                    load_game_knowledge(self.path)

    def test_reproduced_requires_passing_validation(self) -> None:
        document = self.document()
        document["entries"][0]["validations"][0]["result"] = "unavailable"
        self.write(document)
        with self.assertRaisesRegex(GameKnowledgeError, "requires a passing validation"):
            load_game_knowledge(self.path)

    def test_repository_path_must_exist_inside_selected_repository(self) -> None:
        document = self.document()
        document["entries"][0]["evidence"][0]["reference"] = "missing.py"
        self.write(document)
        with self.assertRaisesRegex(GameKnowledgeError, "does not exist"):
            load_game_knowledge(self.path, repository_root=self.root)

    def test_supersession_must_reference_an_existing_acyclic_entry(self) -> None:
        document = self.document()
        document["entries"][0]["status"] = "superseded"
        document["entries"][0]["superseded_by"] = ["unresolved-owner-boundary"]
        document["entries"][1]["status"] = "superseded"
        document["entries"][1]["kind"] = "scoped-fact"
        document["entries"][1]["superseded_by"] = ["bounded-inspection-recipe"]
        self.write(document)
        with self.assertRaisesRegex(GameKnowledgeError, "contains a cycle"):
            load_game_knowledge(self.path)

if __name__ == "__main__":
    unittest.main()
