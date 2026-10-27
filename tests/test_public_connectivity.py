import importlib.util
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch


def script(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parents[1] / "scripts" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


public = script("validate-public-mcp")


class PublicConnectivityTests(unittest.TestCase):
    def test_rejects_tailnet_loopback_and_private_destinations(self):
        for address in ("100.64.0.1", "127.0.0.1", "192.168.1.1", "::1"):
            with self.subTest(address=address), self.assertRaises(ValueError):
                public.public_ip(address)

    def test_rpc_pins_public_ip_bypasses_proxies_and_preserves_tls_hostname(self):
        response = {"jsonrpc": "2.0", "id": 1, "result": {"tools": []}}
        statistics = {"http_code": 200, "remote_ip": "1.1.1.1", "ssl_verify_result": 0}
        completed = subprocess.CompletedProcess([], 0, json.dumps(response) + "\n" + json.dumps(statistics), "")
        with patch.object(public.subprocess, "run", return_value=completed) as run:
            client = public.PublicClient("https://example.invalid/private", "1.1.1.1")
            self.assertEqual(client.rpc("tools/list"), {"tools": []})
        command = run.call_args.args[0]
        self.assertEqual(command[command.index("--noproxy") + 1], "*")
        self.assertEqual(command[command.index("--resolve") + 1], "example.invalid:443:1.1.1.1")
        self.assertEqual(command[-1], "https://example.invalid/private")
        self.assertNotIn("--insecure", command)

    def test_rpc_rejects_wrong_destination_tls_errors_and_http_errors(self):
        for stats in (
            {"http_code": 200, "remote_ip": "100.64.0.1", "ssl_verify_result": 0},
            {"http_code": 200, "remote_ip": "1.1.1.1", "ssl_verify_result": 60},
            {"http_code": 502, "remote_ip": "1.1.1.1", "ssl_verify_result": 0},
        ):
            completed = subprocess.CompletedProcess([], 0, '{}\n' + json.dumps(stats), "")
            with patch.object(public.subprocess, "run", return_value=completed), self.assertRaises(RuntimeError):
                public.PublicClient("https://example.invalid/private", "1.1.1.1").rpc("tools/list")
