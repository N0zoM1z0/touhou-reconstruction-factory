"""Command-line interface for the reconstruction factory foundation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .adapters import inspect_repository
from .errors import FactoryError
from .factory import kit_for_snapshot
from .knowledge import load_knowledge_catalog
from .live_validation import validate_live_repository
from .providers import builtin_registry
from .regressions import run_fixture_suite, verify_fixture_provenance


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reconstruction-factory",
        description="Inspect reconstruction repositories through the truth kernel.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser(
        "inspect", help="normalize an existing repository without modifying it"
    )
    inspect_parser.add_argument("repository", type=Path)
    inspect_parser.add_argument(
        "--summary", action="store_true", help="omit subjects and claims from output"
    )

    validate_parser = subparsers.add_parser(
        "validate-live", help="compare adapter metrics with native read-only reports"
    )
    validate_parser.add_argument("repositories", nargs="+", type=Path)

    subparsers.add_parser("providers", help="list built-in provider IDs")

    fixtures_parser = subparsers.add_parser(
        "fixtures", help="run hash-pinned historical regression fixtures"
    )
    fixtures_parser.add_argument(
        "--directory", type=Path, help="use an alternate fixture directory"
    )
    subparsers.add_parser("knowledge", help="print the scoped cross-game knowledge catalog")

    provenance_parser = subparsers.add_parser(
        "verify-provenance", help="verify fixture commits and paths in local repositories"
    )
    provenance_parser.add_argument(
        "--repository",
        action="append",
        required=True,
        metavar="PROJECT=PATH",
        help="map a fixture project ID to a local Git repository",
    )
    provenance_parser.add_argument(
        "--directory", type=Path, help="use an alternate fixture directory"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "inspect":
            snapshot = inspect_repository(args.repository)
            kit = kit_for_snapshot(snapshot)
            payload = snapshot.to_dict()
            payload["provider_kit"] = {
                "platform": kit.platform.id,
                "toolchain": kit.toolchain.id,
                "capabilities": sorted(item.value for item in kit.capabilities),
                "oracle_contracts": list(kit.oracle_contracts),
                "validation_notes": list(kit.validation_notes),
            }
            if args.summary:
                payload["counts"] = {
                    "products": len(snapshot.products),
                    "subjects": len(snapshot.subjects),
                    "claims": len(snapshot.claims),
                    "oracle_results": len(snapshot.oracle_results),
                }
                for key in ("subjects", "claims", "oracle_results", "artifacts"):
                    payload.pop(key, None)
            print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
            return 0
        if args.command == "validate-live":
            results = [
                validate_live_repository(repository).to_dict()
                for repository in args.repositories
            ]
            print(json.dumps({"results": results}, indent=2, sort_keys=True))
            return 0
        if args.command == "providers":
            registry = builtin_registry()
            print(
                json.dumps(
                    {
                        "platforms": registry.platform_ids(),
                        "toolchains": registry.toolchain_ids(),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        if args.command == "fixtures":
            report = run_fixture_suite(args.directory)
            print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
            return 0 if report.passed else 1
        if args.command == "knowledge":
            catalog = load_knowledge_catalog()
            print(json.dumps(catalog.to_dict(), indent=2, sort_keys=True))
            return 0
        if args.command == "verify-provenance":
            repositories: dict[str, Path] = {}
            for value in args.repository:
                project, separator, raw_path = value.partition("=")
                if not separator or not project or not raw_path:
                    raise ValueError("--repository must use PROJECT=PATH")
                if project in repositories:
                    raise ValueError(f"duplicate --repository project: {project}")
                repositories[project] = Path(raw_path)
            report = verify_fixture_provenance(
                repositories, directory=args.directory
            )
            print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
            return 0 if report.passed else 1
    except (FactoryError, OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 2
