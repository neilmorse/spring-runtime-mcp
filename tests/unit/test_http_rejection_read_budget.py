"""Rejected HTTP statuses must not consume an upstream response body."""

from __future__ import annotations

import asyncio
import gzip
from typing import Any

import pytest

from spring_runtime_mcp.transport.actuator_http import ActuatorHttpTransport
from spring_runtime_mcp.diagnostics import SAFE_CODES
from spring_runtime_mcp.models.common import NormalizationError
from spring_runtime_mcp.replay import services_for
from spring_runtime_mcp.tools.registry import call_tool
from spring_runtime_mcp.transport.response_gate import (
    EndpointReadError,
    ResponseGateReader,
)
from conformance.assertions import validator


class _Response:
    def __init__(
        self,
        status: int,
        content_type: str = "application/json",
        content_encoding: str | None = None,
        body: bytes = b'{"status":"DOWN"}',
        chunk_size: int = 65536,
    ) -> None:
        self.status = status
        self.content_type = content_type
        self.content_encoding = content_encoding
        self.reads = 0
        self.body = body
        self.offset = 0
        self.chunk_size = chunk_size
        self.length: int | None = None

    def read(self, amount: int) -> bytes:
        self.reads += 1
        chunk = self.body[self.offset : self.offset + min(amount, self.chunk_size)]
        self.offset += len(chunk)
        return chunk

    def getheader(self, name: str) -> str | None:
        return {
            "Content-Type": self.content_type,
            "Content-Encoding": self.content_encoding,
        }.get(name)


class _Connection:
    def __init__(self, response: _Response) -> None:
        self.response = response
        self.requests: list[dict[str, Any]] = []
        self.closed = False

    def request(self, **kwargs: Any) -> None:
        self.requests.append(kwargs)

    def getresponse(self) -> _Response:
        return self.response

    def close(self) -> None:
        self.closed = True


@pytest.mark.parametrize(
    ("status", "endpoint", "code"),
    [
        (302, "health", "REDIRECT_BLOCKED"),
        (401, "health", "ENDPOINT_UNAUTHORIZED"),
        (403, "health", "ENDPOINT_UNAUTHORIZED"),
        (404, "health", "ENDPOINT_NOT_EXPOSED"),
        (404, "startup", "STARTUP_DATA_UNAVAILABLE"),
        (500, "health", "ENDPOINT_UNAVAILABLE"),
        (503, "beans", "ENDPOINT_UNAVAILABLE"),
    ],
)
def test_rejected_status_does_not_read_body(
    monkeypatch: pytest.MonkeyPatch, status: int, endpoint: str, code: str
) -> None:
    response = _Response(status)
    connection = _Connection(response)
    transport = ActuatorHttpTransport(
        "http://127.0.0.1:12345", targets=frozenset({"local"})
    )
    monkeypatch.setattr(transport, "_open", lambda timeout, state: connection)
    gate = ResponseGateReader(transport, frozenset({"local"}), frozenset({endpoint}))
    with pytest.raises(EndpointReadError) as failure:
        asyncio.run(gate.read("local", endpoint, snapshot_id="snapshot"))
    assert failure.value.code == code
    assert failure.value.http_status == status
    assert response.reads == 0
    assert connection.closed
    assert connection.requests[0]["method"] == "GET"


def test_health_503_still_reads_valid_health_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = _Response(503)
    connection = _Connection(response)
    transport = ActuatorHttpTransport(
        "http://127.0.0.1:12345", targets=frozenset({"local"})
    )
    monkeypatch.setattr(transport, "_open", lambda timeout, state: connection)
    gate = ResponseGateReader(transport, frozenset({"local"}), frozenset({"health"}))
    observation = asyncio.run(gate.read("local", "health", snapshot_id="snapshot"))
    assert observation.body == {"status": "DOWN"}
    assert observation.http_status == 503
    assert response.reads > 0
    assert connection.closed


@pytest.mark.parametrize("status", [200, 503])
def test_unexpected_content_type_does_not_read_body(
    monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    response = _Response(status, "text/html")
    connection = _Connection(response)
    transport = ActuatorHttpTransport(
        "http://127.0.0.1:12345", targets=frozenset({"local"})
    )
    monkeypatch.setattr(transport, "_open", lambda timeout, state: connection)
    gate = ResponseGateReader(transport, frozenset({"local"}), frozenset({"health"}))
    with pytest.raises(EndpointReadError) as failure:
        asyncio.run(gate.read("local", "health", snapshot_id="snapshot"))
    assert failure.value.code == "UNEXPECTED_CONTENT_TYPE"
    assert response.reads == 0
    assert connection.closed


@pytest.mark.parametrize(
    "media",
    [
        "application/json; charset=UTF-8",
        "application/vnd.spring-boot.actuator.v2+json",
        "application/vnd.spring-boot.actuator.v3+json",
    ],
)
def test_accepted_json_content_types_still_read_body(
    monkeypatch: pytest.MonkeyPatch, media: str
) -> None:
    response = _Response(200, media)
    connection = _Connection(response)
    transport = ActuatorHttpTransport(
        "http://127.0.0.1:12345", targets=frozenset({"local"})
    )
    monkeypatch.setattr(transport, "_open", lambda timeout, state: connection)
    gate = ResponseGateReader(transport, frozenset({"local"}), frozenset({"health"}))
    assert asyncio.run(gate.read("local", "health", snapshot_id="snapshot")).body == {
        "status": "DOWN"
    }
    assert response.reads > 0


@pytest.mark.parametrize("encoding", ["br", "gzip, identity", "", "unknown"])
def test_unsupported_content_encoding_is_rejected_without_reading(
    monkeypatch: pytest.MonkeyPatch, encoding: str
) -> None:
    response = _Response(200, content_encoding=encoding)
    connection = _Connection(response)
    transport = ActuatorHttpTransport(
        "http://127.0.0.1:12345", targets=frozenset({"local"})
    )
    monkeypatch.setattr(transport, "_open", lambda timeout, state: connection)
    gate = ResponseGateReader(transport, frozenset({"local"}), frozenset({"health"}))
    with pytest.raises(EndpointReadError) as failure:
        asyncio.run(gate.read("local", "health", snapshot_id="snapshot"))
    assert failure.value.code == "UNSUPPORTED_CONTENT_ENCODING"
    assert failure.value.http_status == 200
    assert response.reads == 0
    assert connection.closed
    assert "UNSUPPORTED_CONTENT_ENCODING" in SAFE_CODES


@pytest.mark.parametrize("encoding", [None, "identity", " Identity "])
def test_identity_content_encoding_remains_readable(
    monkeypatch: pytest.MonkeyPatch, encoding: str | None
) -> None:
    response = _Response(200, content_encoding=encoding)
    connection = _Connection(response)
    transport = ActuatorHttpTransport(
        "http://127.0.0.1:12345", targets=frozenset({"local"})
    )
    monkeypatch.setattr(transport, "_open", lambda timeout, state: connection)
    gate = ResponseGateReader(transport, frozenset({"local"}), frozenset({"health"}))
    observation = asyncio.run(gate.read("local", "health", snapshot_id="snapshot"))
    assert observation.body == {"status": "DOWN"}
    assert response.reads > 0


def test_gate_preserves_a_transport_endpoint_error() -> None:
    class RejectedTransport:
        async def request(self, *args: Any, **kwargs: Any) -> Any:
            raise EndpointReadError("UNSUPPORTED_CONTENT_ENCODING", "health", 200)

    gate = ResponseGateReader(
        RejectedTransport(), frozenset({"local"}), frozenset({"health"})
    )
    with pytest.raises(EndpointReadError) as failure:
        asyncio.run(gate.read("local", "health", snapshot_id="snapshot"))
    assert failure.value.code == "UNSUPPORTED_CONTENT_ENCODING"
    assert failure.value.endpoint_id == "health"
    assert failure.value.http_status == 200


def test_unsupported_encoding_produces_a_safe_tool_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = _Response(200, content_encoding="br")
    connection = _Connection(response)
    transport = ActuatorHttpTransport(
        "http://127.0.0.1:12345", targets=frozenset({"local"})
    )
    monkeypatch.setattr(transport, "_open", lambda timeout, state: connection)
    services = services_for("boot-3.4-servlet")
    services.reader = ResponseGateReader(
        transport, frozenset({"local"}), frozenset({"health"})
    )
    result = asyncio.run(call_tool("springboot_diagnose_health", {}, services))
    validator("springboot_diagnose_health").validate(result)
    assert result["status"] == "unavailable"
    assert result["data"] is None
    assert result["errors"][0]["code"] == "UNSUPPORTED_CONTENT_ENCODING"
    assert result["errors"][0]["httpStatus"] == 200
    assert response.reads == 0


def _read_compressed(
    monkeypatch: pytest.MonkeyPatch, body: bytes, limit: int, chunk_size: int = 65536
) -> bytes:
    response = _Response(200, content_encoding="gzip", body=body, chunk_size=chunk_size)
    connection = _Connection(response)
    transport = ActuatorHttpTransport(
        "http://127.0.0.1:12345", targets=frozenset({"local"})
    )
    monkeypatch.setattr(transport, "_open", lambda timeout, state: connection)
    try:
        result = asyncio.run(
            transport.request(
                "local",
                "health",
                method="GET",
                follow_redirects=False,
                timeout=2,
                max_bytes=limit,
            )
        )
    finally:
        assert connection.closed
    return result.body


@pytest.mark.parametrize("chunk_size", [1, 65536])
def test_gzip_json_is_decoded_within_both_limits(
    monkeypatch: pytest.MonkeyPatch, chunk_size: int
) -> None:
    body = b'{"status":"DOWN"}'
    assert _read_compressed(monkeypatch, gzip.compress(body), 128, chunk_size) == body


@pytest.mark.parametrize("shape", ["truncated", "crc", "trailing", "multiple"])
@pytest.mark.parametrize("chunk_size", [1, 65536])
def test_gzip_invalid_or_multiple_members_are_rejected(
    monkeypatch: pytest.MonkeyPatch, shape: str, chunk_size: int
) -> None:
    data = gzip.compress(b'{"status":"DOWN"}')
    if shape == "truncated":
        data = data[:-3]
    elif shape == "crc":
        data = data[:-8] + bytes([data[-8] ^ 1]) + data[-7:]
    elif shape == "trailing":
        data += b"junk"
    else:
        data += gzip.compress(b"second")
    with pytest.raises(NormalizationError, match="INVALID_COMPRESSED_DATA"):
        _read_compressed(monkeypatch, data, 512, chunk_size)
    assert "INVALID_COMPRESSED_DATA" in SAFE_CODES


@pytest.mark.parametrize("shape", ["encoded", "decoded"])
def test_gzip_encoded_and_decoded_limits_are_independent(
    monkeypatch: pytest.MonkeyPatch, shape: str
) -> None:
    body = bytes(range(256)) if shape == "encoded" else b"a" * 10000
    with pytest.raises(NormalizationError, match="RESPONSE_TOO_LARGE"):
        _read_compressed(monkeypatch, gzip.compress(body), 128)


@pytest.mark.parametrize("chunk_size", [1, 65536])
def test_gzip_exact_encoded_and_decoded_limits_are_accepted(
    monkeypatch: pytest.MonkeyPatch, chunk_size: int
) -> None:
    data = gzip.compress(b'{"status":"DOWN"}')
    assert (
        _read_compressed(monkeypatch, data, len(data), chunk_size)
        == b'{"status":"DOWN"}'
    )
    assert (
        _read_compressed(monkeypatch, gzip.compress(b"a" * 128), 128, chunk_size)
        == b"a" * 128
    )
