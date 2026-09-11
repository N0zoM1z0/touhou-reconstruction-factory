from __future__ import annotations

import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ElementTree


ROOT = Path(__file__).parents[1]
CONTRACT_ID = "gpt-web-reconstruction-session-v5"
BASE_CONTRACT_ID = "gpt-web-reconstruction-session-v4"
SEMANTIC_CONTRACT_ID = "gpt-web-semantic-reconstruction-session-v4"
SEMANTIC_BASE_CONTRACT_ID = "gpt-web-semantic-reconstruction-session-v3"
PLUGIN_ROOT = ROOT / "plugins" / "touhou-reconstruction-factory"
FACTORY_APP_ID = "asdk_app_6aa21bec66888191bd24c118e47ddee6"


class WebWorkflowAssetTests(unittest.TestCase):
    def test_contract_preserves_separate_authorities(self) -> None:
        contract = json.loads(
            (ROOT / "contracts" / f"{CONTRACT_ID}.json").read_text(
                encoding="utf-8"
            )
        )
        base = json.loads(
            (ROOT / "contracts" / f"{BASE_CONTRACT_ID}.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(contract["schema_version"], 5)
        self.assertEqual(contract["id"], CONTRACT_ID)
        self.assertEqual(contract["extends"], BASE_CONTRACT_ID)
        self.assertEqual(set(contract["required_inputs"]), {"game_id", "objective"})
        self.assertTrue(
            contract["conversation_slice_policy"]["campaign_may_span_conversations"]
        )
        self.assertFalse(
            contract["conversation_slice_policy"][
                "one_conversation_must_attempt_entire_campaign"
            ]
        )
        self.assertIsNone(
            contract["conversation_slice_policy"]["fixed_packet_count"]
        )
        self.assertIn(
            "repository-state-not-chat-context-carries-continuation",
            contract["design_principles_add"],
        )
        self.assertEqual(
            base["authorities"]["analysis"]["exactness_credit"], "none"
        )
        self.assertTrue(
            base["authorities"]["repository_work"]["game_repository_write"]
        )
        self.assertTrue(
            base["authorities"]["repository_work"]["local_git_commit"]
        )
        self.assertFalse(base["authorities"]["repository_work"]["git_push"])
        self.assertFalse(
            base["authorities"]["repository_work"]["truth_promotion"]
        )
        self.assertFalse(
            base["authorities"]["disposable_workspace"][
                "default_for_reconstruction"
            ]
        )
        self.assertEqual(
            base["authorities"]["game_knowledge"]["canonical_path"],
            ".reconstruction/game-knowledge.json",
        )
        self.assertEqual(
            base["authorities"]["game_knowledge"]["factory_publication"],
            "none",
        )
        self.assertFalse(base["authorities"]["factory_knowledge"]["web_write"])
        self.assertFalse(
            base["authorities"]["factory_knowledge"]["mcp_promotion"]
        )
        self.assertFalse(base["authorities"]["replay"]["dirty_source_eligible"])
        self.assertEqual(
            base["authorities"]["acceptance_registry"]["role"],
            "sole live Truth Kernel admission authority",
        )
        self.assertEqual(
            len(base["workflow_phases"]), len(set(base["workflow_phases"]))
        )
        self.assertIn(
            "git-push",
            base["prohibitions"],
        )
        self.assertIn(
            "claim-exactness-from-build-or-git-commit", base["prohibitions"]
        )
        self.assertIn(
            "publish-or-promote-game-local-knowledge", base["prohibitions"]
        )
        self.assertIn("game_knowledge_changes", base["handoff_fields"])
        self.assertIn("created_checkpoint_commits", base["handoff_fields"])
        self.assertIn("unknowns_and_blockers", base["handoff_fields"])
        self.assertIn("agent-autonomy-first", base["design_principles"])
        self.assertIn(
            "verification-planes-are-independent-but-feedback-is-coupled",
            base["design_principles"],
        )
        planes = base["verification_planes"]
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
            "verification_plane_statuses", base["handoff_fields"]
        )
        self.assertFalse(base["checkpoint_rules"]["commit_is_exactness_evidence"])

    def test_semantic_contract_preserves_stage_order_and_two_oracles(self) -> None:
        contract = json.loads(
            (ROOT / "contracts" / f"{SEMANTIC_CONTRACT_ID}.json").read_text(
                encoding="utf-8"
            )
        )
        base = json.loads(
            (ROOT / "contracts" / f"{SEMANTIC_BASE_CONTRACT_ID}.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(contract["schema_version"], 4)
        self.assertEqual(contract["id"], SEMANTIC_CONTRACT_ID)
        self.assertEqual(contract["extends"], SEMANTIC_BASE_CONTRACT_ID)
        self.assertEqual(contract["base_contract_revision"], CONTRACT_ID)
        self.assertEqual(
            set(base["required_inputs"]), {"game_id", "semantic_objective"}
        )
        self.assertNotIn("stop_condition", base["required_inputs"])
        self.assertEqual(
            base["historical_platform_stage_order"],
            [
                "target-specific-exact-reconstruction-baseline",
                "corresponding-historical-platform-product-closure-and-runtime-owner-feedback",
                "semantic-reconstruction-under-both-feedback-lanes",
                "portable-platform-products",
            ],
        )
        entry = base["phase_entry"]
        self.assertFalse(entry["whole_project_exact_completion_required"])
        self.assertTrue(entry["target_specific_exact_baseline_required"])
        self.assertTrue(entry["historical_platform_product_closure_required"])
        self.assertTrue(entry["historical_platform_runtime_owner_feedback_required"])
        self.assertEqual(
            set(base["semantic_regression_oracles"]),
            {
                "target_exact_oracle",
                "historical_platform_product_oracle",
                "joint_role",
                "portable_product_role",
            },
        )
        self.assertEqual(
            base["authority_boundary"]["factory_semantic_completion_provider"],
            "unavailable",
        )
        self.assertIn(
            "zero-router-candidates-does-not-imply-semantic-completion",
            base["non_implications"],
        )
        self.assertFalse(
            base["checkpoint_rules"]["commit_is_semantic_or_exactness_proof"]
        )
        continuation = contract["continuation_policy_override"]
        self.assertTrue(continuation["campaign_open_ended"])
        self.assertFalse(continuation["conversation_open_ended"])
        self.assertFalse(continuation["ask_permission_after_successful_batch"])
        self.assertIsNone(continuation["fixed_batches_per_conversation"])
        self.assertFalse(continuation["batch_completion_is_phase_completion"])
        self.assertFalse(continuation["web_phase_closure_authority"])
        self.assertFalse(continuation["negative_search_result_is_handoff_boundary"])
        self.assertFalse(continuation["negative_search_result_may_be_sole_slice_delivery"])
        self.assertEqual(
            contract["resume_audit_override"]["default_phase_state"], "active-incomplete"
        )
        self.assertEqual(
            base["authority_boundary"]["gpt_web_semantic_phase_closure"],
            "forbidden",
        )
        self.assertIn(
            "an-exploration-agent-cannot-certify-the-absence-of-undiscovered-work-in-an-open-world",
            base["design_principles"],
        )
        self.assertIn("campaign_milestone", base["feedback_ladder"])
        self.assertIn("receipt_cadence", base["feedback_ladder"])

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
        for field in ("GAME_ID", "SEMANTIC_OBJECTIVE", "DEFAULT_PHASE_STATE"):
            self.assertIn(field, prompt)
        self.assertNotIn("STOP_CONDITION:", prompt)
        for document in (prompt, skill, reference):
            self.assertIn("Windows i386", document)
            self.assertIn("exact", document.lower())
            self.assertIn("semantic", document.lower())
        self.assertIn("name: factory-semantic-reconstruction", skill)
        self.assertIn("without asking", prompt)
        self.assertIn("after every private checkpoint", prompt)
        self.assertIn("active-incomplete", prompt)
        self.assertIn("untrusted hypothesis", prompt)
        self.assertIn("no authority to declare", prompt)
        defaults = "\n".join(manifest["interface"]["defaultPrompt"])
        self.assertIn("TH095 semantic", defaults)
        self.assertTrue(
            all(len(item) <= 128 for item in manifest["interface"]["defaultPrompt"])
        )

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
        for field in ("GAME_ID", "OBJECTIVE"):
            self.assertIn(field, prompt)
        self.assertNotIn("STOP_CONDITION:", prompt)
        for document in (prompt, skill):
            self.assertIn(".reconstruction/game-knowledge.json", document)
            self.assertIn("factory_publication", document)
            self.assertIn("factory_repository_run_shell", document)
            self.assertIn("gpt-web:", document)
            self.assertIn("Git push", document)
            self.assertIn("production closure", document)
            self.assertIn("runtime scenario", document)
        self.assertIn("name: factory-reconstruction", skill)
        self.assertIn("one browser conversation", prompt)
        self.assertIn("one browser conversation", skill)
        defaults = "\n".join(manifest["interface"]["defaultPrompt"])
        self.assertIn("reconstruction", defaults.lower())

    def test_exact_game_prompts_bind_platform_and_moving_target(self) -> None:
        th04 = (ROOT / "prompts" / "gpt-web-th04-exact-reconstruction.md").read_text(
            encoding="utf-8"
        )
        th09 = (ROOT / "prompts" / "gpt-web-th09-exact-reconstruction.md").read_text(
            encoding="utf-8"
        )
        for prompt in (th04, th09):
            self.assertIn(CONTRACT_ID, prompt)
            self.assertIn("99.5%", prompt)
            self.assertIn("browser conversation", prompt)
            self.assertIn("gpt-web:", prompt)
            self.assertIn("Never push", prompt)
        for value in ("th04-ghidra", "target:th04-main", "16-bit", "MZ/OMF", "RETF"):
            self.assertIn(value, th04)
        for value in ("th09-ida", "target:th09-main", "Windows i386", "VC7.1"):
            self.assertIn(value, th09)

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
