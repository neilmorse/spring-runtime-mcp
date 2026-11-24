"""One opt-in, read-only view of a registered target's visible lock waits."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import uuid4

from ..adapters.thread_dump import analyze_thread_dump
from ..contracts.definitions import THREAD_TOOL, validate_arguments
from ..diagnostics import failed, partial
from ..models.common import NormalizationError
from ..models.queries import ThreadQuery
from ..services import Services
from ..transport.response_gate import EndpointReadError
from .support import finalize, read_checked, resume, shell, stamp, tool_handler

_ENDPOINT = "threaddump"


@tool_handler
async def analyze_threads(
    arguments: Mapping[str, Any], services: Services
) -> dict[str, Any]:
    target = "local"
    try:
        query = validate_arguments(arguments, THREAD_TOOL)
        assert isinstance(query, ThreadQuery)
        target = query.target_id
        if not services.thread_diagnostics:
            return failed("CAPABILITY_DISABLED", target, endpoint=_ENDPOINT)
        if query.cursor:
            return resume(services, query, include_server_meta=True)

        snapshot = uuid4().hex
        observation = await read_checked(services, target, _ENDPOINT, snapshot)
        if observation.body is None:
            raise NormalizationError("UNSUPPORTED_SHAPE")
        analysis = await services.analyze(analyze_thread_dump, observation.body)
        result = shell(target, "threadDump", "threaddump-1")
        stamp(result, observation, _ENDPOINT, snapshot)
        coverage = analysis.pop("coverage")
        bounded_paths = analysis.pop("truncated")
        cycles = analysis.pop("waitCycles")
        chains = analysis.pop("waitChains")
        analysis["stateCounts"] = [
            {"state": state, "count": count}
            for state, count in analysis["stateCounts"].items()
        ]
        analysis["items"] = [
            *({"kind": "cycle", **item} for item in cycles),
            *({"kind": "chain", **item} for item in chains),
        ]
        result["data"] = analysis
        gaps = coverage["gaps"]
        result["totalMatched"] = None if gaps else len(analysis["items"])
        if bounded_paths:
            result["truncated"] = True
            result["truncationReasons"] = ["THREAD_PATH_LIMIT"]
            gaps.append("THREAD_PATH_LIMIT")
        partial(result, gaps)
        return finalize(result, services, query, include_server_meta=True)
    except NormalizationError as exc:
        return failed(
            exc.code,
            target,
            endpoint=_ENDPOINT,
            http_status=exc.http_status if isinstance(exc, EndpointReadError) else None,
        )
    except TimeoutError:
        return failed("TARGET_TIMEOUT", target, endpoint=_ENDPOINT)
