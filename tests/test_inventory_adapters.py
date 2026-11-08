from pathlib import Path
import tempfile
import unittest

from reconstruction_factory.inspection_adapters import inspect_repository
from reconstruction_factory.adapters.inventory import Th05ManifestRepositoryAdapter
from reconstruction_factory.errors import AdapterError
from reconstruction_factory.factory import kit_for_snapshot
from reconstruction_factory.ontology import ClaimType
from reconstruction_factory.providers.base import Capability

from test_adapters import HASH_A, make_th04, write


class InventoryAdapterTests(unittest.TestCase):
    def make_pe(self, root, game="th20"):
        write(root, "config/target.toml", f'''[target]
filename = "{game}.exe"
title = "test"
version = "1.00a"
region = "japanese"
size = 4096
sha256 = "{HASH_A}"
[pe]
machine = "i386"
image_base = "0x00400000"
entry_point = "0x00401000"
''')
        write(root, "config/tools.lock.toml", "schema_version = 1\n")
        write(root, "config/functions.csv",
              "address,size,name,status,source_file\n0x00401000,16,NativeFn,matching,src/game.cpp\n")
        write(root, "config/matches.csv", "address,size\n0x00401000,16\n")

    def test_native_matching_status_grants_only_provisional_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for game in ("th06", "th07", "th11", "th16", "th20"):
                self.make_pe(root, game)
                snapshot = inspect_repository(root)
                self.assertEqual(snapshot.adapter_id, "windows-pe-inventory-v1")
                self.assertEqual(snapshot.targets[0].id, f"target:{game}-main")
                self.assertEqual({c.type for c in snapshot.claims}, {ClaimType.BOUNDARY_EXTENT})
                self.assertFalse(snapshot.oracle_results)
                kit = kit_for_snapshot(snapshot)
                self.assertNotIn(Capability.STANDALONE_COFF_MATCH, kit.capabilities)

    def test_duplicate_or_negative_inventory_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_pe(root)
            for rows in ("0x00401000,1\n0x401000,2\n", "0x00401000,-1\n"):
                write(root, "config/functions.csv", "address,size\n" + rows)
                with self.assertRaises(AdapterError):
                    inspect_repository(root)

    def test_efz_preserves_uncertain_native_release_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_pe(root, "EFZ")
            manifest = root / "config/target.toml"
            manifest.write_text(manifest.read_text().replace('version = "1.00a"\n', '')
                                .replace('region = "japanese"\n', '')
                                .replace('[pe]', 'version_status = "4.02 candidate"\n[pe]'))
            snapshot = inspect_repository(root)
            self.assertEqual(snapshot.targets[0].id, "target:efz-main")
            self.assertEqual(snapshot.targets[0].version, "unknown")
            self.assertEqual(snapshot.targets[0].region, "unknown")
            self.assertEqual(snapshot.targets[0].metadata["native_target"]["version_status"], "4.02 candidate")
            self.assertFalse(snapshot.oracle_results)
            self.assertEqual({claim.type for claim in snapshot.claims}, {ClaimType.BOUNDARY_EXTENT})
            kit_for_snapshot(snapshot)

    def test_inventory_fingerprint_changes_with_native_extent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_pe(root)
            before = inspect_repository(root).input_fingerprint_sha256
            write(root, "config/functions.csv", "address,size\n0x00401000,17\n")
            self.assertNotEqual(before, inspect_repository(root).input_fingerprint_sha256)

    def test_th05_control_artifacts_do_not_steal_another_game_registration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_th04(root)
            path = root / "config/targets.toml"
            path.write_text(path.read_text() + f'''
[[artifacts]]
id = "th05-main-smoke"
game = "th05"
role = "oracle-smoke"
format = "mz"
size = 512
sha256 = "{HASH_A}"
''')
            self.assertFalse(Th05ManifestRepositoryAdapter().detect(root))
            self.assertEqual(inspect_repository(root).project.id, "th04")

    def test_th05_manifest_keeps_unknown_version_and_no_acceptance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_th04(root)
            for name in ("config/targets.toml", "config/toolchain.toml"):
                path = root / name
                path.write_text(path.read_text().replace("th04", "th05").replace('role = "gameplay"', 'role = "reconstruction"'))
            (root / "config/th04_function_boundaries.csv").unlink()
            snapshot = inspect_repository(root)
            self.assertEqual(snapshot.adapter_id, "th05-pc98-manifest-v1")
            self.assertEqual([t.id for t in snapshot.targets], ["target:th05-main"])
            self.assertEqual(snapshot.targets[0].version, "unknown")
            self.assertFalse(snapshot.claims)
            self.assertFalse(snapshot.oracle_results)
            kit_for_snapshot(snapshot)
