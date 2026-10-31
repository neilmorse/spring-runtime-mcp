"""Loopback proof for the stdlib connector and the MCP stdio host."""

from __future__ import annotations

import asyncio
import gzip
import json
import os
import select
import socket
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from mcp_types.version import LATEST_HANDSHAKE_VERSION

from spring_runtime_mcp.server import build_services
from spring_runtime_mcp.diagnostics import SAFE_CODES

from harness.host import dispatch
from spring_runtime_mcp.tools.inspect_beans import Services
from spring_runtime_mcp.tools.inspect_beans import inspect_beans
from spring_runtime_mcp.policy.configuration import ConfigReadPolicy
from spring_runtime_mcp.transport.actuator_http import ActuatorHttpTransport
from spring_runtime_mcp.transport.response_gate import (
    EndpointReadError,
    ResponseGateReader,
)

ROOT = Path(__file__).resolve().parents[2]
BEANS = (ROOT / "tests/fixtures/bean_graph/parent-child/beans.json").read_bytes()
_ORIG_CREATE = socket.create_connection
_ORIG_GETADDRINFO = socket.getaddrinfo
_ORIG_CONNECT = socket.socket.connect
_ORIG_CONNECT_EX = socket.socket.connect_ex
_LOOPBACK = {"127.0.0.1", "::1", "localhost"}


def _host(address: object) -> object:
    if isinstance(address, tuple):
        return address[0]
    return address


@pytest.fixture(autouse=True)
def allow_loopback_only(
    monkeypatch: pytest.MonkeyPatch, prohibit_network: None
) -> None:
    """Undo the session network ban for this module, and only for loopback."""

    def create_connection(address: Any, *args: Any, **kwargs: Any) -> Any:
        if _host(address) not in _LOOPBACK:
            raise AssertionError("Offline tests must not access the network")
        return _ORIG_CREATE(address, *args, **kwargs)

    def getaddrinfo(host: Any, *args: Any, **kwargs: Any) -> Any:
        if host not in _LOOPBACK:
            raise AssertionError("Offline tests must not access the network")
        return _ORIG_GETADDRINFO(host, *args, **kwargs)

    def connect(self: socket.socket, address: Any) -> Any:
        if _host(address) not in _LOOPBACK:
            raise AssertionError("Offline tests must not access the network")
        return _ORIG_CONNECT(self, address)

    def connect_ex(self: socket.socket, address: Any) -> Any:
        if _host(address) not in _LOOPBACK:
            raise AssertionError("Offline tests must not access the network")
        return _ORIG_CONNECT_EX(self, address)

    monkeypatch.setattr(socket, "create_connection", create_connection)
    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket.socket, "connect_ex", connect_ex)


class _Mount:
    def __init__(self) -> None:
        self.mode = "beans"
        self.paths: list[str] = []
        self.requests: list[tuple[str, str]] = []
        self.responses: dict[str, tuple[int, bytes]] = {}
        self.writes = 0
        self.startup_buffer = [1, 2, 3]
        self.lock = threading.Lock()


def _handler_for(state: _Mount) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, format: str, *args: object) -> None:
            return

        def do_GET(self) -> None:
            path = self.path.split("?", 1)[0]
            with state.lock:
                state.paths.append(path)
                state.requests.append((self.command, self.path))
                mode = state.mode
                response = state.responses.get(path)
            if path == "/stolen":
                body = b"followed"
                self._send(200, "text/plain", body)
                return
            if mode == "redirect":
                host, port = self.server.server_address[:2]
                location = f"http://{host}:{port}/stolen"
                self.send_response(302)
                self.send_header("Location", location)
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", "0")
                self.send_header("Connection", "close")
                self.end_headers()
                return
            if mode == "oversize":
                body = b"x" * 8000
                self._send(200, "application/json", body)
                return
            if response is not None:
                status, body = response
                self._send(status, "application/json", body)
                return
            if path == "/actuator/beans":
                self._send(200, "application/json", BEANS)
                return
            self._send(404, "application/json", b"{}")

        def do_POST(self) -> None:
            # Model a write-capable Actuator: POST startup consumes its buffer.
            with state.lock:
                state.requests.append((self.command, self.path))
                state.writes += 1
                if self.path == "/actuator/startup":
                    state.startup_buffer.clear()
            self._send(200, "application/json", b"{}")

        do_PUT = do_POST
        do_PATCH = do_POST
        do_DELETE = do_POST

        def _send(self, status: int, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                return

    return Handler


@pytest.fixture
def mounted() -> Any:
    state = _Mount()
    server = ThreadingHTTPServer(("127.0.0.1", 0), _handler_for(state))
    server.handle_error = lambda *args, **kwargs: None  # type: ignore[method-assign]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, state
    finally:
        server.shutdown()
        server.server_close()


def _base(server: ThreadingHTTPServer) -> str:
    host, port = server.server_address[:2]
    return f"http://{host}:{port}"


def _call_server(
    services: Services, tool: str, arguments: dict[str, Any]
) -> dict[str, Any]:
    frame = asyncio.run(
        dispatch(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": tool, "arguments": arguments},
            },
            services,
        )
    )
    assert frame is not None
    return json.loads(frame)["result"]


@pytest.mark.parametrize(
    "tool,arguments,endpoints",
    [
        ("springboot_analyze_startup", {}, ["startup"]),
        ("springboot_check_migrations", {}, ["flyway", "liquibase"]),
        (
            "springboot_detect_drift",
            {"expectedBeans": [{"name": "orderService"}]},
            ["beans"],
        ),
        ("springboot_diagnose_health", {}, ["health"]),
        (
            "springboot_inspect_beans",
            {"beanNamePattern": "absentBean"},
            ["beans", "conditions"],
        ),
        (
            "springboot_inspect_config",
            {"prefix": "spring.application"},
            ["env", "configprops"],
        ),
        (
            "springboot_search_openapi",
            {"pathPattern": "/orders", "httpMethod": "POST"},
            ["openapi"],
        ),
        (
            "springboot_verify_mappings",
            {"pathPattern": "/orders", "httpMethod": "DELETE"},
            ["mappings"],
        ),
    ],
)
def test_server_tools_are_readonly_on_wire_and_reject_request_overrides(
    mounted: Any, tool: str, arguments: dict[str, Any], endpoints: list[str]
) -> None:
    server, state = mounted
    fixtures = ROOT / "tests/fixtures/conformance/boot-3.4-servlet"
    for endpoint in endpoints:
        filename = "health-v3" if endpoint == "health" else endpoint
        state.responses[f"/actuator/{endpoint}"] = (
            200,
            (fixtures / f"{filename}.json").read_bytes(),
        )
    # Keep the on-wire assertions; grant only this synthetic config scenario.
    services = build_services(
        _base(server),
        config_policy=ConfigReadPolicy(prefixes=frozenset({"spring.application"}))
        if tool == "springboot_inspect_config"
        else None,
    )
    result = _call_server(services, tool, arguments)
    assert result["isError"] is False
    assert result["structuredContent"]["status"] in {"ok", "partial"}
    expected = [("GET", f"/actuator/{endpoint}") for endpoint in endpoints]
    assert state.requests == expected
    assert state.writes == 0
    assert state.startup_buffer == [1, 2, 3]

    for override in (
        {"method": "POST"},
        {"url": _base(server) + "/actuator/shutdown"},
        {"path": "/actuator/heapdump"},
        {"endpointId": "logfile"},
        {"headers": {"X-HTTP-Method-Override": "DELETE"}},
    ):
        rejected = _call_server(services, tool, {**arguments, **override})
        assert rejected["isError"] is True
        assert rejected["structuredContent"]["errors"][0]["code"] == "INVALID_ARGUMENT"
        assert state.requests == expected
    rejected = _call_server(services, tool, {**arguments, "targetId": "unregistered"})
    assert rejected["isError"] is True
    assert rejected["structuredContent"]["errors"][0]["code"] == "TARGET_NOT_REGISTERED"
    assert state.requests == expected
    assert state.writes == 0
    assert state.startup_buffer == [1, 2, 3]


@pytest.mark.parametrize(
    "status,code",
    [
        (404, "STARTUP_DATA_UNAVAILABLE"),
        (405, "ENDPOINT_UNAVAILABLE"),
        (500, "ENDPOINT_UNAVAILABLE"),
        (503, "ENDPOINT_UNAVAILABLE"),
    ],
)
def test_server_startup_get_failure_never_falls_back_to_post(
    mounted: Any, status: int, code: str
) -> None:
    server, state = mounted
    state.responses["/actuator/startup"] = (status, b"{}")
    result = _call_server(
        build_services(_base(server)), "springboot_analyze_startup", {}
    )
    assert result["isError"] is True
    assert result["structuredContent"]["errors"][0]["code"] == code
    assert state.requests == [("GET", "/actuator/startup")]
    assert state.writes == 0
    assert state.startup_buffer == [1, 2, 3]


@pytest.mark.parametrize("status", [500, 503])
def test_startup_server_error_suggests_collection_without_claiming_a_cause(
    mounted: Any, status: int
) -> None:
    from conformance.assertions import assert_contract

    server, state = mounted
    state.responses["/actuator/startup"] = (status, b"{}")
    result = _call_server(
        build_services(_base(server)), "springboot_analyze_startup", {}
    )
    envelope = result["structuredContent"]
    assert_contract("springboot_analyze_startup", envelope)
    diagnostic = envelope["errors"][0]
    assert diagnostic["code"] == "ENDPOINT_UNAVAILABLE"
    assert diagnostic["httpStatus"] == status
    assert diagnostic["endpointId"] == "startup"
    remediation = diagnostic["remediation"]
    assert remediation["action"] == "configureStartup"
    assert remediation["requiresApproval"] is True
    steps = " ".join(remediation["steps"])
    assert "BufferingApplicationStartup" in steps
    assert "if collection is absent" in steps
    assert "does not identify" in steps
    assert "version" in steps and "exposure" in steps
    assert state.requests == [("GET", "/actuator/startup")]
    assert state.writes == 0 and state.startup_buffer == [1, 2, 3]


def test_server_tool_does_not_follow_redirect_to_an_unregistered_path(
    mounted: Any,
) -> None:
    server, state = mounted
    state.mode = "redirect"
    result = _call_server(
        build_services(_base(server)), "springboot_analyze_startup", {}
    )
    assert result["isError"] is True
    assert result["structuredContent"]["errors"][0]["code"] == "REDIRECT_BLOCKED"
    assert state.requests == [("GET", "/actuator/startup")]
    assert state.writes == 0
    assert state.startup_buffer == [1, 2, 3]


def test_real_http_transport_with_loopback_actuator(mounted: Any) -> None:
    server, _state = mounted
    services = build_services(_base(server), "local", 5.0)
    result = asyncio.run(
        inspect_beans(
            {"beanNamePattern": "orderService", "contextId": "application"},
            services,
        )
    )
    assert result["status"] in ("ok", "partial")
    assert any(item["name"] == "orderService" for item in result["data"]["items"])


def test_tc_bug_03_localhost_uses_only_approved_numeric_addresses(mounted: Any) -> None:
    """TC-BUG-03: dual-stack localhost still reaches the registered IPv4 fixture."""
    server, state = mounted
    services = build_services(f"http://localhost:{server.server_port}")
    result = asyncio.run(inspect_beans({"beanNamePattern": "orderService"}, services))
    assert result["status"] in {"ok", "partial"}
    assert any(row["name"] == "orderService" for row in result["data"]["items"])
    assert state.requests == [("GET", "/actuator/beans")]


@pytest.mark.parametrize("cancel", [False, True], ids=["deadline", "cancellation"])
def test_tc_bug_09_real_slow_stream_is_closed(cancel: bool) -> None:
    """TC-BUG-09: real loopback streaming stops after deadline or cancellation."""
    reading = threading.Event()
    peer_closed = threading.Event()
    stop = threading.Event()

    class SlowHandler(BaseHTTPRequestHandler):
        def log_message(self, *args: Any) -> None:
            return None

        def do_GET(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", "1048576")
            self.end_headers()
            reading.set()
            try:
                while not stop.wait(0.01):
                    self.wfile.write(b" ")
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                peer_closed.set()

    fixture = ThreadingHTTPServer(("127.0.0.1", 0), SlowHandler)
    thread = threading.Thread(target=fixture.serve_forever, daemon=True)
    thread.start()

    async def exercise() -> None:
        reader = ResponseGateReader(
            ActuatorHttpTransport(_base(fixture), targets=frozenset({"local"})),
            frozenset({"local"}),
            frozenset({"health"}),
            timeout=0.2,
        )
        task = asyncio.create_task(reader.read("local", "health", snapshot_id="slow"))
        assert await asyncio.to_thread(reading.wait, 1), "fixture was never reached"
        if cancel:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        else:
            with pytest.raises(EndpointReadError, match="TARGET_TIMEOUT"):
                await task
        assert await asyncio.to_thread(peer_closed.wait, 1), (
            "HTTP socket remained open after cancellation"
        )

    try:
        asyncio.run(exercise())
    finally:
        stop.set()
        fixture.shutdown()
        fixture.server_close()
        thread.join(timeout=2)


@pytest.mark.parametrize(
    ("status", "content_type", "content_encoding", "code"),
    [
        (302, "application/json", None, "REDIRECT_BLOCKED"),
        (401, "application/json", None, "ENDPOINT_UNAUTHORIZED"),
        (200, "text/html", None, "UNEXPECTED_CONTENT_TYPE"),
        (503, "text/html", None, "UNEXPECTED_CONTENT_TYPE"),
        (200, "application/json", "deflate", "UNSUPPORTED_CONTENT_ENCODING"),
        (503, "application/json", "br", "UNSUPPORTED_CONTENT_ENCODING"),
    ],
)
def test_rejected_status_returns_without_waiting_for_slow_body(
    status: int, content_type: str, content_encoding: str | None, code: str
) -> None:
    release = threading.Event()
    headers_ready = threading.Event()
    accepted_encodings: list[str | None] = []

    class DelayedBodyHandler(BaseHTTPRequestHandler):
        def log_message(self, *args: Any) -> None:
            return None

        def do_GET(self) -> None:
            accepted_encodings.append(self.headers.get("Accept-Encoding"))
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            if content_encoding is not None:
                self.send_header("Content-Encoding", content_encoding)
            self.send_header("Content-Length", "1024")
            headers_ready.set()
            self.end_headers()
            release.wait(2)

    fixture = ThreadingHTTPServer(("127.0.0.1", 0), DelayedBodyHandler)
    thread = threading.Thread(target=fixture.serve_forever, daemon=True)
    thread.start()

    async def exercise() -> None:
        reader = ResponseGateReader(
            ActuatorHttpTransport(_base(fixture), targets=frozenset({"local"})),
            frozenset({"local"}),
            frozenset({"health"}),
            timeout=0.5,
        )
        with pytest.raises(EndpointReadError) as failure:
            await reader.read("local", "health", snapshot_id="slow-error")
        assert headers_ready.is_set()
        assert not release.is_set()
        assert failure.value.code == code
        assert failure.value.http_status == status
        assert accepted_encodings == ["identity"]

    try:
        asyncio.run(exercise())
    finally:
        release.set()
        fixture.shutdown()
        fixture.server_close()
        thread.join(timeout=2)


def test_real_http_transport_blocks_redirect_and_oversize(mounted: Any) -> None:
    server, state = mounted
    base = _base(server)
    transport = ActuatorHttpTransport(base, targets=frozenset({"local"}))
    with pytest.raises(AssertionError, match="READ_ONLY_TRANSPORT"):
        asyncio.run(
            transport.request(
                "local",
                "beans",
                method="POST",
                follow_redirects=False,
                timeout=2,
                max_bytes=1000,
            )
        )
    with pytest.raises(AssertionError, match="READ_ONLY_TRANSPORT"):
        asyncio.run(
            transport.request(
                "local",
                "beans",
                method="GET",
                follow_redirects=True,
                timeout=2,
                max_bytes=1000,
            )
        )
    assert state.paths == []

    state.mode = "redirect"
    reader = ResponseGateReader(
        transport,
        targets=frozenset({"local"}),
        enabled_endpoints=frozenset({"beans"}),
        timeout=2,
    )
    with pytest.raises(EndpointReadError) as captured:
        asyncio.run(reader.read("local", "beans", snapshot_id="redirect-snap"))
    assert captured.value.code == "REDIRECT_BLOCKED"
    assert captured.value.http_status == 302
    assert state.paths == ["/actuator/beans"]

    state.mode = "oversize"
    state.paths.clear()
    response = asyncio.run(
        transport.request(
            "local",
            "beans",
            method="GET",
            follow_redirects=False,
            timeout=2,
            max_bytes=1000,
        )
    )
    assert response.status == 200
    assert len(response.body) == 1001
    assert state.paths == ["/actuator/beans"]


@pytest.mark.parametrize("shape", ["single", "multiple", "interim", "below"])
def test_response_headers_are_bounded_during_parsing(shape: str) -> None:
    class OversizedHeaders(BaseHTTPRequestHandler):
        def log_message(self, *args: Any) -> None:
            return None

        def do_GET(self) -> None:
            if shape == "interim":
                self.wfile.write(
                    b"HTTP/1.1 100 Continue\r\nX-Interim: " + b"a" * 17000 + b"\r\n\r\n"
                )
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", "15")
            if shape == "single":
                self.send_header("X-Large", "a" * 33000)
            elif shape == "multiple":
                for index in range(40):
                    self.send_header(f"X-{index}", "a" * 1000)
            elif shape == "interim":
                self.send_header("X-Final", "a" * 17000)
            else:
                self.send_header("X-Below", "a" * 32000)
            self.end_headers()
            try:
                self.wfile.write(b'{"status":"UP"}')
            except (BrokenPipeError, ConnectionResetError):
                pass

    fixture = ThreadingHTTPServer(("127.0.0.1", 0), OversizedHeaders)
    fixture.handle_error = lambda *args, **kwargs: None  # type: ignore[method-assign]
    thread = threading.Thread(target=fixture.serve_forever, daemon=True)
    thread.start()
    try:
        gate = ResponseGateReader(
            ActuatorHttpTransport(_base(fixture), targets=frozenset({"local"})),
            frozenset({"local"}),
            frozenset({"health"}),
            timeout=2,
        )
        if shape == "below":
            result = asyncio.run(
                gate.read("local", "health", snapshot_id="large-headers")
            )
            assert result.body == {"status": "UP"}
        else:
            with pytest.raises(EndpointReadError) as failure:
                asyncio.run(gate.read("local", "health", snapshot_id="large-headers"))
            assert failure.value.code == "RESPONSE_HEADERS_TOO_LARGE"
            assert "RESPONSE_HEADERS_TOO_LARGE" in SAFE_CODES
    finally:
        fixture.shutdown()
        fixture.server_close()
        thread.join(timeout=2)


@pytest.mark.parametrize(
    ("status", "chunked"), [(200, False), (503, False), (200, True)]
)
def test_gzip_health_json_is_decoded_from_loopback(status: int, chunked: bool) -> None:
    class CompressedHealth(BaseHTTPRequestHandler):
        def log_message(self, *args: Any) -> None:
            return None

        def do_GET(self) -> None:
            payload = gzip.compress(b'{"status":"DOWN"}')
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Encoding", "gzip")
            if chunked:
                self.send_header("Transfer-Encoding", "chunked")
            else:
                self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            if chunked:
                for part in (payload[:5], payload[5:]):
                    self.wfile.write(f"{len(part):x}\r\n".encode() + part + b"\r\n")
                self.wfile.write(b"0\r\n\r\n")
            else:
                self.wfile.write(payload)

    fixture = ThreadingHTTPServer(("127.0.0.1", 0), CompressedHealth)
    thread = threading.Thread(target=fixture.serve_forever, daemon=True)
    thread.start()
    try:
        gate = ResponseGateReader(
            ActuatorHttpTransport(_base(fixture), targets=frozenset({"local"})),
            frozenset({"local"}),
            frozenset({"health"}),
            timeout=2,
        )
        result = asyncio.run(gate.read("local", "health", snapshot_id="gzip"))
        assert result.body == {"status": "DOWN"}
        assert result.http_status == status
    finally:
        fixture.shutdown()
        fixture.server_close()
        thread.join(timeout=2)


@pytest.mark.parametrize(
    ("status", "compressed"), [(200, False), (503, False), (200, True), (503, True)]
)
def test_short_content_length_body_cannot_be_accepted(
    status: int, compressed: bool
) -> None:
    class ShortBody(BaseHTTPRequestHandler):
        def log_message(self, *args: Any) -> None:
            return None

        def do_GET(self) -> None:
            body = b'{"status":"DOWN"}'
            payload = gzip.compress(body) if compressed else body
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            if compressed:
                self.send_header("Content-Encoding", "gzip")
            self.send_header("Content-Length", str(len(payload) + 10))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(payload)
            self.close_connection = True

    fixture = ThreadingHTTPServer(("127.0.0.1", 0), ShortBody)
    thread = threading.Thread(target=fixture.serve_forever, daemon=True)
    thread.start()
    try:
        gate = ResponseGateReader(
            ActuatorHttpTransport(_base(fixture), targets=frozenset({"local"})),
            frozenset({"local"}),
            frozenset({"health"}),
            timeout=2,
        )
        with pytest.raises(EndpointReadError) as failure:
            asyncio.run(gate.read("local", "health", snapshot_id="short-body"))
        assert failure.value.code == "INCOMPLETE_RESPONSE"
        assert "INCOMPLETE_RESPONSE" in SAFE_CODES
    finally:
        fixture.shutdown()
        fixture.server_close()
        thread.join(timeout=2)


def _frame(process: subprocess.Popen[bytes], payload: dict[str, Any]) -> dict[str, Any]:
    assert process.stdin is not None and process.stdout is not None
    process.stdin.write(json.dumps(payload).encode("utf-8") + b"\n")
    process.stdin.flush()
    ready, _, _ = select.select([process.stdout], [], [], 5)
    assert ready, "timed out waiting for an MCP frame"
    line = process.stdout.readline()
    assert line
    parsed: dict[str, Any] = json.loads(line)
    return parsed


def test_mcp_stdio_lifecycle_drift_and_unknown_tool(mounted: Any) -> None:
    server, _state = mounted
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "spring_runtime_mcp.cli",
            "--base-url",
            _base(server),
            "--timeout",
            "5",
        ],
        cwd=ROOT,
        env=dict(os.environ, PYTHONPATH=str(ROOT / "src")),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        initialized = _frame(
            process,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2026-07-28",
                    "capabilities": {},
                    "clientInfo": {"name": "audit", "version": "0"},
                },
            },
        )
        assert initialized["id"] == 1
        # RW-02: a handshake-era request must negotiate a version the SDK
        # actually serves instead of echoing a modern revision it cannot obey.
        assert initialized["result"]["protocolVersion"] == LATEST_HANDSHAKE_VERSION
        assert initialized["result"]["serverInfo"]["name"] == "spring-runtime-mcp"
        assert process.stdin is not None
        process.stdin.write(b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
        process.stdin.flush()
        listed = _frame(process, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        names = [item["name"] for item in listed["result"]["tools"]]
        assert names == sorted(names) and len(names) == 8
        assert "springboot_inspect_beans" in names
        assert "springboot_diagnose_health" in names

        beans = _frame(
            process,
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "springboot_inspect_beans",
                    "arguments": {
                        "beanNamePattern": "orderService",
                        "contextId": "application",
                    },
                },
            },
        )
        assert beans["result"]["isError"] is False
        found = beans["result"]["structuredContent"]["data"]["items"]
        assert any(item["name"] == "orderService" for item in found)

        drift = _frame(
            process,
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "springboot_detect_drift",
                    "arguments": {"expectedBeans": [{"name": "orderService"}]},
                },
            },
        )
        assert drift["result"]["isError"] is False
        diagnosis = drift["result"]["structuredContent"]
        assert diagnosis["status"] in ("ok", "partial")
        assert diagnosis["data"]["missingInRuntime"] == []
        assert diagnosis["data"]["profileMismatch"] is None
        unknown = _frame(
            process,
            {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {
                    "name": "not_a_spring_tool",
                    "arguments": {},
                },
            },
        )
        assert unknown["error"]["code"] == -32602
    finally:
        if process.stdin:
            process.stdin.close()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        stderr = process.stderr.read() if process.stderr else b""
        assert b"Traceback" not in stderr
