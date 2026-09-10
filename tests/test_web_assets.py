from __future__ import annotations

import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ElementTree


ROOT = Path(__file__).parents[1]
CONTRACT_ID = "gpt-web-reconstruction-session-v4"
SEMANTIC_CONTRACT_ID = "gpt-web-semantic-reconstruction-session-v2"
PLUGIN_ROOT = ROOT / "plugins" / "touhou-reconstruction-factory"
FACTORY_APP_ID = "asdk_app_6aa21bec66888191bd24c118e47ddee6"


class WebWorkflowAssetTests(unittest.TestCase):
    def test_contract_preserves_separate_authorities(self) -> None:
        contract = json.loads(
            (ROOT / "contracts" / f"{CONTRACT_ID}.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(contract["schema_version"], 4)
        self.assertEqual(contract["id"], CONTRACT_ID)
        self.assertEqual(
            set(contract["required_inputs"]),
            {"game_id", "objective", "stop_condition"},
        )
        self.assertEqual(
            contract["authorities"]["analysis"]["exactness_credit"], "none"
        )
        self.assertTrue(
            contract["authorities"]["repository_work"]["game_repository_write"]
        )
        self.assertTrue(
            contract["authorities"]["repository_work"]["local_git_commit"]
        )
        self.assertFalse(contract["authorities"]["repository_work"]["git_push"])
        self.assertFalse(
            contract["authorities"]["repository_work"]["truth_promotion"]
        )
        self.assertFalse(
            contract["authorities"]["disposable_workspace"][
                "default_for_reconstruction"
            ]
        )
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
        self.assertFalse(contract["authorities"]["replay"]["dirty_source_eligible"])
        self.assertEqual(
            contract["authorities"]["acceptance_registry"]["role"],
            "sole live Truth Kernel admission authority",
        )
        self.assertEqual(
            len(contract["workflow_phases"]), len(set(contract["workflow_phases"]))
        )
        self.assertIn(
            "git-push",
            contract["prohibitions"],
        )
        self.assertIn(
            "claim-exactness-from-build-or-git-commit", contract["prohibitions"]
        )
        self.assertIn(
            "publish-or-promote-game-local-knowledge", contract["prohibitions"]
        )
        self.assertIn("game_knowledge_changes", contract["handoff_fields"])
        self.assertIn("created_checkpoint_commits", contract["handoff_fields"])
        self.assertIn("unknowns_and_blockers", contract["handoff_fields"])
        self.assertIn("agent-autonomy-first", contract["design_principles"])
        self.assertIn(
            "verification-planes-are-independent-but-feedback-is-coupled",
            contract["design_principles"],
        )
        planes = contract["verification_planes"]
        self.assertEqual(
            set(planes),
            {
                "function_or_extent_exactness",
                "production_closure",
                "runtime_storage",
                "runtime_scenario",
            },
        )
        self.assertEqual(
            planes["production_closure"]["subject_kinds"], ["product"]
        )
        self.assertEqual(
            planes["runtime_scenario"]["factory_live_provider"], "unavailable"
        )
        self.assertIn(
            "verification_plane_statuses", contract["handoff_fields"]
        )
        self.assertFalse(contract["checkpoint_rules"]["commit_is_exactness_evidence"])

    def test_semantic_contract_preserves_stage_order_and_two_oracles(self) -> None:
        contract = json.loads(
            (ROOT / "contracts" / f"{SEMANTIC_CONTRACT_ID}.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(contract["schema_version"], 2)
        self.assertEqual(contract["id"], SEMANTIC_CONTRACT_ID)
        self.assertEqual(contract["extends"], CONTRACT_ID)
        self.assertEqual(
            contract["historical_platform_stage_order"],
            [
                "target-specific-exact-reconstruction-baseline",
                "corresponding-historical-platform-product-closure-and-runtime-owner-feedback",
                "semantic-reconstruction-under-both-feedback-lanes",
                "portable-platform-products",
            ],
        )
        entry = contract["phase_entry"]
        self.assertFalse(entry["whole_project_exact_completion_required"])
        self.assertTrue(entry["target_specific_exact_baseline_required"])
        self.assertTrue(entry["historical_platform_product_closure_required"])
        self.assertTrue(entry["historical_platform_runtime_owner_feedback_required"])
        self.assertEqual(
            set(contract["semantic_regression_oracles"]),
            {
                "target_exact_oracle",
                "historical_platform_product_oracle",
                "joint_role",
                "portable_product_role",
            },
        )
        self.assertEqual(
            contract["authority_boundary"]["factory_semantic_completion_provider"],
            "unavailable",
        )
        self.assertIn(
            "zero-router-candidates-does-not-imply-semantic-completion",
            contract["non_implications"],
        )
        self.assertFalse(
            contract["checkpoint_rules"]["commit_is_semantic_or_exactness_proof"]
        )
        continuation = contract["continuation_policy"]
        self.assertTrue(continuation["continue_after_successful_batch"])
        self.assertFalse(continuation["ask_permission_after_successful_batch"])
        self.assertFalse(continuation["batch_completion_is_session_stop"])
        self.assertIn("campaign_milestone", contract["feedback_ladder"])
        self.assertIn("receipt_cadence", contract["feedback_ladder"])

    def test_semantic_prompt_skill_and_manifest_publish_the_same_workflow(self) -> None:
        prompt = (ROOT / "prompts" / "gpt-web-semantic-reconstruction.md").read_text(
            encoding="utf-8"
        )
        skill = (
            PLUGIN_ROOT
            / "skills"
            / "factory-semantic-reconstruction"
            / "SKILL.md"
        ).read_text(encoding="utf-8")
        reference = (
            PLUGIN_ROOT
            / "skills"
            / "factory-semantic-reconstruction"
            / "references"
            / "th095-start.md"
        ).read_text(encoding="utf-8")
        manifest = json.loads(
            (PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(
                encoding="utf-8"
            )
        )
        for document in (prompt, skill):
            self.assertIn(SEMANTIC_CONTRACT_ID, document)
            self.assertIn("factory_report_semantic_debt", document)
            self.assertIn("factory_repository_run_shell", document)
            self.assertIn("gpt-web:", document)
            self.assertIn("unknown", document)
            self.assertIn("campaign", document.lower())
        for field in ("GAME_ID", "SEMANTIC_OBJECTIVE", "STOP_CONDITION"):
            self.assertIn(field, prompt)
        for document in (prompt, skill, reference):
            self.assertIn("Windows i386", document)
            self.assertIn("exact", document.lower())
            self.assertIn("semantic", document.lower())
        self.assertIn("name: factory-semantic-reconstruction", skill)
        self.assertIn("without asking", prompt)
        self.assertIn("after every private checkpoint", prompt)
        defaults = "\n".join(manifest["interface"]["defaultPrompt"])
        self.assertIn("TH095 semantic", defaults)

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
            self.assertIn("factory_repository_run_shell", document)
            self.assertIn("gpt-web:", document)
            self.assertIn("Git push", document)
            self.assertIn("production closure", document)
            self.assertIn("runtime scenario", document)
        self.assertIn("name: factory-reconstruction", skill)
        defaults = "\n".join(manifest["interface"]["defaultPrompt"])
        self.assertIn("reconstruction", defaults.lower())

    def test_plugin_binds_registered_chatgpt_app_without_desktop_only_mcp(self) -> None:
        manifest = json.loads(
            (PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(
                encoding="utf-8"
            )
        )
        app_manifest = json.loads(
            (PLUGIN_ROOT / ".app.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["apps"], "./.app.json")
        self.assertNotIn("mcpServers", manifest)
        self.assertFalse((PLUGIN_ROOT / ".mcp.json").exists())
        self.assertFalse((PLUGIN_ROOT / "mcp.json").exists())
        self.assertEqual(
            set(app_manifest["apps"]), {"touhou-reconstruction-factory"}
        )
        app = app_manifest["apps"]["touhou-reconstruction-factory"]
        self.assertEqual(app, {"id": FACTORY_APP_ID, "required": True})
        self.assertTrue(app["id"].startswith("asdk_app_"))
        self.assertFalse(app["id"].startswith("plugin_"))
        self.assertNotIn("asdk_app_v_", app["id"])

    def test_bundled_skills_have_consistent_ui_metadata(self) -> None:
        expected = {
            "factory-analysis": "Factory Analysis",
            "factory-reconstruction": "Factory Reconstruction",
            "factory-replay": "Factory Replay",
            "factory-semantic-reconstruction": "Factory Semantic Reconstruction",
            "factory-workspace": "Factory Workspace",
        }
        for skill_name, display_name in expected.items():
            metadata = (
                PLUGIN_ROOT / "skills" / skill_name / "agents" / "openai.yaml"
            ).read_text(encoding="utf-8")
            self.assertIn(f'display_name: "{display_name}"', metadata)
            self.assertIn(f"${skill_name}", metadata)
            short_line = next(
                line
                for line in metadata.splitlines()
                if "short_description:" in line
            )
            short_description = json.loads(short_line.split(":", 1)[1].strip())
            self.assertGreaterEqual(len(short_description), 25)
            self.assertLessEqual(len(short_description), 64)

    def test_workflow_evaluation_has_independent_scenarios(self) -> None:
        root = ElementTree.parse(
            ROOT / "evaluations" / "gpt-web-reconstruction.xml"
        ).getroot()
        pairs = root.findall("qa_pair")
        self.assertGreaterEqual(len(pairs), 22)
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
