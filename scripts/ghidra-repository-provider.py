#!/usr/bin/env python3
"""Run a selected repository's existing Ghidra project without full preflights.

This is exploratory analysis. Exact verification belongs to explicit Oracle
commands, not every source lookup or decompilation.
"""

import argparse
import fcntl
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tomllib


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    layout = parser.add_mutually_exclusive_group()
    layout.add_argument("--mz-artifact")
    parser.add_argument("--project-name", help="select an existing project instead of the repository default")
    layout.add_argument("--standalone-project", action="store_true",
                        help="use config/target.toml, .tools/ghidra, .tools/jdk and ghidra-project directly")
    # Accepted for compatibility with existing private launchers.
    parser.add_argument("--marker", help=argparse.SUPPRESS)
    parser.add_argument("--interpreter", help=argparse.SUPPRESS)
    parser.add_argument("operation", choices=("check", "query", "decompile", "function_context"))
    parser.add_argument("arguments", nargs="*")
    args = parser.parse_args()
    root = args.repository.resolve()
    sys.path.insert(0, str(root / "scripts"))
    if args.standalone_project:
        with (root / "config/target.toml").open("rb") as handle:
            target = tomllib.load(handle)["target"]
        filename = target["filename"]
        project, name = root / "ghidra-project", Path(filename).stem
        ghidra_home = (root / ".tools/ghidra").resolve(strict=True)
        analyzer = ghidra_home / "support/analyzeHeadless"
        environment = dict(os.environ, JAVA_HOME=str((root / ".tools/jdk").resolve(strict=True)),
                           GHIDRA_HOME=str(ghidra_home))
    else:
        spec = importlib.util.spec_from_file_location("repository_ghidra", root / "scripts/ghidra.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    if args.mz_artifact:
        from lib.analysis import load_analysis_config, repository_path
        from lib.targets import find_artifact, load_target_manifest
        config = load_analysis_config(root / "config/analysis_toolchain.toml")
        artifact = find_artifact(load_target_manifest(root / "config/targets.toml"), args.mz_artifact)
        project = root / "ghidra-project"
        name = module.project_name(args.mz_artifact)
        filename = Path(artifact["private_path"]).name
        analyzer = repository_path(root, config["ghidra"]["stable_path"]) / "support/analyzeHeadless"
        environment = module.environment(config)
    elif not args.standalone_project:
        _, target, _ = module.load_target()
        ghidra_home, analyzer = module.find_analyzer()
        project, name, filename = module.PROJECT_DIR, module.PROJECT_NAME, target["filename"]
        environment = module.environment(ghidra_home)
    if args.project_name:
        name = args.project_name
    environment.update({"DISPLAY": "", "WAYLAND_DISPLAY": ""})
    environment.setdefault("GHIDRA_HEADLESS_MAXMEM", "768M")
    script_directory = root / "scripts/ghidra"
    if not args.standalone_project and not (script_directory / "QueryProgram.java").is_file():
        script_directory = root / ".tools/mcp_for_gptweb-ghidra/ghidra-scripts"
    script_paths = f"{Path(__file__).resolve().parent / 'ghidra'};{script_directory}"
    query_script = "FactoryQueryProgram.java" if args.standalone_project else "QueryProgram.java"
    decompile_script = "FactoryDecompileFunctions.java" if args.standalone_project else "FactoryDecompile.java"
    query = []
    fragments = []
    if args.operation != "check":
        output, *values = args.arguments
        if args.operation == "query":
            operation, *values = values
            if args.mz_artifact or args.standalone_project:
                index = {"list_functions": 2, "search_strings": 1}.get(operation)
                if index is not None and len(values) > index:
                    values[index] = "text:" + values[index]
            else:
                values = module.query_script_args(operation, values)
            query = ["-postScript", query_script, output, operation, *values]
        elif args.operation == "function_context":
            for operation in ("function", "callers", "callees", "decompile"):
                path = Path(output).with_name(f"{Path(output).stem}-{operation}.txt")
                fragments.append((operation, path))
                if operation == "decompile":
                    query.extend(["-postScript", decompile_script, str(path), *values])
                else:
                    query.extend(["-postScript", query_script, str(path), operation, *values])
        else:
            query = ["-postScript", decompile_script, output, *values]
    scratch = root / ".analysis"
    scratch.mkdir(exist_ok=True)
    gate_path = scratch / ("ghidra/headless.lock" if args.standalone_project else "ghidra.lock")
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    with gate_path.open("a+") as gate, (project / "workflow.lock").open("a+") as project_gate:
        fcntl.flock(gate, fcntl.LOCK_EX)
        fcntl.flock(project_gate, fcntl.LOCK_EX)
        result = subprocess.run(
            ["nice", "-n", "10", "taskset", "-c", str(min(os.sched_getaffinity(0))),
             str(analyzer), str(project), name, "-process", filename,
             "-readOnly", "-noanalysis", "-max-cpu", "1", *query,
             "-scriptPath", script_paths],
            cwd=root, env=environment, capture_output=True, text=True, errors="replace",
        )
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    if fragments:
        with Path(output).open("w", encoding="utf-8") as merged:
            for operation, path in fragments:
                merged.write(f"=== {operation} ===\n")
                merged.write(path.read_text(encoding="utf-8") if path.exists() else "[no output produced]\n")
                merged.write("\n")
    if "ERROR REPORT SCRIPT ERROR" in result.stdout + result.stderr or any(
        not path.exists() for _, path in fragments
    ):
        return 1
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
