"""Check executable plugin wiring without freezing instructions or prose."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugins/touhou-reconstruction-factory'


class PluginWiringTests(unittest.TestCase):
    def test_registered_app_reference_resolves(self):
        manifest = json.loads((PLUGIN / '.codex-plugin/plugin.json').read_text())
        app_file = (PLUGIN / manifest['apps']).resolve()
        self.assertTrue(app_file.is_relative_to(PLUGIN))
        apps = json.loads(app_file.read_text())['apps']
        self.assertTrue(apps)
        for app in apps.values():
            self.assertTrue(app['id'].startswith('asdk_app_'))
            self.assertIsInstance(app['required'], bool)
