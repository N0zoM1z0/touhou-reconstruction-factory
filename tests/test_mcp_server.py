from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

try:
    from mcp import Client
    from reconstruction_factory.mcp_server import (
        BearerTokenMiddleware,
        build_parser,
        build_mcp_server,
        configure_http_auth,
        mcp_path,
    )
except ImportError:
    Client = None


@unittest.skipIf(Client is None, "MCP v2 optional dependency is not installed")
class McpServerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "repository").mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.root / "repository", check=True)
        (self.root / "repository" / "README.md").write_text(
            "committed fixture\n", encoding="utf-8"
        )
        subprocess.run(["git", "add", "."], cwd=self.root / "repository", check=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=Factory Test",
                "-c",
                "user.email=factory-test@example.invalid",
                "commit",
                "-q",
                "-m",
                "fixture",
            ],
            cwd=self.root / "repository",
            check=True,
        )
        source = Path(__file__).parents[1] / "policies/strict-live-v1.json"
        (self.root / "policy.json").write_text(
            source.read_text(encoding="utf-8"), encoding="utf-8"
        )
        self.config = self.root / "service.toml"
        self.config.write_text(
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
command_timeout_seconds = 5
max_command_output_bytes = 1024
max_patch_bytes = 65536

[repository_work]
enabled = true
root = "state/repository-work"
command_timeout_seconds = 10
max_command_output_bytes = 65536
git_author_name = "gpt-web"
git_author_email = "gpt-web@example.invalid"
shared_tool_roots = []

[[repositories]]
id = "th08"
path = "repository"
adapter_id = "th08-vc7-ledgers-v1"
target_identity_ids = ["target:th08-v1.00d-original"]
""",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    async def test_discovery_exposes_only_bounded_factory_tools(self) -> None:
        async with Client(build_mcp_server(self.config)) as client:
            discovered = await client.list_tools()
        names = {tool.name for tool in discovered.tools}
        self.assertFalse(any("promot" in name or "publish" in name for name in names))
        self.assertEqual(
            names,
            {
                "factory_cancel_job",
                "factory_analysis_call",
                "factory_create_workspace",
                "factory_describe",
                "factory_discard_workspace",
                "factory_get_acceptance_registry",
                "factory_get_accepted_snapshot",
                "factory_get_job",
                "factory_get_job_events",
                "factory_get_job_output_page",
                "factory_get_repository_command_output",
                "factory_get_repository_status",
                "factory_get_workspace",
                "factory_get_workspace_command_output",
                "factory_get_workspace_diff",
                "factory_get_workspace_status",
                "factory_inspect_repository",
                "factory_list_analysis_operations",
                "factory_list_analysis_providers",
                "factory_list_claims",
                "factory_list_historical_fixtures",
                "factory_list_jobs",
                "factory_list_repositories",
                "factory_query_accepted_facts",
                "factory_query_knowledge",
                "factory_report_semantic_debt",
                "factory_repository_run_shell",
                "factory_submit_replay",
                "factory_workspace_apply_patch",
                "factory_workspace_list_files",
                "factory_workspace_read_file",
                "factory_workspace_run_shell",
                "factory_workspace_search",
            },
        )
        schemas = json.dumps(
            [tool.input_schema for tool in discovered.tools], sort_keys=True
        )
        self.assertNotIn('"command"', schemas)
        self.assertNotIn('"cwd"', schemas)
        self.assertNotIn('"path"', schemas)
        self.assertIn('"script"', schemas)
        self.assertIn('"relative_cwd"', schemas)
        claims = next(
            tool for tool in discovered.tools if tool.name == "factory_list_claims"
        )
        self.assertEqual(claims.input_schema["properties"]["limit"]["maximum"], 100)
        self.assertEqual(claims.input_schema["properties"]["offset"]["minimum"], 0)
        shell = next(
            tool
            for tool in discovered.tools
            if tool.name == "factory_workspace_run_shell"
        )
        self.assertEqual(shell.input_schema["properties"]["script"]["maxLength"], 65536)
        self.assertTrue(shell.annotations.destructive_hint)
        repository_shell = next(
            tool
            for tool in discovered.tools
            if tool.name == "factory_repository_run_shell"
        )
        self.assertEqual(
            repository_shell.input_schema["properties"]["script"]["maxLength"],
            65536,
        )
        self.assertTrue(repository_shell.annotations.destructive_hint)
        semantic_debt = next(
            tool
            for tool in discovered.tools
            if tool.name == "factory_report_semantic_debt"
        )
        self.assertEqual(
            semantic_debt.input_schema["properties"]["limit"]["maximum"], 100
        )
        self.assertTrue(semantic_debt.annotations.read_only_hint)
        registry = next(
            tool
            for tool in discovered.tools
            if tool.name == "factory_get_acceptance_registry"
        )
        self.assertEqual(
            registry.input_schema["properties"]["detail"]["default"],
            "summary",
        )
        facts = next(
            tool
            for tool in discovered.tools
            if tool.name == "factory_query_accepted_facts"
        )
        self.assertEqual(
            facts.input_schema["properties"]["detail"]["default"],
            "summary",
        )

        mutating = {
            "factory_analysis_call": (False, False, False),
            "factory_create_workspace": (False, False, True),
            "factory_workspace_apply_patch": (False, False, False),
            "factory_workspace_run_shell": (False, True, False),
            "factory_repository_run_shell": (False, True, False),
            "factory_discard_workspace": (False, True, True),
            "factory_submit_replay": (False, False, True),
            "factory_cancel_job": (False, True, True),
        }
        for tool in discovered.tools:
            with self.subTest(tool=tool.name):
                expected = mutating.get(tool.name, (True, False, True))
                self.assertEqual(
                    (
                        tool.annotations.read_only_hint,
                        tool.annotations.destructive_hint,
                        tool.annotations.idempotent_hint,
                    ),
                    expected,
                )
                self.assertFalse(tool.annotations.open_world_hint)
                self.assertTrue(tool.description)

    async def test_structured_read_and_model_visible_error(self) -> None:
        async with Client(build_mcp_server(self.config)) as client:
            description = await client.call_tool("factory_describe")
            registry_summary = await client.call_tool(
                "factory_get_acceptance_registry"
            )
            registry_full = await client.call_tool(
                "factory_get_acceptance_registry", {"detail": "full"}
            )
            failure = await client.call_tool(
                "factory_get_job", {"job_id": "job:" + "0" * 32}
            )
            repository_failure = await client.call_tool(
                "factory_inspect_repository", {"repository_id": "th08"}
            )
            knowledge = await client.call_tool(
                "factory_query_knowledge", {"limit": 1, "offset": 0}
            )
        self.assertFalse(description.is_error)
        self.assertFalse(registry_summary.is_error)
        self.assertNotIn("entries", registry_summary.structured_content)
        self.assertEqual(registry_summary.structured_content["detail"], "summary")
        self.assertFalse(registry_full.is_error)
        self.assertIn("entries", registry_full.structured_content)
        self.assertEqual(description.structured_content["policy_id"], "strict-live-v1")
        self.assertTrue(description.structured_content["workspace"]["enabled"])
        self.assertTrue(description.structured_content["repository_work"]["enabled"])
        self.assertEqual(
            description.structured_content["repository_work"]["git_push"],
            "unavailable",
        )
        self.assertEqual(
            knowledge.structured_content["authority"],
            "factory-published-cross-game",
        )
        self.assertEqual(
            knowledge.structured_content["publication_interface"], "none"
        )
        self.assertFalse(knowledge.structured_content["game_local_input_included"])
        rendered = json.dumps(description.structured_content)
        self.assertNotIn(str(self.root), rendered)
        self.assertTrue(failure.is_error)
        self.assertIn("unknown job_id", failure.content[0].text)
        self.assertTrue(repository_failure.is_error)
        self.assertNotIn(str(self.root), repository_failure.content[0].text)
        self.assertIn("<operator-path>", repository_failure.content[0].text)

    @unittest.skipUnless(shutil.which("bwrap"), "bubblewrap is not installed")
    async def test_live_repository_shell_creates_a_reviewable_git_checkpoint(self) -> None:
        async with Client(build_mcp_server(self.config)) as client:
            before = await client.call_tool(
                "factory_get_repository_status", {"repository_id": "th08"}
            )
            command = await client.call_tool(
                "factory_repository_run_shell",
                {
                    "repository_id": "th08",
                    "script": (
                        "printf 'web checkpoint\\n' > checkpoint.txt\n"
                        "git add checkpoint.txt\n"
                        "git commit -m 'gpt-web: checkpoint through MCP'\n"
                    ),
                    "relative_cwd": ".",
                    "timeout_seconds": 5,
                },
            )
            after = await client.call_tool(
                "factory_get_repository_status", {"repository_id": "th08"}
            )
        self.assertFalse(before.is_error)
        self.assertFalse(command.is_error)
        self.assertFalse(after.is_error)
        result = command.structured_content
        self.assertEqual(result["head_relation"], "advanced")
        self.assertEqual(
            result["created_commits"][0]["subject"],
            "gpt-web: checkpoint through MCP",
        )
        self.assertNotEqual(
            before.structured_content["head_commit"],
            after.structured_content["head_commit"],
        )
        self.assertTrue(result["after"]["git_commit_is_checkpoint_only"])

    def test_bearer_token_has_minimum_length_floor(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least 32"):
            BearerTokenMiddleware(object(), "short")

    def test_http_auth_defaults_safe_and_none_is_explicit(self) -> None:
        defaults = build_parser().parse_args(
            ["--config", str(self.config), "--transport", "streamable-http"]
        )
        self.assertEqual(defaults.auth, "bearer")
        self.assertEqual(defaults.mcp_path, "/mcp")

        app = object()
        public = build_parser().parse_args(
            [
                "--config",
                str(self.config),
                "--transport",
                "streamable-http",
                "--auth",
                "none",
                "--mcp-path",
                "/touhou-reconstruction-factory-mcp",
            ]
        )
        self.assertEqual(public.auth, "none")
        self.assertEqual(public.mcp_path, "/touhou-reconstruction-factory-mcp")
        self.assertIs(configure_http_auth(app, public.auth, ""), app)

    def test_mcp_path_rejects_ambiguous_routes(self) -> None:
        for value in (
            "mcp",
            "/",
            "/mcp/",
            "//mcp",
            "/mcp//v1",
            "/mcp?q=1",
            "/mcp path",
            "/mcp%2Fhidden",
        ):
            with self.subTest(value=value):
                with self.assertRaisesRegex(argparse.ArgumentTypeError, "MCP path"):
                    mcp_path(value)

    async def test_bearer_middleware_rejects_wrong_token_and_forwards_exact_token(
        self,
    ) -> None:
        calls = 0

        async def app(_scope, _receive, send):
            nonlocal calls
            calls += 1
            await send({"type": "http.response.start", "status": 204, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        token = "a" * 32
        middleware = BearerTokenMiddleware(app, token)

        async def request(authorization: bytes) -> int:
            messages = []

            async def receive():
                return {"type": "http.request", "body": b""}

            async def send(message):
                messages.append(message)

            await middleware(
                {
                    "type": "http",
                    "method": "POST",
                    "headers": [(b"authorization", authorization)],
                },
                receive,
                send,
            )
            return messages[0]["status"]

        self.assertEqual(await request(b"Bearer wrong"), 401)
        self.assertEqual(await request(f"Bearer {token}".encode()), 204)
        self.assertEqual(calls, 1)


if __name__ == "__main__":
    unittest.main()
