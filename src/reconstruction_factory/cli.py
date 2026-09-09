"""Command-line interface for the reconstruction factory foundation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .acceptance import build_acceptance_registry, load_acceptance_policy
from .adapters import inspect_repository
from .artifact_store import ArtifactStore
from .errors import FactoryError
from .factory import kit_for_snapshot
from .knowledge import load_knowledge_catalog
from .live_validation import validate_live_repository
from .ontology import ClaimType
from .providers import builtin_registry
from .regressions import run_fixture_suite, verify_fixture_provenance
from .replay_runner import ReplayRunner, verify_live_freshness


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

    registry_parser = subparsers.add_parser(
        "acceptance-registry",
        help="classify receipt candidates through an explicit live policy",
    )
    _add_registry_arguments(registry_parser)

    accepted_inspect_parser = subparsers.add_parser(
        "inspect-accepted",
        help="materialize a snapshot using only registry-accepted oracle results",
    )
    accepted_inspect_parser.add_argument("repository", type=Path)
    accepted_inspect_parser.add_argument("--store", type=Path, required=True)
    accepted_inspect_parser.add_argument("--policy", type=Path, required=True)
    accepted_inspect_parser.add_argument(
        "--summary", action="store_true", help="omit subjects and claims from output"
    )

    accepted_knowledge_parser = subparsers.add_parser(
        "accepted-knowledge",
        help="query only facts backed by registry-accepted receipts",
    )
    _add_registry_arguments(accepted_knowledge_parser)
    accepted_knowledge_parser.add_argument("--target")
    accepted_knowledge_parser.add_argument(
        "--claim-type",
        choices=sorted(item.value for item in ClaimType),
    )
    accepted_knowledge_parser.add_argument("--oracle")

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

    replay_parser = subparsers.add_parser(
        "replay", help="cold-replay one claim through a factory-controlled driver"
    )
    replay_parser.add_argument("repository", type=Path)
    replay_parser.add_argument("--claim", required=True)
    replay_parser.add_argument(
        "--store", type=Path, default=Path(".factory"), help="content-addressed evidence store"
    )
    replay_parser.add_argument(
        "--timeout", type=int, default=1800, help="timeout in seconds for each native stage"
    )

    receipt_parser = subparsers.add_parser(
        "verify-receipt", help="verify receipt and content-addressed artifact integrity"
    )
    receipt_parser.add_argument("receipt", type=Path)
    receipt_parser.add_argument("--store", type=Path, default=Path(".factory"))
    receipt_parser.add_argument(
        "--repository", type=Path, help="also require the receipt to be fresh for this repository"
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
        if args.command == "acceptance-registry":
            registry = build_acceptance_registry(
                ArtifactStore(args.store),
                load_acceptance_policy(args.policy),
                _repository_map(args.repository),
            )
            print(json.dumps(registry.to_dict(), indent=2, sort_keys=True))
            return 1 if registry.invalid_count else 0
        if args.command == "inspect-accepted":
            initial = inspect_repository(args.repository)
            repository_map = {
                target.id: args.repository for target in initial.targets
            }
            registry = build_acceptance_registry(
                ArtifactStore(args.store),
                load_acceptance_policy(args.policy),
                repository_map,
            )
            snapshot = registry.materialize_live_snapshot(args.repository)
            payload = snapshot.to_dict()
            payload["acceptance_registry"] = registry.to_dict()
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
            return 1 if registry.invalid_count else 0
        if args.command == "accepted-knowledge":
            registry = build_acceptance_registry(
                ArtifactStore(args.store),
                load_acceptance_policy(args.policy),
                _repository_map(args.repository),
            )
            facts = registry.accepted_facts(
                target_identity_id=args.target,
                claim_type=ClaimType(args.claim_type) if args.claim_type else None,
                oracle_id=args.oracle,
            )
            print(
                json.dumps(
                    {"registry": registry.to_dict(), "facts": facts},
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
            )
            return 1 if registry.invalid_count else 0
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
        if args.command == "replay":
            run = ReplayRunner(
                ArtifactStore(args.store), timeout_seconds=args.timeout
            ).run(args.repository, args.claim)
            result = run.receipt.result
            print(
                json.dumps(
                    {
                        "receipt_id": run.receipt.receipt_id,
                        "receipt_path": str(run.receipt_path),
                        "verdict": result.verdict.value,
                        "coverage": {
                            "domain": result.coverage.domain,
                            "expected": result.coverage.expected_units,
                            "observed": result.coverage.observed_units,
                            "complete": result.coverage.complete,
                        },
                        "acceptance_errors": list(run.receipt.acceptance_errors),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0 if result.verdict.value == "pass" else 1
        if args.command == "verify-receipt":
            document = ArtifactStore(args.store).verify_receipt_document(args.receipt)
            freshness = (
                verify_live_freshness(document, args.repository)
                if args.repository is not None
                else ()
            )
            print(
                json.dumps(
                    {
                        "receipt_id": document["receipt_id"],
                        "integrity": "pass",
                        "fresh": not freshness if args.repository is not None else None,
                        "freshness_errors": list(freshness),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0 if not freshness else 1
    except (FactoryError, OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 2


def _add_registry_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument(
        "--repository",
        action="append",
        default=[],
        metavar="TARGET_ID=PATH",
        help="bind a receipt target identity to a live repository",
    )


def _repository_map(values: list[str]) -> dict[str, Path]:
    repositories: dict[str, Path] = {}
    for value in values:
        target_id, separator, raw_path = value.partition("=")
        if not separator or not target_id or not raw_path:
            raise ValueError("--repository must use TARGET_ID=PATH")
        if target_id in repositories:
            raise ValueError(f"duplicate --repository target identity: {target_id}")
        repositories[target_id] = Path(raw_path)
    return repositories
