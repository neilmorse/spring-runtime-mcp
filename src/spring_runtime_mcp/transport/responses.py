"""Canonical bounded JSON-RPC result framing with compatible text content."""

from __future__ import annotations

import json
from typing import Any

from .. import __version__
from ..models.common import NormalizationError
from ..policy.output_guard import ensure_safe_output
from ..policy.sanitization import SanitizerPipeline

MAX_RESPONSE_BYTES = 16_384
MAX_SAFE_INTEGER = 2**53 - 1
SERVER_NAME = "spring-runtime-mcp"
SERVER_VERSION = __version__
# The SDK stamps this on every 2026-era result; the budget measurement includes
# it so a response that fits our cap also fits the stamped wire frame.
SERVER_INFO_META: dict[str, Any] = {
    "io.modelcontextprotocol/serverInfo": {
        "name": SERVER_NAME,
        "version": SERVER_VERSION,
    }
}


def _check_request_id(request_id: object) -> None:
    if isinstance(request_id, bool) or not isinstance(
        request_id, (str, int, type(None))
    ):
        raise NormalizationError("INVALID_REQUEST_ID")
    if isinstance(request_id, int) and abs(request_id) > MAX_SAFE_INTEGER:
        raise NormalizationError("INVALID_REQUEST_ID")
    if isinstance(request_id, str) and len(request_id.encode("utf-8")) > 128:
        raise NormalizationError("INVALID_REQUEST_ID")


def tool_result(
    envelope: dict[str, Any], *, server_meta: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build one tools/call result: structured content plus a compatible text copy."""
    text = json.dumps(
        envelope,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    )
    result: dict[str, Any] = {
        "resultType": "complete",
        "structuredContent": envelope,
        "content": [{"type": "text", "text": text}],
        "isError": envelope.get("status") not in ("ok", "partial"),
    }
    if server_meta is not None:
        result["_meta"] = server_meta
    return result


def serialize_response(
    envelope: dict[str, Any],
    request_id: str | int | None = None,
    *,
    sanitizer: SanitizerPipeline | None = None,
    server_meta: dict[str, Any] | None = None,
) -> bytes:
    """Measure the entire actual frame, including the duplicated JSON text.

    `server_meta` is the per-response serverInfo stamp an MCP host adds; the
    budget must include it so a page that fits here also fits on the wire.
    """
    _check_request_id(request_id)
    try:
        frame = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": tool_result(envelope, server_meta=server_meta),
        }
        encoded = json.dumps(
            frame,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as error:
        if isinstance(error, NormalizationError):
            raise
        raise NormalizationError("INVALID_RESPONSE") from None
    if len(encoded) > MAX_RESPONSE_BYTES:
        raise NormalizationError("RESPONSE_TOO_LARGE")
    ensure_safe_output(envelope, sanitizer=sanitizer)
    return encoded
