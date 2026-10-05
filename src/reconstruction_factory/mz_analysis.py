"""Independent disk-side MZ checks for Factory-native headless Ghidra."""

from __future__ import annotations

import hashlib
from pathlib import Path
import re
import struct
from typing import Any

from .errors import AnalysisError
from .ontology import TargetIdentity


MARKER = re.compile(
    r"FACTORY_GHIDRA_MZ_ATTESTATION_V1:"
    r"(?P<sha256>[0-9a-f]{64}):(?P<md5>[0-9a-f]{32}):"
    r"(?P<size>\d+):(?P<header_size>\d+):(?P<load_size>\d+):"
    r"(?P<cs>[0-9a-f]{4}):(?P<ip>[0-9a-f]{4}):(?P<relocation_count>\d+):"
    r"(?P<load_sha256>[0-9a-f]{64}):(?P<relocated_sha256>[0-9a-f]{64}):"
    r"(?P<sample_count>\d+)"
)


def inspect_mz_target(path: Path, target: TargetIdentity) -> dict[str, Any]:
    try:
        data = path.read_bytes()
    except OSError as error:
        raise AnalysisError("cannot read registered private MZ target") from error
    sha = hashlib.sha256(data).hexdigest()
    md5 = hashlib.md5(data, usedforsecurity=False).hexdigest()
    if (target.format != "mz" or len(data) != target.size or sha != target.sha256
            or (target.md5 is not None and md5 != target.md5)):
        raise AnalysisError("registered private MZ target identity differs from adapter")
    if len(data) < 28 or data[:2] != b"MZ":
        raise AnalysisError("registered private target is not an MZ image")
    fields = struct.unpack_from("<14H", data)
    _, last, pages, count, paragraphs, minimum, maximum, ss, sp, _, ip, cs, table, overlay = fields
    header = paragraphs * 16
    declared = pages * 512 if last == 0 else (pages - 1) * 512 + last
    if (not pages or last >= 512 or header < 28 or header > declared
            or declared > len(data) or minimum > maximum
            or (count and (table < 28 or table + count * 4 > header))):
        raise AnalysisError("registered private MZ header/relocation bounds are invalid")
    load = data[header:declared]
    if not load:
        raise AnalysisError("registered private MZ load module is empty")
    entry = cs * 16 + ip
    if entry >= len(load) or ss * 16 + sp > len(load) + minimum * 16:
        raise AnalysisError("registered private MZ entry/stack exceeds loaded allocation")
    relocated = bytearray(load)
    sites = []
    for index in range(count):
        offset, segment = struct.unpack_from("<HH", data, table + index * 4)
        site = segment * 16 + offset
        sites.append(site)
        if site + 2 > len(load):
            raise AnalysisError("registered private MZ relocation site exceeds load module")
        value = struct.unpack_from("<H", relocated, site)[0]
        struct.pack_into("<H", relocated, site, (value + 0x1000) & 0xFFFF)
    candidates = [0, entry, len(load) // 4, len(load) // 2,
                  len(load) * 3 // 4, len(load) - 16]
    if sites:
        candidates.extend((sites[0], sites[len(sites) // 2], sites[-1]))
    offsets = sorted({max(0, min(value, len(load) - 1)) for value in candidates})
    return {
        "sha256": sha, "md5": md5, "size": len(data), "header_size": header,
        "load_size": len(load), "cs": cs, "ip": ip, "relocation_count": count,
        "load_sha256": hashlib.sha256(load).hexdigest(),
        "relocated_sha256": hashlib.sha256(relocated).hexdigest(),
        "sample_count": len(offsets),
        "samples": [{"address": f"0x{0x10000 + offset:x}",
                     "bytes": bytes(relocated[offset:offset + 16])} for offset in offsets],
        "overlay_number": overlay,
    }


def validate_mz_attestation(stdout: str, disk: dict[str, Any], target: TargetIdentity) -> dict[str, Any]:
    matches = list(MARKER.finditer(stdout))
    if len(matches) != 1:
        raise AnalysisError("native Ghidra must emit exactly one MZ attestation marker")
    values = matches[0].groupdict()
    observed = {key: int(value, 16 if key in {"cs", "ip"} else 10)
                if key in {"size", "header_size", "load_size", "cs", "ip",
                           "relocation_count", "sample_count"} else value
                for key, value in values.items()}
    if observed != {key: disk[key] for key in observed}:
        raise AnalysisError("native Ghidra MZ attestation differs from private target")
    return {
        "status": "passed", "target_identity_id": target.id,
        "provider_transport": "factory-native-command", "format": "mz",
        "private_target_file_attested": True,
        "observed_sha256": disk["sha256"], "observed_md5": disk["md5"],
        "observed_size": disk["size"], "observed_load_size": disk["load_size"],
        "observed_entry_cs_ip": f"{disk['cs']:04X}:{disk['ip']:04X}",
        "observed_relocation_count": disk["relocation_count"],
        "mapped_byte_sample_count": disk["sample_count"],
        "mapped_byte_samples": [{"address": sample["address"], "size": len(sample["bytes"])}
                                for sample in disk["samples"]],
    }
