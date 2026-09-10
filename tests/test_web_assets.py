from __future__ import annotations

import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ElementTree


ROOT = Path(__file__).parents[1]
CONTRACT_ID = "gpt-web-reconstruction-session-v1"


class WebWorkflowAssetTests(unittest.TestCase):
    def test_contract_preserves_separate_authorities(self) -> None:
        contract = json.loads(
            (ROOT / "contracts" / f"{CONTRACT_ID}.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(contract["schema_version"], 1)
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
        self.assertIn("name: factory-reconstruction", skill)
        defaults = "\n".join(manifest["interface"]["defaultPrompt"])
        self.assertIn("reconstruction", defaults.lower())

    def test_workflow_evaluation_has_ten_independent_scenarios(self) -> None:
        root = ElementTree.parse(
            ROOT / "evaluations" / "gpt-web-reconstruction.xml"
        ).getroot()
        pairs = root.findall("qa_pair")
        self.assertEqual(len(pairs), 10)
        questions = [pair.findtext("question") for pair in pairs]
        answers = [pair.findtext("answer") for pair in pairs]
        self.assertEqual(len(questions), len(set(questions)))
        self.assertTrue(all(questions))
        self.assertTrue(all(answers))


if __name__ == "__main__":
    unittest.main()
