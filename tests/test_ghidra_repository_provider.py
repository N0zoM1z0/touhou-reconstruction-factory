"""Exercise standalone project dispatch without a game-specific Python frontend."""

from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest


PROVIDER = Path(__file__).resolve().parents[1] / "scripts/ghidra-repository-provider.py"


class StandaloneGhidraTests(unittest.TestCase):
    def test_standalone_text_queries_and_context_use_shared_scripts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config").mkdir()
            (root / "config/target.toml").write_text('[target]\nfilename = "EFZ.exe"\n')
            (root / "ghidra-project").mkdir()
            (root / ".tools/jdk").mkdir(parents=True)
            analyzer = root / ".tools/ghidra/support/analyzeHeadless"
            analyzer.parent.mkdir(parents=True)
            analyzer.write_text(f"#!{sys.executable}\n" + '''
import json,os,sys
from pathlib import Path
Path('observed.json').write_text(json.dumps({'argv':sys.argv[1:],'java':os.environ['JAVA_HOME']}))
for i,arg in enumerate(sys.argv):
    if arg=='-postScript': Path(sys.argv[i+2]).write_text(sys.argv[i+1]+'\\n')
''')
            analyzer.chmod(0o755)
            output = root / "result.txt"
            command = [sys.executable, str(PROVIDER), "--repository", str(root), "--standalone-project"]
            subprocess.run(command + ["query", str(output), "search_strings", "5", "0xABC"],
                           capture_output=True, text=True, check=True)
            observed = json.loads((root / "observed.json").read_text())
            self.assertIn("text:0xABC", observed["argv"])
            self.assertIn("FactoryQueryProgram.java", observed["argv"])
            self.assertIn("-readOnly", observed["argv"])
            self.assertIn("-noanalysis", observed["argv"])
            self.assertEqual(observed["java"], str(root / ".tools/jdk"))
            subprocess.run(command + ["function_context", str(output), "0x405a21"],
                           capture_output=True, text=True, check=True)
            text = output.read_text()
            for operation in ("function", "callers", "callees", "decompile"):
                self.assertIn(f"=== {operation} ===", text)
            self.assertIn("FactoryDecompileFunctions.java", text)
            self.assertTrue((root / ".analysis/ghidra/headless.lock").exists())
            result = subprocess.run(command + ["--mz-artifact", "other", "check"], capture_output=True)
            self.assertEqual(result.returncode, 2)
