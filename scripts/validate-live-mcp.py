#!/usr/bin/env python3
"""Validate the deployed Factory MCP without accepting false success."""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
import re
from typing import Any
from uuid import uuid4

from mcp import Client


DEFAULT_URL = os.environ.get("FACTORY_MCP_URL")
REPOSITORIES = {
    "th04": "th04-pc98-v1",
    "th08": "th08-vc7-ledgers-v1",
    "th09": "windows-pe-ledgers-v1",
    "th095": "windows-pe-ledgers-v1",
    "th105": "windows-pe-ledgers-v1",
}
REQUIRED_HISTORICAL_FIXTURE_REPOSITORIES = {"th04", "th08", "th095", "th105"}
EXPECTED_TOOLS = {
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
}
MUTATING_ANNOTATIONS = {
    "factory_analysis_call": (False, False, False),
    "factory_create_workspace": (False, False, True),
    "factory_workspace_apply_patch": (False, False, False),
    "factory_workspace_run_shell": (False, True, False),
    "factory_repository_run_shell": (False, True, False),
    "factory_discard_workspace": (False, True, True),
    "factory_submit_replay": (False, False, True),
    "factory_cancel_job": (False, True, True),
}
CAPABILITY = re.compile(r"^workspace:[0-9a-f]{32}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
GIT_OBJECT = re.compile(r"^[0-9a-f]{40,64}$")
TERMINAL_JOBS = {"completed", "failed", "cancelled"}


def _check(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


async def _call(
    client: Client,
    name: str,
    arguments: dict[str, Any] | None = None,
    *,
    read_timeout_seconds: int = 120,
) -> dict[str, Any]:
    result = await client.call_tool(
        name,
        arguments or {},
        read_timeout_seconds=read_timeout_seconds,
    )
    if result.is_error:
        detail = "\n".join(
            block.text
            for block in result.content
            if getattr(block, "type", None) == "text"
        )
        raise RuntimeError(f"{name} failed: {detail}")
    _check(
        isinstance(result.structured_content, dict),
        f"{name} did not return structured content",
    )
    return result.structured_content


async def _discovery_and_read_only(url: str, report: dict[str, Any]) -> None:
    async with Client(url, read_timeout_seconds=120) as client:
        discovery = await client.list_tools()
        tools = {tool.name: tool for tool in discovery.tools}
        _check(set(tools) == EXPECTED_TOOLS, "deployed MCP tool inventory drifted")
        for name, tool in tools.items():
            annotations = tool.annotations.model_dump(by_alias=True)
            expected = MUTATING_ANNOTATIONS.get(name, (True, False, True))
            observed = (
                annotations["readOnlyHint"],
                annotations["destructiveHint"],
                annotations["idempotentHint"],
            )
            _check(observed == expected, f"incorrect annotations for {name}")
            _check(annotations["openWorldHint"] is False, f"open-world tool: {name}")
        schemas = json.dumps(
            [tool.input_schema for tool in tools.values()], sort_keys=True
        )
        for forbidden in ('"command"', '"cwd"', '"path"'):
            _check(forbidden not in schemas, f"host-authority field exposed: {forbidden}")

        description = await _call(client, "factory_describe")
        _check(description["policy_id"] == "strict-live-v1", "unexpected policy")
        described = {item["id"] for item in description["repositories"]}
        _check(described == set(REPOSITORIES), "repository inventory drifted")
        _check(description["workspace"]["enabled"] is True, "workspace is disabled")
        _check(
            description["repository_work"]["enabled"] is True,
            "live repository work is disabled",
        )
        _check(
            description["repository_work"]["git_commit"] == "available"
            and description["repository_work"]["git_push"] == "unavailable",
            "live repository Git boundary drifted",
        )

        repository_report: dict[str, Any] = {}
        for repository_id, adapter_id in REPOSITORIES.items():
            worktree = await _call(
                client,
                "factory_get_repository_status",
                {"repository_id": repository_id},
            )
            _check(
                worktree["repository_id"] == repository_id,
                "live repository status identity mismatch",
            )
            _check(
                GIT_OBJECT.fullmatch(worktree["head_commit"]) is not None
                and DIGEST.fullmatch(worktree["status_sha256"]) is not None,
                "live repository status has an invalid identity",
            )
            inspected = await _call(
                client,
                "factory_inspect_repository",
                {"repository_id": repository_id},
            )
            _check(inspected["id"] == repository_id, "repository identity mismatch")
            _check(inspected["adapter_id"] == adapter_id, "adapter identity mismatch")
            _check(inspected["counts"]["claims"] > 0, "repository has no claims")
            _check(
                inspected["counts"]["imported_oracle_results"] == 0,
                "adapter manufactured oracle results",
            )
            _check(
                DIGEST.fullmatch(inspected["input_fingerprint_sha256"]) is not None,
                "invalid repository fingerprint",
            )
            claims = await _call(
                client,
                "factory_list_claims",
                {"repository_id": repository_id, "limit": 1, "offset": 0},
            )
            _check(claims["total"] == inspected["counts"]["claims"], "claim drift")
            product_closure_claim = None
            semantic_debt_report = None
            if repository_id == "th095":
                semantic_debt = await _call(
                    client,
                    "factory_report_semantic_debt",
                    {
                        "repository_id": repository_id,
                        "relative_path": "src",
                        "category": "all",
                        "limit": 5,
                        "offset": 0,
                    },
                )
                _check(
                    semantic_debt["repository_id"] == repository_id
                    and semantic_debt["routing_only"] is True
                    and semantic_debt["completion_metric"] is False
                    and semantic_debt["exactness_credit"] == "none"
                    and semantic_debt["semantic_evidence_credit"] == "none",
                    "TH095 semantic-debt authority boundary drifted",
                )
                _check(
                    semantic_debt["source_binding"]["head_commit"]
                    == worktree["head_commit"]
                    and semantic_debt["source_binding"]["status_sha256"]
                    == worktree["status_sha256"],
                    "TH095 semantic-debt report is not bound to live repository state",
                )
                _check(
                    set(semantic_debt["category_counts"])
                    == {
                        "raw-member-access",
                        "absolute-address",
                        "anonymous-identifier",
                        "opaque-storage",
                    },
                    "TH095 semantic-debt category contract drifted",
                )
                semantic_debt_report = {
                    "scan_profile": semantic_debt["scan_profile"],
                    "scope": semantic_debt["scope"],
                    "scope_complete": semantic_debt["scope_complete"],
                    "files_scanned": semantic_debt["files_scanned"],
                    "category_counts": semantic_debt["category_counts"],
                    "findings": semantic_debt["findings"]["total"],
                    "report_sha256": semantic_debt["report_sha256"],
                }
                product_claims = await _call(
                    client,
                    "factory_list_claims",
                    {
                        "repository_id": repository_id,
                        "claim_type": "whole_build_closed",
                        "limit": 5,
                        "offset": 0,
                    },
                )
                _check(
                    product_claims["total"] == 1
                    and len(product_claims["items"]) == 1,
                    "TH095 product-closure claim is not unique",
                )
                product_item = product_claims["items"][0]
                product_claim = product_item["claim"]
                product_subject = product_item["subject"]
                _check(
                    product_claim["id"]
                    == "claim:th095-main:product:whole-build-closed"
                    and product_claim["evidence_class"] == "unknown"
                    and product_claim["value"]
                    == {
                        "closed": True,
                        "compile_machine": "i386-coff",
                        "link_output": "pe32-i386-windows-gui",
                        "profile_count": 2,
                        "source_count": 88,
                        "whole_image_exact": False,
                        "zero_unresolved_required": True,
                    },
                    "TH095 product-closure claim contract drifted",
                )
                _check(
                    product_subject["kind"] == "product"
                    and product_subject["extents"] == [],
                    "TH095 product closure must use an extent-free product subject",
                )
                product_closure_claim = product_claim["id"]
            snapshot = await _call(
                client,
                "factory_get_accepted_snapshot",
                {"repository_id": repository_id},
            )
            repository_report[repository_id] = {
                "adapter_id": adapter_id,
                "claims": claims["total"],
                "targets": inspected["target_identity_ids"],
                "accepted_oracle_results": len(snapshot["oracle_results"]),
                "input_fingerprint_sha256": inspected["input_fingerprint_sha256"],
                "product_closure_claim": product_closure_claim,
                "semantic_debt_report": semantic_debt_report,
                "live_worktree": {
                    "head_commit": worktree["head_commit"],
                    "branch": worktree["branch"],
                    "dirty": worktree["dirty"],
                    "staged_changes": worktree["staged_changes"],
                    "unstaged_changes": worktree["unstaged_changes"],
                    "untracked_files": worktree["untracked_files"],
                    "status_sha256": worktree["status_sha256"],
                },
            }

        registry = await _call(client, "factory_get_acceptance_registry")
        _check(
            registry["counts"]["candidates"]
            == registry["counts"]["accepted"]
            + registry["counts"]["rejected"]
            + registry["counts"]["invalid"],
            "registry counts do not partition every candidate",
        )
        unknown = await _call(
            client,
            "factory_query_knowledge",
            {"status": "unknown", "limit": 100, "offset": 0},
        )
        _check(
            unknown["authority"] == "factory-published-cross-game"
            and unknown["publication_interface"] == "none"
            and unknown["game_local_input_included"] is False,
            "knowledge query crossed the Factory publication boundary",
        )
        _check(unknown["total"] > 0, "unknown knowledge was erased")
        fixtures = {}
        for repository_id in REPOSITORIES:
            page = await _call(
                client,
                "factory_list_historical_fixtures",
                {"project": repository_id, "limit": 100, "offset": 0},
            )
            fixtures[repository_id] = page["total"]
            if repository_id in REQUIRED_HISTORICAL_FIXTURE_REPOSITORIES:
                _check(
                    page["total"] > 0,
                    f"no historical fixtures for {repository_id}",
                )

        report["read_only"] = {
            "tool_count": len(tools),
            "policy_id": description["policy_id"],
            "repositories": repository_report,
            "registry_counts": registry["counts"],
            "unknown_knowledge_entries": unknown["total"],
            "historical_fixtures": fixtures,
        }


async def _analysis(url: str, report: dict[str, Any]) -> None:
    probes = {
        "th04-ghidra": ("check", "target:th04-main"),
        "th08-ida": ("get_metadata", "target:th08-main"),
        "th09-ida": ("get_metadata", "target:th09-main"),
        "th095-ghidra": ("check", "target:th095-main"),
        "th105-ida": ("get_metadata", "target:th105-main"),
    }
    outcomes: dict[str, Any] = {}
    expected_unavailable = {
        "th08-ida": "active IDA database is not TH08",
        "th105-ida": "active IDA database metadata is not canonical TH105",
    }
    async with Client(url, read_timeout_seconds=120) as client:
        listed = await _call(client, "factory_list_analysis_providers")
        providers = {item["id"]: item for item in listed["analysis_providers"]}
        _check(set(providers) == set(probes), "analysis provider inventory drifted")
        for provider_id, (operation, target_id) in probes.items():
            operations = await client.call_tool(
                "factory_list_analysis_operations",
                {"analysis_provider_id": provider_id, "limit": 100, "offset": 0},
                read_timeout_seconds=120,
            )
            if operations.is_error:
                detail = "\n".join(
                    block.text
                    for block in operations.content
                    if getattr(block, "type", None) == "text"
                )
                expected = expected_unavailable.get(provider_id)
                _check(
                    expected is not None and expected in detail,
                    f"unexpected analysis discovery failure for {provider_id}",
                )
                outcomes[provider_id] = {
                    "status": "accurately-unavailable-at-discovery",
                    "target_identity_id": target_id,
                }
                continue
            items = operations.structured_content["items"]
            names = {item["name"] for item in items}
            _check(operation in names, f"{provider_id} omitted {operation}")
            if provider_id == "th09-ida":
                _check(
                    items
                    and all(isinstance(item.get("input_schema"), dict) for item in items),
                    "native TH09 IDA operation schemas are missing",
                )
            result = await client.call_tool(
                "factory_analysis_call",
                {
                    "analysis_provider_id": provider_id,
                    "operation": operation,
                    "arguments_json": "{}",
                },
                read_timeout_seconds=120,
            )
            _check(not result.is_error, f"analysis call failed for {provider_id}")
            payload = result.structured_content
            _check(payload["target"]["id"] == target_id, "analysis target mismatch")
            _check(payload["exactness_credit"] == "none", "analysis gained exactness")
            _check(
                payload["authority"] == "provisional-semantic-analysis",
                "analysis authority drifted",
            )
            bounded_query = None
            if provider_id.endswith("-ghidra"):
                query = await _call(
                    client,
                    "factory_analysis_call",
                    {
                        "analysis_provider_id": provider_id,
                        "operation": "list_functions",
                        "arguments_json": '{"limit":1,"offset":0}',
                    },
                    read_timeout_seconds=300,
                )
                _check(
                    query["target"]["id"] == target_id
                    and query["exactness_credit"] == "none",
                    f"bounded Ghidra query escaped its target for {provider_id}",
                )
                _check(
                    "returned: 1" in query["output"]["text"],
                    f"bounded Ghidra query failed for {provider_id}",
                )
                bounded_query = "list_functions(limit=1)"
            outcomes[provider_id] = {
                "status": "attested-success",
                "target_identity_id": target_id,
                "provider_binding_sha256": payload["provider_binding_sha256"],
                "bounded_query": bounded_query,
            }
    report["analysis"] = outcomes


async def _repository_toolchains(url: str, report: dict[str, Any]) -> None:
    """Exercise every registered legacy toolchain through live-repository Bash.

    These probes prove only that Factory exposes the selected repository's current
    tool environment.  They deliberately do not create Oracle receipts or grant
    exactness credit.
    """

    probes = {
        "th04": (
            "set -euo pipefail\n"
            "probe_dir=$(mktemp -d)\n"
            "trap 'rm -rf -- \"$probe_dir\"' EXIT\n"
            "python3 scripts/attest_toolchain.py --json "
            "--output \"$probe_dir/attestation.json\" >/dev/null\n"
            "python3 - \"$probe_dir/attestation.json\" <<'PY'\n"
            "import json, pathlib, sys\n"
            "report = json.loads(pathlib.Path(sys.argv[1]).read_text())\n"
            "assert report['ready'] is True\n"
            "assert report['identity_pass'] is True\n"
            "assert report['execution_pass'] is True\n"
            "PY\n"
            "printf 'th04 Borland/Wine attestation passed\\n'\n"
        ),
        "th08": (
            "set -euo pipefail\n"
            "test \"$HOME\" = /home/pentester\n"
            "test -d \"$HOME/.wineth08\"\n"
            "output=$(./scripts/wineth08 ./scripts/th08run.bat cl 2>&1)\n"
            "printf '%s\\n' \"$output\" | grep -F 'Microsoft (R)' >/dev/null\n"
            "printf 'th08 VC7/Wine prefix passed\\n'\n"
        ),
        "th095": (
            "set -euo pipefail\n"
            "test \"$WINEPREFIX\" = /home/pentester/.wine\n"
            "probe_dir=$(mktemp -d)\n"
            "trap 'rm -rf -- \"$probe_dir\"' EXIT\n"
            "printf 'extern \"C\" int factory_probe(void) { return 95; }\\n' "
            "> \"$probe_dir/probe.cpp\"\n"
            "scripts/compile-probe.sh \"$probe_dir/probe.cpp\" "
            "\"$probe_dir/probe.obj\" /O2 /GR /EHsc /MT\n"
            "test -s \"$probe_dir/probe.obj\"\n"
            "printf 'th095 VC7.1/Wine probe passed\\n'\n"
        ),
        "th105": (
            "set -euo pipefail\n"
            "probe_dir=$(mktemp -d)\n"
            "trap 'rm -rf -- \"$probe_dir\"' EXIT\n"
            "printf 'extern \"C\" int factory_probe(void) { return 105; }\\n' "
            "> \"$probe_dir/probe.cpp\"\n"
            "scripts/compile-unit.sh \"$probe_dir/probe.cpp\" "
            "\"$probe_dir/probe.obj\"\n"
            "test -s \"$probe_dir/probe.obj\"\n"
            "printf 'th105 VC8 SP1/Wine probe passed\\n'\n"
        ),
    }
    outcomes: dict[str, Any] = {}
    async with Client(url, read_timeout_seconds=900) as client:
        for repository_id, script in probes.items():
            before = await _call(
                client,
                "factory_get_repository_status",
                {"repository_id": repository_id},
            )
            command = await _call(
                client,
                "factory_repository_run_shell",
                {
                    "repository_id": repository_id,
                    "relative_cwd": ".",
                    "timeout_seconds": 600,
                    "script": script,
                },
                read_timeout_seconds=900,
            )
            _check(command["exit_code"] == 0, f"toolchain probe failed for {repository_id}")
            _check(command["timed_out"] is False, f"toolchain probe timed out for {repository_id}")
            _check(
                command["before"]["head_commit"] == command["after"]["head_commit"],
                f"toolchain probe changed HEAD for {repository_id}",
            )
            _check(
                command["before"]["status_sha256"]
                == command["after"]["status_sha256"]
                == before["status_sha256"],
                f"toolchain probe changed tracked or visible untracked state for {repository_id}",
            )
            _check(command["created_commits"] == [], "probe unexpectedly committed")
            outcomes[repository_id] = {
                "status": "passed",
                "command_id": command["command_id"],
                "head_commit": command["after"]["head_commit"],
                "status_sha256": command["after"]["status_sha256"],
                "exactness_credit": "none",
            }
    report["repository_toolchains"] = outcomes


async def _workspace(url: str, report: dict[str, Any]) -> None:
    workspace_id: str | None = None
    command_id: str | None = None
    key = "live-validation-" + uuid4().hex
    marker = "factory-live-validation.txt"
    try:
        async with Client(url, read_timeout_seconds=120) as client:
            created = await _call(
                client,
                "factory_create_workspace",
                {"repository_id": "th105", "idempotency_key": key},
            )
            workspace_id = created["workspace_id"]
            _check(CAPABILITY.fullmatch(workspace_id) is not None, "bad capability")
            reused = await _call(
                client,
                "factory_create_workspace",
                {"repository_id": "th105", "idempotency_key": key},
            )
            _check(reused["workspace_id"] == workspace_id, "idempotency failed")
            await _call(
                client,
                "factory_workspace_read_file",
                {
                    "workspace_id": workspace_id,
                    "relative_path": "README.md",
                    "offset": 0,
                    "limit": 256,
                },
            )
            escaped = await client.call_tool(
                "factory_workspace_read_file",
                {
                    "workspace_id": workspace_id,
                    "relative_path": "../etc/passwd",
                    "offset": 0,
                    "limit": 32,
                },
            )
            _check(escaped.is_error, "workspace traversal unexpectedly succeeded")
            command = await _call(
                client,
                "factory_workspace_run_shell",
                {
                    "workspace_id": workspace_id,
                    "relative_cwd": ".",
                    "timeout_seconds": 30,
                    "script": (
                        "set -eu\n"
                        "test ! -e /home\n"
                        "test ! -e /etc/passwd\n"
                        "test -f .git/HEAD\n"
                        "if printf 'forbidden\\n' > .git/HEAD 2>/dev/null; then "
                        "exit 92; fi\n"
                        "test ! -e .tools\n"
                        "python3 -c 'import socket; s=socket.socket(); "
                        "assert s.connect_ex((\"1.1.1.1\", 53)) != 0'\n"
                        f"printf 'ephemeral validation\\n' > {marker}\n"
                        "printf 'workspace sandbox passed\\n'\n"
                    ),
                },
            )
            command_id = command["command_id"]
            _check(command["exit_code"] == 0, "sandbox command failed")
            _check(command["workspace_committed"] is True, "transaction not committed")

        # A new MCP session must recover both workspace and command state.
        async with Client(url, read_timeout_seconds=120) as client:
            resumed = await _call(
                client, "factory_get_workspace", {"workspace_id": workspace_id}
            )
            output = await _call(
                client,
                "factory_get_workspace_command_output",
                {
                    "workspace_id": workspace_id,
                    "command_id": command_id,
                    "stream": "stdout",
                    "offset": 0,
                    "limit": 16384,
                },
            )
            _check("workspace sandbox passed" in output["text"], "lost output")
            changed = await _call(
                client,
                "factory_get_workspace_diff",
                {"workspace_id": workspace_id, "offset": 0, "limit": 16384},
            )
            _check(marker in changed["text"], "workspace diff lost after reconnect")
            cleanup = await _call(
                client,
                "factory_workspace_run_shell",
                {
                    "workspace_id": workspace_id,
                    "script": f"rm -- {marker}",
                    "relative_cwd": ".",
                    "timeout_seconds": 30,
                },
            )
            _check(cleanup["workspace_committed"] is True, "cleanup did not commit")
            clean = await _call(
                client,
                "factory_get_workspace_diff",
                {"workspace_id": workspace_id, "offset": 0, "limit": 16384},
            )
            _check(clean["size"] == 0, "validation workspace remained dirty")
            discarded = await _call(
                client,
                "factory_discard_workspace",
                {"workspace_id": workspace_id},
            )
            _check(discarded["state"] == "discarded", "discard failed")
            report["workspace"] = {
                "workspace_id": workspace_id,
                "source_git_commit": created["source_git_commit"],
                "source_git_tree": created["source_git_tree"],
                "source_worktree_dirty_observed": created[
                    "source_worktree_dirty_observed"
                ],
                "command_id": command_id,
                "reconnected": resumed["workspace_id"] == workspace_id,
                "final_diff_bytes": clean["size"],
                "final_state": discarded["state"],
            }
            workspace_id = None
    finally:
        if workspace_id is not None:
            async with Client(url, read_timeout_seconds=120) as client:
                await client.call_tool(
                    "factory_discard_workspace", {"workspace_id": workspace_id}
                )


async def _replay_th105(
    url: str,
    report: dict[str, Any],
    idempotency_key: str | None,
) -> None:
    key = idempotency_key or "live-validation-" + uuid4().hex
    async with Client(url, read_timeout_seconds=120) as client:
        claims = await _call(
            client,
            "factory_list_claims",
            {
                "repository_id": "th105",
                "claim_type": "codegen_exact",
                "limit": 100,
                "offset": 0,
            },
        )
        expected_claim = "claim:th105-main:function:00401000:codegen-exact"
        available = {item["claim"]["id"] for item in claims["items"]}
        _check(expected_claim in available, "TH105 smoke claim is unavailable")
        submission = await _call(
            client,
            "factory_submit_replay",
            {
                "repository_id": "th105",
                "claim_id": expected_claim,
                "idempotency_key": key,
            },
        )
        job = submission["job"]
        job_id = job["job_id"]
        for _attempt in range(90):
            job = await _call(client, "factory_get_job", {"job_id": job_id})
            if job["state"] in TERMINAL_JOBS:
                break
            await asyncio.sleep(2)
        _check(job["state"] == "completed", f"replay ended as {job['state']}")
        outcome = job["outcome"]
        _check(outcome["receipt_verdict"] == "pass", "receipt did not pass")
        _check(outcome["acceptance_decision"] == "accepted", "receipt not accepted")
        facts = await _call(
            client,
            "factory_query_accepted_facts",
            {
                "target_identity_id": "target:th105-main",
                "claim_type": "codegen_exact",
                "limit": 100,
                "offset": 0,
            },
        )
        accepted = [
            item
            for item in facts["items"]
            if item["claim"]["claim_id"] == expected_claim
            and item["receipt_id"] == outcome["receipt_id"]
        ]
        _check(len(accepted) == 1, "accepted replay is absent from current facts")
        events = await _call(
            client,
            "factory_get_job_events",
            {"job_id": job_id, "limit": 100, "offset": 0},
        )
        output = await _call(
            client,
            "factory_get_job_output_page",
            {"job_id": job_id, "offset": 0, "limit": 16384},
        )
        report["replay"] = {
            "claim_id": expected_claim,
            "job_id": job_id,
            "state": job["state"],
            "receipt_id": outcome["receipt_id"],
            "receipt_verdict": outcome["receipt_verdict"],
            "acceptance_decision": outcome["acceptance_decision"],
            "registry_id": outcome["registry_id"],
            "event_count": events["total"],
            "artifact_count": len(output["artifacts"]),
            "idempotent_submission_reused": submission["reused"],
        }


async def _main(arguments: argparse.Namespace) -> dict[str, Any]:
    report: dict[str, Any] = {
        "url": arguments.url,
        "observed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    await _discovery_and_read_only(arguments.url, report)
    if arguments.analysis or arguments.all:
        await _analysis(arguments.url, report)
    if arguments.repository_toolchains or arguments.all:
        await _repository_toolchains(arguments.url, report)
    if arguments.workspace or arguments.all:
        await _workspace(arguments.url, report)
    if arguments.replay_th105 or arguments.all:
        await _replay_th105(
            arguments.url,
            report,
            arguments.replay_idempotency_key,
        )
    report["status"] = "pass"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a deployed Factory MCP; mutation checks are opt-in."
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help="private deployment URL (or set FACTORY_MCP_URL)",
    )
    parser.add_argument("--analysis", action="store_true")
    parser.add_argument(
        "--repository-toolchains",
        action="store_true",
        help="run non-committing Wine/toolchain probes in all live repositories",
    )
    parser.add_argument("--workspace", action="store_true")
    parser.add_argument("--replay-th105", action="store_true")
    parser.add_argument(
        "--replay-idempotency-key",
        help="reuse an identical TH105 smoke replay instead of creating a new job",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help=(
            "run analysis, live toolchain, disposable workspace, and TH105 "
            "replay checks"
        ),
    )
    arguments = parser.parse_args()
    if not arguments.url:
        parser.error("--url or FACTORY_MCP_URL is required")
    report = asyncio.run(_main(arguments))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
