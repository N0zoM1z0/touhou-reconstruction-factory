"""Typed MCP v2 surface for GPT-web factory operation."""

from __future__ import annotations

import argparse
import hmac
import os
from pathlib import Path
from typing import Annotated, Any, Callable, TypeVar

import anyio
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import Field
from starlette.responses import JSONResponse
import uvicorn

from .job_service import FactoryService
from .errors import FactoryError
from .jobs import JobState
from .knowledge import KnowledgeStatus
from .ontology import ClaimType
from .service_config import load_service_config


_T = TypeVar("_T")
RepositoryId = Annotated[
    str, Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._:-]*$")
]
ClaimId = Annotated[
    str, Field(min_length=1, max_length=512, pattern=r"^[a-z0-9][a-z0-9._:-]*$")
]
JobId = Annotated[str, Field(pattern=r"^job:[0-9a-f]{32}$")]
IdempotencyKey = Annotated[
    str,
    Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$"),
]
Reason = Annotated[str, Field(min_length=1, max_length=1000)]
ArtifactId = Annotated[str, Field(pattern=r"^artifact:sha256:[0-9a-f]{64}$")]
NormalizedId = Annotated[
    str, Field(min_length=1, max_length=512, pattern=r"^[a-z0-9][a-z0-9._:-]*$")
]
PageLimit = Annotated[int, Field(ge=1, le=100)]
ByteLimit = Annotated[int, Field(ge=1, le=65536)]
Offset = Annotated[int, Field(ge=0)]
_READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)
_SUBMIT = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)
_CANCEL = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=True,
    idempotentHint=True,
    openWorldHint=False,
)


def build_mcp_server(config_path: str | Path) -> MCPServer:
    """Create a stateless tool server over one private operator configuration."""

    path = Path(config_path).expanduser().resolve(strict=True)
    server = MCPServer(
        "touhou-reconstruction-factory",
        version="0.2.0",
        instructions=(
            "Use registered repository IDs only. Submit replays with a stable, unique "
            "idempotency key, then poll factory_get_job. A completed job is not proof "
            "of exactness: inspect receipt_verdict and acceptance_decision. Only "
            "factory_query_accepted_facts and factory_get_accepted_snapshot expose "
            "facts admitted to the Truth Kernel."
        ),
    )

    def service() -> FactoryService:
        return FactoryService.from_path(path)

    async def invoke(function: Callable[[], _T]) -> _T:
        return await _thread(function, config_path=path)

    @server.tool(
        description=(
            "Describe the configured factory authority boundary, policy identity, and "
            "registered repositories. Local filesystem paths are intentionally omitted."
        ),
        annotations=_READ_ONLY,
        structured_output=True,
    )
    async def factory_describe() -> dict[str, Any]:
        return await invoke(lambda: service().describe())

    @server.tool(
        description=(
            "List stable repository IDs that may be used by all other tools. Never "
            "accepts or reveals an arbitrary filesystem path."
        ),
        annotations=_READ_ONLY,
        structured_output=True,
    )
    async def factory_list_repositories() -> dict[str, Any]:
        return await invoke(lambda: {"repositories": service().list_repositories()})

    @server.tool(
        description=(
            "Inspect one registered repository through its read-only adapter. Returns "
            "target identities, diagnostics, and counts; imported claims are not accepted facts."
        ),
        annotations=_READ_ONLY,
        structured_output=True,
    )
    async def factory_inspect_repository(repository_id: RepositoryId) -> dict[str, Any]:
        return await invoke(lambda: service().inspect_repository(repository_id))

    @server.tool(
        description=(
            "Page through imported replay candidates for a registered repository. "
            "Use a returned claim ID with factory_submit_replay."
        ),
        annotations=_READ_ONLY,
        structured_output=True,
    )
    async def factory_list_claims(
        repository_id: RepositoryId,
        claim_type: ClaimType | None = None,
        limit: PageLimit = 20,
        offset: Offset = 0,
    ) -> dict[str, Any]:
        return await invoke(
            lambda: (
                service()
                .list_claims(
                    repository_id,
                    claim_type=claim_type,
                    limit=limit,
                    offset=offset,
                )
                .to_dict()
            )
        )

    @server.tool(
        description=(
            "Durably queue one factory-controlled replay and return immediately. The "
            "idempotency key must remain stable across retries; reusing it with changed "
            "arguments is rejected. This tool cannot run arbitrary commands."
        ),
        annotations=_SUBMIT,
        structured_output=True,
    )
    async def factory_submit_replay(
        repository_id: RepositoryId,
        claim_id: ClaimId,
        idempotency_key: IdempotencyKey,
    ) -> dict[str, Any]:
        return await invoke(
            lambda: service().submit_replay(repository_id, claim_id, idempotency_key)
        )

    @server.tool(
        description=(
            "Get durable state for one job after a reconnect or process restart. A "
            "completed state means execution and classification finished; exactness still "
            "requires receipt_verdict=pass and acceptance_decision=accepted."
        ),
        annotations=_READ_ONLY,
        structured_output=True,
    )
    async def factory_get_job(job_id: JobId) -> dict[str, Any]:
        return await invoke(lambda: service().get_job(job_id))

    @server.tool(
        description="Page through durable replay jobs with optional state and repository filters.",
        annotations=_READ_ONLY,
        structured_output=True,
    )
    async def factory_list_jobs(
        state: JobState | None = None,
        repository_id: RepositoryId | None = None,
        limit: PageLimit = 20,
        offset: Offset = 0,
    ) -> dict[str, Any]:
        return await invoke(
            lambda: service().list_jobs(
                state=state,
                repository_id=repository_id,
                limit=limit,
                offset=offset,
            )
        )

    @server.tool(
        description=(
            "Request cancellation of a queued or active replay. Queued work becomes "
            "cancelled immediately; a worker terminates an active native process group "
            "before recording cancellation. Terminal jobs are unchanged."
        ),
        annotations=_CANCEL,
        structured_output=True,
    )
    async def factory_cancel_job(job_id: JobId, reason: Reason) -> dict[str, Any]:
        return await invoke(lambda: service().cancel_job(job_id, reason))

    @server.tool(
        description=(
            "Page through the append-only state transition history of one durable job."
        ),
        annotations=_READ_ONLY,
        structured_output=True,
    )
    async def factory_get_job_events(
        job_id: JobId, limit: PageLimit = 20, offset: Offset = 0
    ) -> dict[str, Any]:
        return await invoke(
            lambda: service().job_events(job_id, limit=limit, offset=offset)
        )

    @server.tool(
        description=(
            "List receipt artifacts for a completed job, or read a bounded byte page "
            "from one referenced artifact. Continue with next_offset; output tails are "
            "never silently discarded."
        ),
        annotations=_READ_ONLY,
        structured_output=True,
    )
    async def factory_get_job_output_page(
        job_id: JobId,
        artifact_id: ArtifactId | None = None,
        offset: Offset = 0,
        limit: ByteLimit = 16384,
    ) -> dict[str, Any]:
        return await invoke(
            lambda: service().artifact_page(
                job_id, artifact_id, offset=offset, limit=limit
            )
        )

    @server.tool(
        description=(
            "Build and return the current acceptance registry. Every stored receipt is "
            "classified as accepted, rejected, or invalid; none are silently omitted."
        ),
        annotations=_READ_ONLY,
        structured_output=True,
    )
    async def factory_get_acceptance_registry() -> dict[str, Any]:
        return await invoke(lambda: service().accepted_registry())

    @server.tool(
        description=(
            "Return a live repository snapshot whose oracle results come only from fresh, "
            "integrity-checked, policy-accepted receipts."
        ),
        annotations=_READ_ONLY,
        structured_output=True,
    )
    async def factory_get_accepted_snapshot(
        repository_id: RepositoryId,
    ) -> dict[str, Any]:
        return await invoke(lambda: service().accepted_snapshot(repository_id))

    @server.tool(
        description=(
            "Page through only fresh facts admitted by the acceptance registry. This is "
            "the authoritative receipt-backed knowledge query, not the imported claim list."
        ),
        annotations=_READ_ONLY,
        structured_output=True,
    )
    async def factory_query_accepted_facts(
        target_identity_id: NormalizedId | None = None,
        claim_type: ClaimType | None = None,
        oracle_id: NormalizedId | None = None,
        limit: PageLimit = 20,
        offset: Offset = 0,
    ) -> dict[str, Any]:
        return await invoke(
            lambda: service().accepted_facts(
                target_identity_id=target_identity_id,
                claim_type=claim_type,
                oracle_id=oracle_id,
                limit=limit,
                offset=offset,
            )
        )

    @server.tool(
        description=(
            "Page through scoped cross-game knowledge, preserving verified, provisional, "
            "unknown, and superseded status rather than guessing missing facts."
        ),
        annotations=_READ_ONLY,
        structured_output=True,
    )
    async def factory_query_knowledge(
        status: KnowledgeStatus | None = None,
        scope: NormalizedId | None = None,
        limit: PageLimit = 20,
        offset: Offset = 0,
    ) -> dict[str, Any]:
        return await invoke(
            lambda: service().knowledge(
                status=status, scope=scope, limit=limit, offset=offset
            )
        )

    @server.tool(
        description=(
            "Page through hash-pinned historical regression fixtures and their exact "
            "expected verdicts. These are durable counterexamples, not live receipts."
        ),
        annotations=_READ_ONLY,
        structured_output=True,
    )
    async def factory_list_historical_fixtures(
        project: NormalizedId | None = None,
        limit: PageLimit = 20,
        offset: Offset = 0,
    ) -> dict[str, Any]:
        return await invoke(
            lambda: service().fixtures(project=project, limit=limit, offset=offset)
        )

    return server


async def _thread(function: Callable[[], _T], *, config_path: Path) -> _T:
    try:
        return await anyio.to_thread.run_sync(function)
    except (FactoryError, OSError, TypeError, ValueError) as error:
        message = str(error)
        redactions = {str(config_path), str(config_path.parent)}
        try:
            config = load_service_config(config_path)
        except (FactoryError, OSError, TypeError, ValueError):
            pass
        else:
            redactions.update(
                {
                    str(config.state_directory),
                    str(config.evidence_store),
                    str(config.policy_path),
                    *(str(item.path) for item in config.repositories),
                }
            )
        for value in sorted(redactions, key=len, reverse=True):
            message = message.replace(value, "<operator-path>")
        raise ToolError(f"{type(error).__name__}: {message}") from error


class BearerTokenMiddleware:
    """Require one operator-supplied bearer token before MCP parsing."""

    def __init__(self, app, token: str) -> None:
        if len(token) < 32:
            raise ValueError(
                "FACTORY_MCP_BEARER_TOKEN must contain at least 32 characters"
            )
        self.app = app
        self.expected = f"Bearer {token}".encode("utf-8")

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {name.lower(): value for name, value in scope.get("headers", [])}
        supplied = headers.get(b"authorization", b"")
        if not hmac.compare_digest(supplied, self.expected):
            response = JSONResponse(
                {"error": "unauthorized"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="touhou-reconstruction-factory-mcp")
    parser.add_argument(
        "--config",
        type=Path,
        default=os.environ.get("FACTORY_SERVICE_CONFIG"),
    )
    parser.add_argument(
        "--transport", choices=("stdio", "streamable-http"), default="stdio"
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--allowed-host", action="append", default=[])
    parser.add_argument("--allowed-origin", action="append", default=[])
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.config is None:
        raise SystemExit("--config or FACTORY_SERVICE_CONFIG is required")
    server = build_mcp_server(args.config)
    if args.transport == "stdio":
        server.run("stdio")
        return 0
    token = os.environ.get("FACTORY_MCP_BEARER_TOKEN", "")
    allowed_hosts = args.allowed_host or [
        f"{args.host}:{args.port}",
        f"127.0.0.1:{args.port}",
        f"localhost:{args.port}",
    ]
    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=sorted(set(allowed_hosts)),
        allowed_origins=sorted(set(args.allowed_origin)),
    )
    app = server.streamable_http_app(
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=True,
        transport_security=security,
        host=args.host,
    )
    uvicorn.run(BearerTokenMiddleware(app, token), host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
