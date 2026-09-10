"""Typed MCP v2 surface for GPT-web factory operation."""

from __future__ import annotations

import argparse
import hmac
import os
import sys
from pathlib import Path
from typing import Annotated, Any, Callable, Literal, TypeVar

import anyio
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import Field
from starlette.responses import JSONResponse
import uvicorn

from .job_service import FactoryService
from .analysis_mcp import AnalysisGateway
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
WorkspaceId = Annotated[str, Field(pattern=r"^workspace:[0-9a-f]{32}$")]
CommandId = Annotated[str, Field(pattern=r"^command:[0-9a-f]{32}$")]
RepositoryCommandId = Annotated[
    str, Field(pattern=r"^repository-command:[0-9a-f]{32}$")
]
IdempotencyKey = Annotated[
    str,
    Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$"),
]
Reason = Annotated[str, Field(min_length=1, max_length=1000)]
ArtifactId = Annotated[str, Field(pattern=r"^artifact:sha256:[0-9a-f]{64}$")]
NormalizedId = Annotated[
    str, Field(min_length=1, max_length=512, pattern=r"^[a-z0-9][a-z0-9._:-]*$")
]
AnalysisProviderId = Annotated[
    str, Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._:-]*$")
]
AnalysisOperation = Annotated[
    str, Field(min_length=1, max_length=160, pattern=r"^[a-z][a-z0-9_]*$")
]
ArgumentsJson = Annotated[str, Field(min_length=2, max_length=65536)]
OperationFilter = Annotated[str, Field(max_length=128)]
PageLimit = Annotated[int, Field(ge=1, le=100)]
ByteLimit = Annotated[int, Field(ge=1, le=65536)]
Offset = Annotated[int, Field(ge=0)]
RelativePath = Annotated[str, Field(min_length=1, max_length=1024)]
GlobPattern = Annotated[str, Field(min_length=1, max_length=256)]
SearchQuery = Annotated[str, Field(min_length=1, max_length=512)]
SemanticDebtCategory = Literal[
    "all",
    "raw-member-access",
    "absolute-address",
    "anonymous-identifier",
    "opaque-storage",
]
RegistryDetail = Literal["summary", "full"]
UnifiedPatch = Annotated[str, Field(min_length=1, max_length=4194304)]
ShellScript = Annotated[str, Field(min_length=1, max_length=65536)]
CommandTimeout = Annotated[int, Field(ge=1, le=3600)]
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
_WORKSPACE_CREATE = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)
_WORKSPACE_EDIT = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=False,
    openWorldHint=False,
)
_WORKSPACE_SHELL = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=True,
    idempotentHint=False,
    openWorldHint=False,
)
_REPOSITORY_SHELL = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=True,
    idempotentHint=False,
    openWorldHint=False,
)
_ANALYSIS_CALL = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=False,
    openWorldHint=False,
)


def build_mcp_server(config_path: str | Path) -> MCPServer:
    """Create a stateless tool server over one private operator configuration."""

    path = Path(config_path).expanduser().resolve(strict=True)
    server = MCPServer(
        "touhou-reconstruction-factory",
        version="0.5.0",
        instructions=(
            "Use registered repository IDs only. Prefer the live repository workflow "
            "for source reconstruction: it exposes the real worktree, broad composable "
            "Bash, repository-local tools, and local Git checkpoints. Commands may edit "
            "or commit and their partial changes persist even on failure or timeout; inspect "
            "status before and after. Network is unavailable, so Git push is not provided. "
            "For semantic reconstruction, use factory_report_semantic_debt only as a "
            "live-bound lexical router, preserve the target exact and corresponding "
            "historical-platform product/runtime baselines, and keep portable products "
            "after semantic readiness. "
            "A Git commit is a review checkpoint, never proof of exactness. Submit replays "
            "with a stable, unique "
            "idempotency key, then poll factory_get_job. A completed job is not proof "
            "of exactness: inspect receipt_verdict and acceptance_decision. Only "
            "factory_query_accepted_facts and factory_get_accepted_snapshot expose "
            "facts admitted to the Truth Kernel. Disposable workspaces remain available "
            "for intentionally isolated experiments, but they omit dirty, ignored, target, "
            "and toolchain state. Game-local knowledge may be committed in its game repo "
            "with publication authority set to none. This server exposes no Factory-knowledge promotion "
            "tool; factory_query_knowledge reads only the packaged cross-game catalog."
        ),
    )

    def service() -> FactoryService:
        return FactoryService.from_path(path)

    def analysis() -> AnalysisGateway:
        return AnalysisGateway(load_service_config(path))

    async def invoke(function: Callable[[], _T]) -> _T:
        return await _thread(function, config_path=path)

    async def analysis_invoke(function: Callable[[], Any]) -> Any:
        try:
            return await function()
        except (FactoryError, OSError, TypeError, ValueError) as error:
            raise ToolError(
                f"{type(error).__name__}: {_redact_error(str(error), path)}"
            ) from error

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
            "Inspect the real Git status of one operator-registered reconstruction repo. "
            "This includes current dirty, staged, untracked, branch, upstream, and HEAD "
            "state. A clean or committed worktree is a checkpoint state, not Oracle proof."
        ),
        annotations=_READ_ONLY,
        structured_output=True,
    )
    async def factory_get_repository_status(
        repository_id: RepositoryId,
    ) -> dict[str, Any]:
        return await invoke(lambda: service().repository_status(repository_id))

    @server.tool(
        description=(
            "Report paginated C/C++ semantic-debt candidates from the live worktree of "
            "one registered repository. The report is bound to HEAD and dirty-state "
            "digests and is only a heuristic router for raw member offsets, absolute "
            "addresses, anonymous identifiers, and opaque storage. Counts, including "
            "zero, are not semantic progress, evidence, exactness, or completion claims."
        ),
        annotations=_READ_ONLY,
        structured_output=True,
    )
    async def factory_report_semantic_debt(
        repository_id: RepositoryId,
        relative_path: RelativePath = "src",
        category: SemanticDebtCategory = "all",
        limit: PageLimit = 20,
        offset: Offset = 0,
    ) -> dict[str, Any]:
        return await invoke(
            lambda: service().repository_semantic_debt_report(
                repository_id,
                relative_path=relative_path,
                category=category,
                limit=limit,
                offset=offset,
            )
        )

    @server.tool(
        description=(
            "Run broad composable Bash in the real worktree of one registered repository. "
            "The command can inspect ignored targets/toolchains, edit source, build with "
            "repo-local Wine/toolchains, and create local Git commits. It has no network, "
            "so remote Git push is unavailable. Filesystem changes persist on nonzero exit "
            "or timeout. The result records before/after Git state, created commits, and "
            "initial output pages. A successful command or commit has zero exactness credit "
            "until a canonical replay receipt is accepted."
        ),
        annotations=_REPOSITORY_SHELL,
        structured_output=True,
    )
    async def factory_repository_run_shell(
        repository_id: RepositoryId,
        script: ShellScript,
        relative_cwd: RelativePath = ".",
        timeout_seconds: CommandTimeout = 120,
    ) -> dict[str, Any]:
        return await invoke(
            lambda: service().repository_run_shell(
                repository_id,
                script,
                relative_cwd=relative_cwd,
                timeout_seconds=timeout_seconds,
            )
        )

    @server.tool(
        description=(
            "Read a bounded stdout or stderr page from a durable live-repository command. "
            "Use next_offset until null; observed and captured sizes make truncation explicit."
        ),
        annotations=_READ_ONLY,
        structured_output=True,
    )
    async def factory_get_repository_command_output(
        repository_id: RepositoryId,
        command_id: RepositoryCommandId,
        stream: Literal["stdout", "stderr"] = "stdout",
        offset: Offset = 0,
        limit: ByteLimit = 16384,
    ) -> dict[str, Any]:
        return await invoke(
            lambda: service().repository_command_output(
                repository_id,
                command_id,
                stream=stream,
                offset=offset,
                limit=limit,
            )
        )

    @server.tool(
        description=(
            "List operator-registered semantic-analysis providers, optionally for one "
            "repository. Availability is not claimed until a target-attested operation "
            "succeeds. Endpoints and host paths are omitted."
        ),
        annotations=_READ_ONLY,
        structured_output=True,
    )
    async def factory_list_analysis_providers(
        repository_id: RepositoryId | None = None,
    ) -> dict[str, Any]:
        return await analysis_invoke(
            lambda: _async_value(
                {"analysis_providers": analysis().list_providers(repository_id)}
            )
        )

    @server.tool(
        description=(
            "Page the factory-approved atomic operations for an analysis provider. "
            "Native IDA includes semantic reads and reversible database-metadata edits, "
            "but no target-byte patching. Discovery re-attests the active target; "
            "Ghidra schemas are static and report not-probed until invoked."
        ),
        annotations=_READ_ONLY,
        structured_output=True,
    )
    async def factory_list_analysis_operations(
        analysis_provider_id: AnalysisProviderId,
        filter: OperationFilter = "",
        limit: PageLimit = 20,
        offset: Offset = 0,
    ) -> dict[str, Any]:
        return await analysis_invoke(
            lambda: analysis().list_operations(
                analysis_provider_id,
                filter=filter,
                limit=limit,
                offset=offset,
            )
        )

    @server.tool(
        description=(
            "Run one discovered, factory-allowlisted semantic-analysis operation. Native "
            "IDA talks directly over a Factory-owned stdio session and permits reversible "
            "database-metadata edits; target-byte patching and bridge Bash remain absent. "
            "Encode only the selected operation's listed arguments as one JSON object. "
            "Every result is target-bound provisional evidence with zero exactness credit."
        ),
        annotations=_ANALYSIS_CALL,
        structured_output=True,
    )
    async def factory_analysis_call(
        analysis_provider_id: AnalysisProviderId,
        operation: AnalysisOperation,
        arguments_json: ArgumentsJson = "{}",
    ) -> dict[str, Any]:
        return await analysis_invoke(
            lambda: analysis().call(analysis_provider_id, operation, arguments_json)
        )

    @server.tool(
        description=(
            "Create a capability-addressed disposable snapshot of one registered "
            "repository's committed HEAD. Dirty, untracked, and ignored files are "
            "reported as excluded, never copied. Retain the returned workspace ID."
        ),
        annotations=_WORKSPACE_CREATE,
        structured_output=True,
    )
    async def factory_create_workspace(
        repository_id: RepositoryId,
        idempotency_key: IdempotencyKey,
    ) -> dict[str, Any]:
        return await invoke(
            lambda: service().create_workspace(repository_id, idempotency_key)
        )

    @server.tool(
        description=(
            "Resume one workspace by its unguessable capability ID. Returns expiry, "
            "committed source identity, and recent command IDs without listing other "
            "callers' workspaces."
        ),
        annotations=_READ_ONLY,
        structured_output=True,
    )
    async def factory_get_workspace(workspace_id: WorkspaceId) -> dict[str, Any]:
        return await invoke(lambda: service().get_workspace(workspace_id))

    @server.tool(
        description=(
            "Page through regular files in a disposable workspace using a bounded POSIX "
            "glob. Git control data and host paths are outside this namespace."
        ),
        annotations=_READ_ONLY,
        structured_output=True,
    )
    async def factory_workspace_list_files(
        workspace_id: WorkspaceId,
        glob: GlobPattern = "**",
        limit: PageLimit = 20,
        offset: Offset = 0,
    ) -> dict[str, Any]:
        return await invoke(
            lambda: service().workspace_list_files(
                workspace_id, glob=glob, limit=limit, offset=offset
            )
        )

    @server.tool(
        description=(
            "Read one bounded byte page from a regular workspace file. The path must be "
            "POSIX-relative and cannot traverse symlinks or Git control data."
        ),
        annotations=_READ_ONLY,
        structured_output=True,
    )
    async def factory_workspace_read_file(
        workspace_id: WorkspaceId,
        relative_path: RelativePath,
        offset: Offset = 0,
        limit: ByteLimit = 16384,
    ) -> dict[str, Any]:
        return await invoke(
            lambda: service().workspace_read_file(
                workspace_id, relative_path, offset=offset, limit=limit
            )
        )

    @server.tool(
        description=(
            "Search workspace contents with ripgrep semantics and bounded results. Set "
            "literal=true for exact text; truncated=true means the service deliberately "
            "stopped before claiming a complete result set."
        ),
        annotations=_READ_ONLY,
        structured_output=True,
    )
    async def factory_workspace_search(
        workspace_id: WorkspaceId,
        query: SearchQuery,
        glob: GlobPattern = "**",
        literal: bool = True,
        case_sensitive: bool = True,
        limit: PageLimit = 20,
        offset: Offset = 0,
    ) -> dict[str, Any]:
        return await invoke(
            lambda: service().workspace_search(
                workspace_id,
                query,
                glob=glob,
                literal=literal,
                case_sensitive=case_sensitive,
                limit=limit,
                offset=offset,
            )
        )

    @server.tool(
        description=(
            "Apply one text-only unified Git diff to a disposable workspace after path, "
            "file-type, size, and Git applicability checks. This never edits the canonical "
            "repository and does not promote evidence."
        ),
        annotations=_WORKSPACE_EDIT,
        structured_output=True,
    )
    async def factory_workspace_apply_patch(
        workspace_id: WorkspaceId,
        patch: UnifiedPatch,
    ) -> dict[str, Any]:
        return await invoke(
            lambda: service().workspace_apply_patch(workspace_id, patch)
        )

    @server.tool(
        description=(
            "Return the bounded file inventory and structured change list for a workspace "
            "relative to its immutable committed-source baseline."
        ),
        annotations=_READ_ONLY,
        structured_output=True,
    )
    async def factory_get_workspace_status(
        workspace_id: WorkspaceId,
    ) -> dict[str, Any]:
        return await invoke(lambda: service().workspace_status(workspace_id))

    @server.tool(
        description=(
            "Read a byte page of the reproducible Git diff from the workspace baseline. "
            "Continue with next_offset and preserve the returned whole-diff SHA-256."
        ),
        annotations=_READ_ONLY,
        structured_output=True,
    )
    async def factory_get_workspace_diff(
        workspace_id: WorkspaceId,
        offset: Offset = 0,
        limit: ByteLimit = 16384,
    ) -> dict[str, Any]:
        return await invoke(
            lambda: service().workspace_diff(workspace_id, offset=offset, limit=limit)
        )

    @server.tool(
        description=(
            "Run arbitrary Bash transactionally inside a bounded source-only bubblewrap "
            "sandbox. It has system binaries but no network, operator HOME, canonical repo, "
            "ignored targets/toolchains, or factory stores. A timeout or invalid final tree "
            "is discarded. The returned command ID resumes paged output."
        ),
        annotations=_WORKSPACE_SHELL,
        structured_output=True,
    )
    async def factory_workspace_run_shell(
        workspace_id: WorkspaceId,
        script: ShellScript,
        relative_cwd: RelativePath = ".",
        timeout_seconds: CommandTimeout = 120,
    ) -> dict[str, Any]:
        return await invoke(
            lambda: service().workspace_run_shell(
                workspace_id,
                script,
                relative_cwd=relative_cwd,
                timeout_seconds=timeout_seconds,
            )
        )

    @server.tool(
        description=(
            "Read a bounded stdout or stderr page for a workspace command after reconnect. "
            "Observed byte counts and output_truncated prevent silent completeness claims."
        ),
        annotations=_READ_ONLY,
        structured_output=True,
    )
    async def factory_get_workspace_command_output(
        workspace_id: WorkspaceId,
        command_id: CommandId,
        stream: Literal["stdout", "stderr"] = "stdout",
        offset: Offset = 0,
        limit: ByteLimit = 16384,
    ) -> dict[str, Any]:
        return await invoke(
            lambda: service().workspace_command_output(
                workspace_id,
                command_id,
                stream=stream,
                offset=offset,
                limit=limit,
            )
        )

    @server.tool(
        description=(
            "Permanently discard one disposable workspace payload. This cannot delete or "
            "modify a canonical repository, receipt, job, or accepted fact."
        ),
        annotations=_CANCEL,
        structured_output=True,
    )
    async def factory_discard_workspace(
        workspace_id: WorkspaceId,
    ) -> dict[str, Any]:
        return await invoke(lambda: service().discard_workspace(workspace_id))

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
            "Build the current acceptance registry. Summary mode returns its identity and "
            "counts with minimal context; full mode returns every classified candidate."
        ),
        annotations=_READ_ONLY,
        structured_output=True,
    )
    async def factory_get_acceptance_registry(
        detail: RegistryDetail = "summary",
    ) -> dict[str, Any]:
        return await invoke(lambda: service().accepted_registry(detail=detail))

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
            "Page through only fresh facts admitted by the acceptance registry. Summary "
            "mode minimizes context; full mode includes complete claim and result bindings."
        ),
        annotations=_READ_ONLY,
        structured_output=True,
    )
    async def factory_query_accepted_facts(
        target_identity_id: NormalizedId | None = None,
        claim_type: ClaimType | None = None,
        oracle_id: NormalizedId | None = None,
        detail: RegistryDetail = "summary",
        limit: PageLimit = 20,
        offset: Offset = 0,
    ) -> dict[str, Any]:
        return await invoke(
            lambda: service().accepted_facts(
                target_identity_id=target_identity_id,
                claim_type=claim_type,
                oracle_id=oracle_id,
                detail=detail,
                limit=limit,
                offset=offset,
            )
        )

    @server.tool(
        description=(
            "Page only the Factory-published cross-game catalog, preserving verified, "
            "provisional, unknown, and superseded status. This read-only tool never "
            "reads, nominates, or promotes game-local knowledge input."
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
        raise ToolError(
            f"{type(error).__name__}: {_redact_error(str(error), config_path)}"
        ) from error


async def _async_value(value: _T) -> _T:
    return value


def _redact_error(message: str, config_path: Path) -> str:
    redactions = {str(config_path), str(config_path.parent), str(Path.home())}
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
    return message


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


def configure_http_auth(app: Any, mode: str, token: str) -> Any:
    """Apply the explicitly selected HTTP authentication profile."""

    if mode == "none":
        return app
    if mode == "bearer":
        return BearerTokenMiddleware(app, token)
    raise ValueError(f"unsupported HTTP authentication mode: {mode}")


def mcp_path(value: str) -> str:
    """Validate one non-root URL path without query or fragment syntax."""

    if (
        not value.startswith("/")
        or value == "/"
        or value.endswith("/")
        or "//" in value
        or any(character in value for character in ("?", "#"))
        or any(
            not character.isascii() or not (character.isalnum() or character in "/._~-")
            for character in value
        )
    ):
        raise argparse.ArgumentTypeError(
            "MCP path must be an absolute, non-root path without a trailing slash, "
            "empty segment, query, or fragment"
        )
    return value


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
    parser.add_argument(
        "--mcp-path",
        type=mcp_path,
        default="/mcp",
        help="Streamable HTTP endpoint path (default: /mcp)",
    )
    parser.add_argument(
        "--auth",
        choices=("bearer", "none"),
        default="bearer",
        help="HTTP authentication profile; none is an explicit public dev mode",
    )
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
        streamable_http_path=args.mcp_path,
        json_response=True,
        stateless_http=True,
        transport_security=security,
        host=args.host,
    )
    if args.auth == "none":
        print(
            "WARNING: MCP HTTP authentication is disabled; anyone who can reach the "
            "endpoint can invoke every exposed factory tool.",
            file=sys.stderr,
        )
    uvicorn.run(
        configure_http_auth(app, args.auth, token), host=args.host, port=args.port
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
