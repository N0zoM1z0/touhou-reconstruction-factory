"""Operator and worker CLI for the durable reconstruction service."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import sys
import time

from .errors import FactoryError
from .job_service import FactoryService, ReplayWorker
from .jobs import JobState
from .knowledge import KnowledgeStatus
from .ontology import ClaimType
from .service_config import load_service_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reconstruction-factory-service",
        description="Submit, execute, and inspect durable factory replay jobs.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=os.environ.get("FACTORY_SERVICE_CONFIG"),
        help="operator TOML (or set FACTORY_SERVICE_CONFIG)",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("describe")
    commands.add_parser("repositories")

    inspect = commands.add_parser("inspect")
    inspect.add_argument("repository_id")

    claims = commands.add_parser("claims")
    claims.add_argument("repository_id")
    claims.add_argument("--claim-type", choices=[item.value for item in ClaimType])
    _page_arguments(claims)

    submit = commands.add_parser("submit-replay")
    submit.add_argument("repository_id")
    submit.add_argument("claim_id")
    submit.add_argument("--idempotency-key", required=True)

    get_job = commands.add_parser("get-job")
    get_job.add_argument("job_id")

    list_jobs = commands.add_parser("list-jobs")
    list_jobs.add_argument("--state", choices=[item.value for item in JobState])
    list_jobs.add_argument("--repository-id")
    _page_arguments(list_jobs)

    cancel = commands.add_parser("cancel-job")
    cancel.add_argument("job_id")
    cancel.add_argument("--reason", required=True)

    events = commands.add_parser("job-events")
    events.add_argument("job_id")
    _page_arguments(events)

    output = commands.add_parser("job-output")
    output.add_argument("job_id")
    output.add_argument("--artifact-id")
    output.add_argument("--offset", type=int, default=0)
    output.add_argument("--limit", type=int, default=16384)

    commands.add_parser("accepted-registry")
    snapshot = commands.add_parser("accepted-snapshot")
    snapshot.add_argument("repository_id")

    facts = commands.add_parser("accepted-facts")
    facts.add_argument("--target")
    facts.add_argument("--claim-type", choices=[item.value for item in ClaimType])
    facts.add_argument("--oracle")
    _page_arguments(facts)

    knowledge = commands.add_parser("knowledge")
    knowledge.add_argument("--status", choices=[item.value for item in KnowledgeStatus])
    knowledge.add_argument("--scope")
    _page_arguments(knowledge)

    fixtures = commands.add_parser("fixtures")
    fixtures.add_argument("--project")
    _page_arguments(fixtures)

    worker = commands.add_parser("worker")
    worker.add_argument("--once", action="store_true")
    worker.add_argument("--worker-id")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.config is None:
            raise ValueError("--config or FACTORY_SERVICE_CONFIG is required")
        if args.command == "worker":
            return _worker(args.config, args.worker_id, args.once)
        service = FactoryService.from_path(args.config)
        if args.command == "describe":
            result = service.describe()
        elif args.command == "repositories":
            result = {"repositories": service.list_repositories()}
        elif args.command == "inspect":
            result = service.inspect_repository(args.repository_id)
        elif args.command == "claims":
            result = service.list_claims(
                args.repository_id,
                claim_type=ClaimType(args.claim_type) if args.claim_type else None,
                limit=args.limit,
                offset=args.offset,
            ).to_dict()
        elif args.command == "submit-replay":
            result = service.submit_replay(
                args.repository_id, args.claim_id, args.idempotency_key
            )
        elif args.command == "get-job":
            result = service.get_job(args.job_id)
        elif args.command == "list-jobs":
            result = service.list_jobs(
                state=JobState(args.state) if args.state else None,
                repository_id=args.repository_id,
                limit=args.limit,
                offset=args.offset,
            )
        elif args.command == "cancel-job":
            result = service.cancel_job(args.job_id, args.reason)
        elif args.command == "job-events":
            result = service.job_events(
                args.job_id, limit=args.limit, offset=args.offset
            )
        elif args.command == "job-output":
            result = service.artifact_page(
                args.job_id,
                args.artifact_id,
                offset=args.offset,
                limit=args.limit,
            )
        elif args.command == "accepted-registry":
            result = service.accepted_registry()
        elif args.command == "accepted-snapshot":
            result = service.accepted_snapshot(args.repository_id)
        elif args.command == "accepted-facts":
            result = service.accepted_facts(
                target_identity_id=args.target,
                claim_type=ClaimType(args.claim_type) if args.claim_type else None,
                oracle_id=args.oracle,
                limit=args.limit,
                offset=args.offset,
            )
        elif args.command == "knowledge":
            result = service.knowledge(
                status=KnowledgeStatus(args.status) if args.status else None,
                scope=args.scope,
                limit=args.limit,
                offset=args.offset,
            )
        elif args.command == "fixtures":
            result = service.fixtures(
                project=args.project, limit=args.limit, offset=args.offset
            )
        else:
            raise AssertionError(f"unhandled command {args.command}")
        _print(result)
        return 0
    except (FactoryError, OSError, TypeError, ValueError) as error:
        print(
            json.dumps(
                {"error": type(error).__name__, "message": str(error)},
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


def _worker(config_path: Path, worker_id: str | None, once: bool) -> int:
    stopping = False

    def stop(_signum, _frame) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    worker = ReplayWorker(
        config_path,
        worker_id=worker_id,
        stop_requested=lambda: stopping,
    )
    while not stopping:
        result = worker.run_once()
        if result is not None:
            _print(result.public_dict())
        if once:
            if result is None:
                _print({"state": "idle"})
            return 0
        if result is None:
            delay = load_service_config(config_path).worker_poll_seconds
            time.sleep(delay)
    return 0


def _page_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--offset", type=int, default=0)


def _print(value) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
