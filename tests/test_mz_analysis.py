from __future__ import annotations

import hashlib
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
import unittest

from reconstruction_factory.errors import AnalysisError
from reconstruction_factory.mz_analysis import inspect_mz_target, validate_mz_attestation
from reconstruction_factory.ontology import TargetIdentity


class MzAnalysisTests(unittest.TestCase):
    def fixture(self, root, mutation=None):
        data = bytearray(192)
        struct.pack_into("<14H", data, 0, 0x5A4D, 192, 1, 1, 4, 0, 0xFFFF,
                         0, 0, 0, 4, 0, 28, 0)
        struct.pack_into("<HH", data, 28, 2, 0)
        struct.pack_into("<H", data, 66, 0x1234)
        if mutation:
            mutation(data)
        path = root / "target.exe"
        path.write_bytes(data)
        target = TargetIdentity(id="target:th03-main", project_id="th03",
                                product_id="th03-main", game="th03", version="unknown",
                                region="japanese-local-attested", format="mz", size=len(data),
                                sha256=hashlib.sha256(data).hexdigest(),
                                md5=hashlib.md5(data, usedforsecurity=False).hexdigest())
        return path, target

    def marker(self, disk):
        return ("FACTORY_GHIDRA_MZ_ATTESTATION_V1:"
                f"{disk['sha256']}:{disk['md5']}:{disk['size']}:{disk['header_size']}:"
                f"{disk['load_size']}:{disk['cs']:04x}:{disk['ip']:04x}:"
                f"{disk['relocation_count']}:{disk['load_sha256']}:"
                f"{disk['relocated_sha256']}:{disk['sample_count']}")

    def test_relocation_and_marker_bind_the_same_loaded_image(self):
        with TemporaryDirectory() as temporary:
            path, target = self.fixture(Path(temporary))
            disk = inspect_mz_target(path, target)
            relocated = bytearray(path.read_bytes()[64:])
            struct.pack_into("<H", relocated, 2, 0x2234)
            self.assertEqual(disk["relocated_sha256"], hashlib.sha256(relocated).hexdigest())
            marker = self.marker(disk)
            self.assertEqual(validate_mz_attestation(marker, disk, target)["status"], "passed")
            for bad in ("", marker + "\n" + marker, marker[:-1] + "0"):
                with self.assertRaises(AnalysisError):
                    validate_mz_attestation(bad, disk, target)

    def test_rejects_header_relocation_and_entry_corruption_with_rehashed_identity(self):
        for offset, value in ((8, 0), (24, 63), (28, 129), (22, 0xFFFF), (4, 2)):
            with self.subTest(offset=offset), TemporaryDirectory() as temporary:
                path, target = self.fixture(Path(temporary),
                    lambda data: struct.pack_into("<H", data, offset, value))
                with self.assertRaises(AnalysisError):
                    inspect_mz_target(path, target)

    def test_rejects_private_target_drift(self):
        with TemporaryDirectory() as temporary:
            path, target = self.fixture(Path(temporary))
            path.write_bytes(path.read_bytes() + b"x")
            with self.assertRaises(AnalysisError):
                inspect_mz_target(path, target)
