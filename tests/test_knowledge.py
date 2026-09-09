from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from reconstruction_factory.errors import RegressionFixtureError
from reconstruction_factory.knowledge import (
    DEFAULT_KNOWLEDGE_CATALOG,
    KnowledgeStatus,
    load_knowledge_catalog,
)


class KnowledgeCatalogTests(unittest.TestCase):
    def test_catalog_links_verified_rules_to_fixture_evidence(self) -> None:
        catalog = load_knowledge_catalog()
        self.assertEqual(len(catalog.entries), 12)
        verified = [entry for entry in catalog.entries if entry.status is KnowledgeStatus.VERIFIED]
        unknown = [entry for entry in catalog.entries if entry.status is KnowledgeStatus.UNKNOWN]
        self.assertEqual(len(verified), 10)
        self.assertEqual(len(unknown), 2)
        self.assertTrue(all(entry.evidence_fixture_ids for entry in verified))
        self.assertTrue(all(not entry.consequences for entry in unknown))

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


if __name__ == "__main__":
    unittest.main()
