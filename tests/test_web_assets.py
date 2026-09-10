from __future__ import annotations

import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ElementTree


ROOT = Path(__file__).parents[1]
CONTRACT_ID = "gpt-web-reconstruction-session-v2"


class WebWorkflowAssetTests(unittest.TestCase):
    def test_contract_preserves_separate_authorities(self) -> None:
        contract = json.loads(
            (ROOT / "contracts" / f"{CONTRACT_ID}.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(contract["schema_version"], 2)
        self.assertEqual(contract["id"], CONTRACT_ID)
        self.assertEqual(
            set(contract["required_inputs"]),
            {"game_id", "objective", "stop_condition"},
        )
        self.assertEqual(
            contract["authorities"]["analysis"]["exactness_credit"], "none"
        )
        self.assertFalse(contract["authorities"]["workspace"]["canonical_write"])
        self.assertFalse(contract["authorities"]["workspace"]["truth_promotion"])
        self.assertEqual(
            contract["authorities"]["game_knowledge"]["canonical_path"],
            ".reconstruction/game-knowledge.json",
        )
        self.assertEqual(
            contract["authorities"]["game_knowledge"]["factory_publication"],
            "none",
        )
        self.assertFalse(contract["authorities"]["factory_knowledge"]["web_write"])
        self.assertFalse(
            contract["authorities"]["factory_knowledge"]["mcp_promotion"]
        )
        self.assertFalse(
            contract["authorities"]["replay"]["workspace_diff_eligible"]
        )
        self.assertEqual(
            contract["authorities"]["acceptance_registry"]["role"],
            "sole live Truth Kernel admission authority",
        )
        self.assertEqual(
            len(contract["workflow_phases"]), len(set(contract["workflow_phases"]))
        )
        self.assertIn(
            "discard-a-resumable-workspace-without-instruction",
            contract["prohibitions"],
        )
        self.assertIn(
            "run-the-game-or-start-portability-work", contract["prohibitions"]
        )
        self.assertIn(
            "publish-or-promote-game-local-knowledge", contract["prohibitions"]
        )
        self.assertIn("game_knowledge_changes", contract["handoff_fields"])
        self.assertIn("unknowns_and_blockers", contract["handoff_fields"])

    def test_prompt_skill_and_manifest_publish_the_same_workflow(self) -> None:
        prompt = (ROOT / "prompts" / "gpt-web-reconstruction.md").read_text(
            encoding="utf-8"
        )
        skill = (
            ROOT
            / "plugins"
            / "touhou-reconstruction-factory"
            / "skills"
            / "factory-reconstruction"
            / "SKILL.md"
        ).read_text(encoding="utf-8")
        manifest = json.loads(
            (
                ROOT
                / "plugins"
                / "touhou-reconstruction-factory"
                / ".codex-plugin"
                / "plugin.json"
            ).read_text(encoding="utf-8")
        )
        for document in (prompt, skill):
            self.assertIn(CONTRACT_ID, document)
        for field in ("GAME_ID", "OBJECTIVE", "STOP_CONDITION"):
            self.assertIn(field, prompt)
        for document in (prompt, skill):
            self.assertIn(".reconstruction/game-knowledge.json", document)
            self.assertIn("factory_publication", document)
        self.assertIn("name: factory-reconstruction", skill)
        defaults = "\n".join(manifest["interface"]["defaultPrompt"])
        self.assertIn("reconstruction", defaults.lower())

    def test_workflow_evaluation_has_twelve_independent_scenarios(self) -> None:
        root = ElementTree.parse(
            ROOT / "evaluations" / "gpt-web-reconstruction.xml"
        ).getroot()
        pairs = root.findall("qa_pair")
        self.assertEqual(len(pairs), 12)
        questions = [pair.findtext("question") for pair in pairs]
        answers = [pair.findtext("answer") for pair in pairs]
        self.assertEqual(len(questions), len(set(questions)))
        self.assertTrue(all(questions))
        self.assertTrue(all(answers))

    def test_game_knowledge_schema_and_template_fix_the_nonpublication_boundary(self) -> None:
        schema = json.loads(
            (ROOT / "schemas" / "v1" / "game-knowledge-input.schema.json").read_text(
                encoding="utf-8"
            )
        )
        template = json.loads(
            (ROOT / "templates" / "game-knowledge-v1.json").read_text(
                encoding="utf-8"
            )
        )
        properties = schema["properties"]
        self.assertEqual(properties["authority"]["const"], "game-local")
        self.assertEqual(properties["factory_publication"]["const"], "none")
        self.assertEqual(template["authority"], "game-local")
        self.assertEqual(template["factory_publication"], "none")
        statuses = schema["$defs"]["entry"]["properties"]["status"]["enum"]
        self.assertNotIn("verified", statuses)
        self.assertNotIn("provisional", statuses)


if __name__ == "__main__":
    unittest.main()
