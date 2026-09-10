from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).parents[1]


def _load_validate_release():
    path = ROOT / "scripts" / "validate-release.py"
    spec = importlib.util.spec_from_file_location("validate_release", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ValidateReleaseTests(unittest.TestCase):
    def test_tracked_files_omit_worktree_deletions(self) -> None:
        module = _load_validate_release()
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            subprocess.run(["git", "init", "--quiet"], cwd=root, check=True)
            retained = root / "retained.json"
            deleted = root / "deleted.json"
            untracked = root / "untracked.json"
            retained.write_text("{}\n", encoding="utf-8")
            deleted.write_text("{}\n", encoding="utf-8")
            subprocess.run(
                ["git", "add", "retained.json", "deleted.json"],
                cwd=root,
                check=True,
            )
            deleted.unlink()
            untracked.write_text("{}\n", encoding="utf-8")

            module.ROOT = root
            paths = set(module._tracked_files())

            self.assertEqual(paths, {retained, untracked})


if __name__ == "__main__":
    unittest.main()
