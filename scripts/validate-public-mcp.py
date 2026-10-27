#!/usr/bin/env python3
"""Exercise the real public MCP relays without MagicDNS or an HTTP proxy.

Set FACTORY_MCP_URL privately. DNS-over-HTTPS may use the operator proxy; every
MCP request bypasses proxies, pins a global relay IP and verifies TLS normally.
Reports can contain repository state and should stay in ignored operator state.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import ipaddress
import json
import os
from pathlib import Path
import subprocess
import time
from urllib.parse import urlsplit


def public_ip(value: str) -> str:
    address = ipaddress.ip_address(value)
    if not address.is_global:
        raise ValueError("relay address must be globally routable")
    return str(address)


def resolve_public(host: str) -> list[str]:
    response = subprocess.run(
        ["curl", "--silent", "--show-error", "--max-time", "20", "--get",
         "https://dns.google/resolve", "--data-urlencode", f"name={host}",
         "--data-urlencode", "type=A"], capture_output=True, text=True, check=True,
    )
    dns = json.loads(response.stdout)
    if dns.get("Status") != 0:
        raise ValueError("external DNS lookup failed")
    addresses = sorted({public_ip(a["data"]) for a in dns.get("Answer", []) if a["type"] == 1})
    if not addresses:
        raise ValueError("external DNS returned no public IPv4 relay addresses")
    return addresses


class PublicClient:
    def __init__(self, url: str, address: str) -> None:
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or not parsed.hostname or parsed.port not in {None, 443}
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.path in {"", "/"}):
            raise ValueError("expected a private HTTPS MCP URL on port 443")
        self.url, self.host, self.address = url, parsed.hostname, public_ip(address)
        self.calls: list[dict] = []

    def rpc(self, method: str, params: dict | None = None) -> dict:
        payload = {"jsonrpc": "2.0", "id": len(self.calls) + 1,
                   "method": method, "params": params or {}}
        address = f"[{self.address}]" if ":" in self.address else self.address
        started = time.monotonic()
        result = subprocess.run(
            ["curl", "--noproxy", "*", "--resolve", f"{self.host}:443:{address}",
             "--silent", "--show-error", "--connect-timeout", "10", "--max-time", "360",
             "-H", "Content-Type: application/json", "-H", "Accept: application/json, text/event-stream",
             "-d", json.dumps(payload), "-w", "\n%{json}", self.url],
            capture_output=True, text=True, check=False,
        )
        if result.returncode:
            raise RuntimeError(f"public transport failed: curl exit {result.returncode}")
        body, statistics = result.stdout.rsplit("\n", 1)
        stats = json.loads(statistics)
        if (stats["http_code"] != 200 or stats["ssl_verify_result"] != 0
                or ipaddress.ip_address(stats["remote_ip"]) != ipaddress.ip_address(self.address)):
            raise RuntimeError("HTTP, TLS verification or connected public IP check failed")
        if body.lstrip().startswith("{"):
            answer = json.loads(body)
        else:
            events = [json.loads(line[5:].strip()) for line in body.splitlines() if line.startswith("data:")]
            answer = next(event for event in events if event.get("id") == payload["id"])
        if answer.get("id") != payload["id"] or "error" in answer:
            raise RuntimeError("MCP response ID mismatch or JSON-RPC error")
        self.calls.append({"method": method, "params": params, "answer": answer,
                           "remote_ip": stats["remote_ip"], "ssl_verify_result": 0,
                           "http_code": 200, "seconds": round(time.monotonic() - started, 3)})
        return answer["result"]

    def call(self, name: str, arguments: dict | None = None) -> dict:
        result = self.rpc("tools/call", {"name": name, "arguments": arguments or {}})
        if result.get("isError"):
            # Full provider diagnostics remain in the private report.
            raise RuntimeError(f"{name} returned an MCP tool error")
        structured = result.get("structuredContent")
        if not isinstance(structured, dict):
            raise RuntimeError(f"{name} did not return structured content")
        return structured


def check_repository(url: str, address: str, repository: dict, shell: bool, analysis: bool) -> dict:
    client = PublicClient(url, address)
    game = repository["id"]
    checks = []

    def run(label, function):
        try:
            function()
            checks.append({"check": label, "ok": True})
        except Exception as error:
            checks.append({"check": label, "ok": False, "error": str(error)})

    run("status", lambda: client.call("factory_get_repository_status", {"repository_id": game}))
    run("inspect", lambda: client.call("factory_inspect_repository", {"repository_id": game}))
    if shell:
        def shell_probe():
            script = (
                "if [ -x scripts/repo-python ]; then factory_probe_python=scripts/repo-python; "
                "else factory_probe_python=python3; fi\n"
                '"$factory_probe_python" -c \'import pathlib; '
                'assert pathlib.Path("AGENTS.md").is_file(); '
                'print("FACTORY_PUBLIC_SHELL_OK")\''
            )
            command = client.call("factory_repository_run_shell", {
                "repository_id": game, "script": script, "timeout_seconds": 30,
            })
            if (command["exit_code"] != 0 or command["timed_out"]
                    or command["before"]["head_commit"] != command["after"]["head_commit"]
                    or command["before"]["status_sha256"] != command["after"]["status_sha256"]):
                raise RuntimeError("read-only repository shell failed or changed repository state")
            output = client.call("factory_get_repository_command_output", {
                "repository_id": game, "command_id": command["command_id"],
            })
            if "FACTORY_PUBLIC_SHELL_OK" not in json.dumps(output):
                raise RuntimeError("durable shell output marker is missing")
        run("shell-and-durable-output", shell_probe)
    if analysis:
        def providers_probe():
            providers = client.call("factory_list_analysis_providers", {"repository_id": game})
            if not providers["analysis_providers"]:
                raise RuntimeError("repository has no registered analysis provider")
            for provider in providers["analysis_providers"]:
                def query():
                    client.call("factory_list_analysis_operations", {
                        "analysis_provider_id": provider["id"], "limit": 100,
                    })
                    ida = "ida" in provider["backend"]
                    arguments = {"offset": 0, "count": 1} if ida else {"offset": 0, "limit": 1}
                    result = client.call("factory_analysis_call", {
                        "analysis_provider_id": provider["id"], "operation": "list_functions",
                        "arguments_json": json.dumps(arguments),
                    })
                    if (result["target"]["id"] != provider["target_identity_id"]
                            or result["exactness_credit"] != "none"):
                        raise RuntimeError("analysis repository selection or authority mismatch")
                run("analysis:" + provider["id"], query)
        run("analysis-discovery", providers_probe)
    return {"repository_id": game, "checks": checks, "calls": client.calls}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-ip", action="append", default=[])
    parser.add_argument("--expected-repository", action="append", default=[])
    parser.add_argument("--shell", action="store_true")
    parser.add_argument("--analysis", action="store_true")
    parser.add_argument("--workers", type=int, choices=(1, 2, 3), default=1)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    url = os.environ.get("FACTORY_MCP_URL", "")
    host = urlsplit(url).hostname
    if not host:
        parser.error("set FACTORY_MCP_URL in private operator state")
    addresses = [public_ip(a) for a in args.public_ip] or resolve_public(host)
    report = {"public_ips": addresses, "transport": [], "repositories": []}
    inventory = None
    for address in addresses:
        client = PublicClient(url, address)
        client.rpc("initialize", {
            "protocolVersion": "2025-11-25", "capabilities": {},
            "clientInfo": {"name": "factory-public-validation", "version": "1"},
        })
        tools = client.rpc("tools/list")["tools"]
        current = client.call("factory_list_repositories")["repositories"]
        if inventory is not None and current != inventory:
            raise RuntimeError("repository inventory differs between public relays")
        inventory = current
        report["transport"].append({"public_ip": address, "tool_count": len(tools), "calls": client.calls})
        print(f"Public relay {address}: TLS, initialize, {len(tools)} tools and repository discovery passed", flush=True)
    expected = set(args.expected_repository)
    if expected and {r["id"] for r in inventory} != expected:
        raise RuntimeError("public repository inventory differs from the explicit expected set")
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = pool.map(lambda r: check_repository(url, addresses[0], r, args.shell, args.analysis), inventory)
        for result in results:
            report["repositories"].append(result)
            failures = [c["check"] for c in result["checks"] if not c["ok"]]
            print(result["repository_id"], "FAIL " + ", ".join(failures) if failures else "PASS", flush=True)
            args.report.write_text(json.dumps(report, indent=2) + "\n")
            args.report.chmod(0o600)
    failed = sum(not c["ok"] for r in report["repositories"] for c in r["checks"])
    print(f"Checked {len(inventory)} repositories; {failed} failed checks", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
