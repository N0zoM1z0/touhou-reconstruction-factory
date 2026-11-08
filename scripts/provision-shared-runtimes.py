#!/usr/bin/env python3
"""Consolidate existing runtimes and attach registered worktrees (no downloads)."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import stat
import tomllib
import uuid


FACTORY = Path(__file__).resolve().parents[1]
DESTINATION = FACTORY / ".factory/shared-tools"


def manifest(root: Path) -> dict:
    result = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        mode = stat.S_IMODE(path.lstat().st_mode)
        if path.is_symlink():
            result[relative] = {"link": os.readlink(path)}
        elif path.is_file():
            with path.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            result[relative] = {"sha256": digest, "size": path.stat().st_size, "mode": mode}
        elif path.is_dir():
            result[relative] = {"directory": True, "mode": mode}
        else:
            raise ValueError(f"unexpected runtime entry: {path}")
    return result


def replace_link(path: Path, destination: Path) -> None:
    if path.is_symlink():
        # Use a direct link: an equivalent chain through an unregistered
        # worktree may be invisible inside the repository sandbox.
        if Path(os.readlink(path)) == destination:
            return
        path.unlink()
    elif path.exists():
        raise ValueError(f"refusing to replace an unreviewed directory or file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.symlink_to(destination, target_is_directory=destination.is_dir())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--prefix", action="append", default=[], metavar="REPOSITORY=PATH")
    parser.add_argument("--apply", action="store_true", help="apply the byte-verified consolidation plan")
    args = parser.parse_args()
    selector = runpy.run_path(str(FACTORY / "scripts/push-registered-repos.py"))
    selected = args.config or os.environ.get("FACTORY_SERVICE_CONFIG")
    config = Path(selected).expanduser().resolve() if selected else selector["running_config"]()
    repositories = selector["registered_repositories"](config)
    overrides = dict(value.split("=", 1) for value in args.prefix)
    unknown = set(overrides) - {rid for rid, _ in repositories}
    if unknown:
        raise ValueError("prefix override names an unregistered repository")
    defaults = {"ghidra": FACTORY / ".factory/web-live/tools/ghidra_12.1.3_PUBLIC",
                "jdk": FACTORY / ".factory/web-live/tools/jdk-21.0.12.1+1"}
    for kind, legacy in defaults.items():
        if (DESTINATION / legacy.name).is_dir():
            defaults[kind] = DESTINATION / legacy.name
    packages, selections = {}, {}
    for rid, repository in repositories:
        choices = {}
        for kind in ("ghidra", "jdk"):
            local = repository / ".tools" / kind
            source = local.resolve() if local.exists() else defaults[kind].resolve()
            if not source.is_dir():
                raise ValueError(f"{rid}: no installed {kind} payload")
            name = source.name
            if kind == "ghidra" and not (source / "Ghidra/application.properties").is_file():
                raise ValueError("not a Ghidra installation")
            if kind == "jdk" and not (source / "bin/java").is_file():
                raise ValueError("not a JDK installation")
            packages.setdefault(name, set()).add(source)
            choices[kind] = name
        selections[rid] = choices
    # Verify all duplicate content before mutating any payload. A conflicting
    # extension or modified install is retained for operator review.
    plans = []
    for name, sources in packages.items():
        destination = DESTINATION / name
        ordered = sorted(sources, key=lambda path: (not path.is_relative_to(FACTORY), str(path)))
        primary = destination if destination.exists() else ordered[0]
        expected = manifest(primary)
        for source in ordered:
            if source == destination:
                continue
            observed = expected if source == primary else manifest(source)
            if observed != expected:
                different = sorted(key for key in expected.keys() | observed.keys()
                                   if expected.get(key) != observed.get(key))
                raise ValueError(f"runtime {name} has distinct content; preserve and review: {different[:8]}")
        plans.append((name, destination, primary, ordered, expected))
        print(f"{name}: {len(ordered)} source installation(s), byte-identical selection", flush=True)
    template = (FACTORY / "runtime/repository-shim.py").read_text()
    specs, prefix_owners = {}, {}
    for name in ("wine", "winepath", "wineserver"):
        binary = Path("/usr/bin") / name
        if not binary.is_file():
            raise ValueError(f"system Wine component is missing: {name}")
    for rid, repository in repositories:
        tools = repository / ".tools"
        spec_path = tools / "shared-runtimes.json"
        previous = json.loads(spec_path.read_text()) if spec_path.exists() else {}
        prefix = overrides.get(rid) or previous.get("wine_prefix")
        if prefix is None:
            native = repository / "config/toolchain.toml"
            if native.exists():
                prefix = tomllib.loads(native.read_text()).get("paths", {}).get("wine_prefix")
        if prefix is None:
            existing = [p for p in tools.iterdir() if p.is_dir() and (p / "system.reg").exists()] if tools.exists() else []
            if len(existing) > 1:
                raise ValueError(f"{rid}: choose an existing Wine prefix with --prefix")
            prefix = str(existing[0].relative_to(repository)) if existing else ".tools/wine"
        resolved = (repository / Path(prefix).expanduser()).resolve()
        if resolved in prefix_owners:
            raise ValueError("two repositories selected the same Wine prefix")
        prefix_owners[resolved] = rid
        arch = "win32"
        registry = resolved / "system.reg"
        if registry.exists():
            with registry.open(errors="replace") as stream:
                for _ in range(8):
                    line = stream.readline()
                    if line.startswith("#arch="):
                        arch = line.strip().split("=", 1)[1]
        spec = {"schema_version": 1, "repository_id": rid,
                "owner_token": previous.get("owner_token", uuid.uuid4().hex),
                **selections[rid], "wine_prefix": str(prefix), "wine_arch": arch}
        marker = resolved / ".factory-runtime-owner.json"
        if marker.exists() and json.loads(marker.read_text()).get("owner_token") != spec["owner_token"]:
            raise ValueError(f"{rid}: prefix is owned by another repository")
        shim = repository / "scripts/shared_runtime.py"
        if shim.exists() and shim.read_text() != template:
            raise ValueError(f"{rid}: existing shared_runtime.py needs review")
        specs[rid] = spec
        print(f"{rid}: {arch} prefix selected", flush=True)
    if not args.apply:
        print(f"Plan only: {len(repositories)} worktrees; pass --apply to provision")
        return 0
    DESTINATION.mkdir(parents=True, exist_ok=True)
    audit = DESTINATION / "migration-manifests"
    audit.mkdir(exist_ok=True)
    for name, destination, primary, sources, expected in plans:
        record = audit / (name + ".json")
        if not record.exists():
            record.write_text(json.dumps({"entries": expected, "sources": [str(p) for p in sources]}, indent=2))
        if not destination.exists():
            primary.rename(destination)
            primary.symlink_to(destination, target_is_directory=True)
        for source in sources:
            if source == destination or source.is_symlink():
                continue
            # Every entry has an identical retained copy and a saved manifest.
            shutil.rmtree(source)
            source.symlink_to(destination, target_is_directory=True)
    wine = DESTINATION / "wine/bin"
    wine.mkdir(parents=True, exist_ok=True)
    for name in ("wine", "winepath", "wineserver"):
        replace_link(wine / name, (Path("/usr/bin") / name).resolve())
    for rid, repository in repositories:
        tools = repository / ".tools"
        tools.mkdir(exist_ok=True)
        spec, spec_path = specs[rid], tools / "shared-runtimes.json"
        spec_path.write_text(json.dumps(spec, indent=2) + "\n")
        for kind in ("ghidra", "jdk"):
            replace_link(tools / kind, DESTINATION / spec[kind])
        replace_link(tools / "factory-runtime.py", FACTORY / "runtime/run.py")
        shim = repository / "scripts/shared_runtime.py"
        shim.write_text(template)
        shim.chmod(0o755)
        bins = tools / "factory-bin"
        bins.mkdir(exist_ok=True)
        for tool in ("wine", "winepath", "wineserver", "analyzeHeadless", "java"):
            selection = "ghidra" if tool == "analyzeHeadless" else tool
            prefix_args = ('if [[ -n "${WINEPREFIX:-}" ]]; then extra=(--prefix "$WINEPREFIX"); fi\n'
                           if selection in {"wine", "winepath", "wineserver"} else "")
            wrapper = bins / tool
            wrapper.write_text('#!/usr/bin/env bash\nset -euo pipefail\n'
                'repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)\n'
                'extra=()\n' + prefix_args +
                f'exec "$repo_root/scripts/shared_runtime.py" "${{extra[@]}}" {selection} -- "$@"\n')
            wrapper.chmod(0o755)
        print(f"{rid}: shared tools attached", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError) as error:
        raise SystemExit(f"provision shared runtimes: {error}")
