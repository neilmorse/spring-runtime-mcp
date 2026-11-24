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

from spring_runtime_mcp.server import SERVER_INFO_META, build_services
from spring_runtime_mcp.services import HealthBeanBinding
from spring_runtime_mcp.transport.responses import serialize_response
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


def test_gateway_routes_read_only_and_opt_in(mounted: Any) -> None:
    server, state = mounted
    path = "/actuator/gateway/routes"
    tool = "springboot_verify_mappings"
    query = {"routeSource": "gateway", "maxResults": 1}
    routes = [
        {
            "route_id": "catalog",
            "predicate": "Paths: [/api/catalog/**], match trailing slash: true",
            "uri": "lb://shop-product",
            "order": -1,
            "filters": ["synthetic-filter-value"],
        },
        {
            "route_id": "auth",
            "predicate": "Paths: [/api/auth/**], match trailing slash: false",
            "uri": "lb://shop-auth",
            "order": 0,
        },
    ]
    state.responses[path] = (200, json.dumps(routes).encode())
    disabled = _call_server(build_services(_base(server)), tool, query)[
        "structuredContent"
    ]
    assert disabled["errors"][0]["code"] == "CAPABILITY_DISABLED"
    assert disabled["errors"][0]["endpointId"] == "gateway-routes"
    assert not state.requests

    services = build_services(_base(server), gateway_routes=True)
    first = _call_server(services, tool, query)["structuredContent"]
    assert first["source"]["endpointIds"] == ["gateway-routes"]
    assert first["totalMatched"] == 2
    assert first["truncated"] is True
    assert first["nextAction"]["kind"] == "page"
    item = first["data"]["items"][0]
    assert {
        key: item[key]
        for key in ("routeId", "paths", "order", "targetService", "matchTrailingSlash")
    } == {
        "routeId": "catalog",
        "paths": ["/api/catalog/**"],
        "order": -1,
        "targetService": "shop-product",
        "matchTrailingSlash": True,
    }
    assert "synthetic-filter-value" not in json.dumps(first)
    cursor = first["nextCursor"]
    second = _call_server(services, tool, {**query, "cursor": cursor})[
        "structuredContent"
    ]
    assert second["data"]["items"][0]["routeId"] == "auth"
    assert second["nextCursor"] is None
    assert state.requests == [("GET", path)]

    mismatch = _call_server(
        services, tool, {"pathPattern": "*", "maxResults": 1, "cursor": cursor}
    )["structuredContent"]
    assert mismatch["errors"][0]["code"] == "CURSOR_QUERY_MISMATCH"
    for invalid in (
        {"method": "POST"},
        {"httpMethod": "DELETE"},
        {"controllerClassPattern": "*"},
        {"contextId": "gateway"},
        {"path": "/actuator/gateway/refresh"},
        {"endpointId": "gateway-routes"},
        {"operation": "create"},
        {"operation": "delete"},
    ):
        response = _call_server(services, tool, {**query, **invalid})[
            "structuredContent"
        ]
        assert response["errors"][0]["code"] == "INVALID_ARGUMENT"
    assert state.requests == [("GET", path)]
    assert state.writes == 0


def test_gateway_routes_preserve_unknown_evidence(mounted: Any) -> None:
    server, state = mounted
    path = "/actuator/gateway/routes"
    services = build_services(_base(server), gateway_routes=True)
    tool = "springboot_verify_mappings"
    routes = [
        {
            "route_id": "known",
            "uri": "lb://shop-product",
            "predicate": "Paths: [/catalog, /catalog/**], match trailing slash: true",
            "order": 0,
        },
        {
            "route_id": "uncertain",
            "uri": "https://user:synthetic-password@example.invalid/private",
            "predicate": "(Paths: [/catalog], match trailing slash: true || synthetic-raw-predicate)",
            "order": True,
        },
    ]
    state.responses[path] = (200, json.dumps(routes).encode())
    query = {"routeSource": "gateway"}
    result = _call_server(services, tool, query)["structuredContent"]
    assert result["status"] == "partial"
    assert result["totalMatched"] is None
    uncertain = result["data"]["items"][1]
    assert uncertain["paths"] is None
    assert uncertain["matchTrailingSlash"] is None
    assert uncertain["targetService"] is None
    assert uncertain["order"] is None
    assert "synthetic-password" not in json.dumps(result)
    assert "synthetic-raw-predicate" not in json.dumps(result)

    filtered = _call_server(services, tool, {**query, "pathPattern": "/catalog*"})[
        "structuredContent"
    ]
    assert [item["routeId"] for item in filtered["data"]["items"]] == ["known"]
    assert filtered["totalMatched"] is None

    state.responses[path] = (200, b"{}")
    malformed = _call_server(services, tool, query)["structuredContent"]
    assert malformed["errors"][0]["code"] == "UNSUPPORTED_SHAPE"
    assert malformed["data"] is None
    state.responses[path] = (404, b"{}")
    unavailable = _call_server(services, tool, query)["structuredContent"]
    assert unavailable["errors"][0]["code"] == "ENDPOINT_NOT_EXPOSED"
    assert unavailable["errors"][0]["endpointId"] == "gateway-routes"
    assert state.requests == [("GET", path)] * 4


def test_gateway_route_analysis_limit_does_not_offer_an_unavailable_page(
    mounted: Any,
) -> None:
    server, state = mounted
    path = "/actuator/gateway/routes"
    route = {
        "route_id": "catalog",
        "uri": "lb://shop-product",
        "predicate": "Paths: [/catalog/**], match trailing slash: true",
        "order": 0,
    }
    state.responses[path] = (
        200,
        json.dumps(
            [route, *([None] * 1_999), {**route, "route_id": "unobserved"}]
        ).encode(),
    )
    response = _call_server(
        build_services(_base(server), gateway_routes=True),
        "springboot_verify_mappings",
        {"routeSource": "gateway"},
    )["structuredContent"]
    assert response["status"] == "partial"
    assert response["totalMatched"] is None
    assert response["truncated"] is True
    assert response["truncationReasons"] == ["GATEWAY_ROUTE_LIMIT"]
    assert response["nextCursor"] is None
    assert [item["routeId"] for item in response["data"]["items"]] == ["catalog"]
    assert state.requests == [("GET", path)]


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


@pytest.mark.parametrize(
    ("case", "evidence_state", "read_beans"),
    [
        ("default", None, False),
        ("up", "notApplicable", False),
        ("filtered", "notApplicable", False),
        ("hidden", "unknown", False),
        ("unregistered", "unknown", False),
        ("missing", "unknown", True),
        ("unauthorized", "unknown", True),
        ("forbidden", "unknown", True),
        ("down", "observed", True),
    ],
)
def test_health_with_registered_bean_over_mcp(
    mounted: Any, case: str, evidence_state: str | None, read_beans: bool
) -> None:
    server, state = mounted
    services = build_services(_base(server))
    if case != "unregistered":
        name = "missingBean" if case == "missing" else "stripeService"
        services.health_bean_binding = HealthBeanBinding(("db",), "application", name)
    health_status = "UP" if case == "up" else "DOWN"
    db = {"status": health_status}
    if case != "hidden":
        db["details"] = {"database": "H2"}
    state.responses["/actuator/health"] = (
        200 if case == "up" else 503,
        json.dumps({"status": health_status, "components": {"db": db}}).encode(),
    )
    if case in {"unauthorized", "forbidden"}:
        state.responses["/actuator/beans"] = (
            401 if case == "unauthorized" else 403,
            b'{"message":"upstream-private-details"}',
        )
    else:
        state.responses["/actuator/beans"] = (
            200,
            b'{"contexts":{"application":{"beans":{"stripeService":{"aliases":[],"type":"example.StripeService","scope":"singleton","dependencies":["factory"]},"factory":{"aliases":[],"type":"example.Factory","scope":"singleton","dependencies":[]}}}}}',
        )

    arguments: dict[str, Any] = (
        {"includeBeanEvidence": True} if case != "default" else {}
    )
    if case == "filtered":
        arguments["componentPath"] = ["redis"]
    result = _call_server(services, "springboot_diagnose_health", arguments)

    assert result["isError"] is False
    envelope = result["structuredContent"]
    assert json.loads(result["content"][0]["text"]) == envelope
    assert envelope["data"]["overallStatus"] == health_status
    expected = [("GET", "/actuator/health")]
    if read_beans:
        expected.append(("GET", "/actuator/beans"))
    assert state.requests == expected
    if evidence_state is None:
        assert "beanEvidence" not in envelope["data"]
        return
    evidence = envelope["data"]["beanEvidence"]
    assert evidence["state"] == evidence_state
    if evidence_state == "observed":
        assert evidence["source"]["endpointId"] == "beans"
        assert evidence["source"]["snapshotId"] != envelope["source"]["snapshotId"]
        assert evidence["bean"]["name"] == "stripeService"
        assert evidence["bean"]["dependencies"][0]["targetName"] == "factory"
        assert envelope["totalMatched"] == 1
    if case in {"unauthorized", "forbidden"}:
        assert envelope["status"] == "partial"
        assert evidence["bean"] is None
        (failure,) = evidence["errors"]
        assert failure["code"] == "ENDPOINT_UNAUTHORIZED"
        assert failure["httpStatus"] == (401 if case == "unauthorized" else 403)
        assert "upstream-private-details" not in result["content"][0]["text"]


def test_health_bean_evidence_timeout_retains_health(
    mounted: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from spring_runtime_mcp.models.common import ParsedObservation

    server, state = mounted
    services = build_services(_base(server))
    services.health_bean_binding = HealthBeanBinding(
        ("db",), "application", "stripeService"
    )
    state.responses["/actuator/health"] = (
        503,
        b'{"status":"DOWN","components":{"db":{"status":"DOWN","details":{"database":"H2"}}}}',
    )
    read = services.read

    async def read_with_timeout(
        target: str, endpoint: str, snapshot_id: str
    ) -> ParsedObservation:
        if endpoint == "beans":
            raise TimeoutError
        return await read(target, endpoint, snapshot_id=snapshot_id)

    monkeypatch.setattr(services, "read", read_with_timeout)
    result = _call_server(
        services, "springboot_diagnose_health", {"includeBeanEvidence": True}
    )
    assert not result["isError"]
    envelope = result["structuredContent"]
    assert envelope["status"] == "partial"
    assert envelope["totalMatched"] == 1
    assert envelope["data"]["items"][0]["status"] == "DOWN"
    evidence = envelope["data"]["beanEvidence"]
    assert evidence["errors"][0]["code"] == "TARGET_TIMEOUT"
    assert evidence["bean"] is None


def test_health_bean_evidence_pages_and_trims_before_health_items(mounted: Any) -> None:
    server, state = mounted
    services = build_services(_base(server))
    services.health_bean_binding = HealthBeanBinding(
        ("db",), "application", "dataSource"
    )
    names = [f"factory{i}" + "x" * 240 for i in range(8)]
    beans = {
        name: {
            "aliases": [],
            "scope": "singleton",
            "type": "example.Factory",
            "dependencies": [],
        }
        for name in names
    }
    beans["dataSource"] = {
        "aliases": [],
        "scope": "singleton",
        "type": "example.DataSource",
        "dependencies": names,
    }
    state.responses["/actuator/beans"] = (
        200,
        json.dumps({"contexts": {"application": {"beans": beans}}}).encode(),
    )
    detail = {"d" + str(index): "x" * 512 for index in range(10)}
    state.responses["/actuator/health"] = (
        503,
        json.dumps(
            {
                "status": "DOWN",
                "components": {
                    "db": {"status": "DOWN", "details": detail},
                    "redis": {"status": "DOWN", "details": {"database": "H2"}},
                },
            }
        ).encode(),
    )
    arguments = {"includeBeanEvidence": True, "includeDetails": True, "maxResults": 1}
    first = _call_server(services, "springboot_diagnose_health", arguments)[
        "structuredContent"
    ]
    second = _call_server(
        services,
        "springboot_diagnose_health",
        {**arguments, "cursor": first["nextCursor"]},
    )["structuredContent"]

    assert state.requests == [("GET", "/actuator/health"), ("GET", "/actuator/beans")]
    assert first["nextAction"]["kind"] == "page"
    assert first["totalMatched"] == second["totalMatched"] == 2
    assert first["data"]["items"][0]["details"]
    first_evidence = first["data"]["beanEvidence"]
    second_evidence = second["data"]["beanEvidence"]
    assert first_evidence["source"] == second_evidence["source"]
    assert "HEALTH_BEAN_EVIDENCE_BUDGET" in first["truncationReasons"]
    assert len(second_evidence["bean"]["dependencies"]) == 8
    for envelope in (first, second):
        assert (
            len(serialize_response(envelope, 1, server_meta=SERVER_INFO_META)) <= 16_384
        )


@pytest.mark.parametrize("enabled", [False, True])
def test_thread_tool_cli_registration_and_snapshot(mounted: Any, enabled: bool) -> None:
    server, state = mounted
    thread_rows = [
        {
            "threadId": 1,
            "threadState": "BLOCKED",
            "lockOwnerId": 2,
            "threadName": "PRIVATE_THREAD",
        },
        {"threadId": 2, "threadState": "TIMED_WAITING", "lockOwnerId": 1},
        {
            "threadId": 3,
            "threadState": "BLOCKED",
            "lockOwnerId": 4,
            "stackTrace": [{"fileName": "PRIVATE_PATH"}],
        },
        {"threadId": 4, "threadState": "RUNNABLE", "lockOwnerId": -1},
    ]
    state.responses["/actuator/threaddump"] = (
        200,
        json.dumps({"threads": thread_rows}).encode(),
    )
    with subprocess.Popen(
        [
            sys.executable,
            "-m",
            "spring_runtime_mcp.cli",
            "--base-url",
            _base(server),
            *(["--enable-thread-diagnostics"] if enabled else []),
        ],
        cwd=ROOT,
        env=dict(os.environ, PYTHONPATH=str(ROOT / "src")),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ) as process:
        initialization = _frame(
            process,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": LATEST_HANDSHAKE_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "thread-test", "version": "1"},
                },
            },
        )
        assert initialization["id"] == 1
        assert process.stdin is not None
        process.stdin.write(b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
        process.stdin.flush()
        listed = _frame(process, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        tools = listed["result"]["tools"]
        names = [tool["name"] for tool in tools]
        name = "springboot_analyze_threads"
        assert names == sorted(names) and len(names) == (9 if enabled else 8)
        assert (name in names) == enabled
        assert state.requests == []
        request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": name, "arguments": {"maxResults": 1}},
        }
        first = _frame(process, request)
        if not enabled:
            assert first["error"]["code"] == -32602
            assert state.requests == []
            process.stdin.close()
            return
        info = next(tool for tool in tools if tool["name"] == name)
        assert info["annotations"]["readOnlyHint"] is True
        assert info["annotations"]["destructiveHint"] is False
        assert info["annotations"]["idempotentHint"] is True
        assert info["annotations"]["openWorldHint"] is False
        first_result = first["result"]
        assert not first_result["isError"]
        first_data = first_result["structuredContent"]
        assert first_data["data"]["items"] == [
            {
                "kind": "cycle",
                "threadIds": ["1", "2"],
                "length": 2,
                "containsTimedWait": True,
            }
        ]

        request["id"] = 4
        request["params"]["arguments"]["cursor"] = first_data["nextCursor"]
        second_result = _frame(process, request)["result"]
        process.stdin.close()
        assert not second_result["isError"]
        second_data = second_result["structuredContent"]
        assert second_data["data"]["items"] == [
            {
                "kind": "chain",
                "threadIds": ["3", "4"],
                "end": "endOfObservedChain",
            }
        ]
        assert first_data["source"] == second_data["source"]
        assert first_data["totalMatched"] == second_data["totalMatched"] == 2
        assert second_data["nextCursor"] is None
        for result in (first_result, second_result):
            assert (
                json.loads(result["content"][0]["text"]) == result["structuredContent"]
            )
            assert "PRIVATE_" not in result["content"][0]["text"]
        assert state.requests == [("GET", "/actuator/threaddump")]
    assert process.returncode == 0


@pytest.mark.parametrize(
    ("status", "body", "error_code"),
    [
        (401, b'{"error":"private upstream body"}', "ENDPOINT_UNAUTHORIZED"),
        (403, b'{"error":"private upstream body"}', "ENDPOINT_UNAUTHORIZED"),
        (404, b"{}", "ENDPOINT_NOT_EXPOSED"),
        (503, b'{"threads":[]}', "ENDPOINT_UNAVAILABLE"),
        (200, b"x" * (8 * 1024 * 1024 + 1), "RESPONSE_TOO_LARGE"),
    ],
)
def test_thread_dump_rejects_unusable_http_response(
    mounted: Any, status: int, body: bytes, error_code: str
) -> None:
    server, state = mounted
    state.responses["/actuator/threaddump"] = (status, body)
    result = _call_server(
        build_services(_base(server), thread_diagnostics=True),
        "springboot_analyze_threads",
        {},
    )
    assert result["isError"]
    evidence = result["structuredContent"]
    assert evidence["data"] is None and evidence["totalMatched"] is None
    error = evidence["errors"][0]
    assert error["code"] == error_code
    assert error["endpointId"] == "threaddump"
    assert "private upstream" not in result["content"][0]["text"]
    assert state.requests == [("GET", "/actuator/threaddump")]


def test_thread_tool_enforces_wire_budget_without_losing_snapshot_items(
    mounted: Any,
) -> None:
    server, state = mounted
    services = build_services(_base(server), thread_diagnostics=True)
    rows = []
    for start in range(55):
        root = 9_000_000_000_000_000_000 + start * 20
        for offset in range(16):
            rows.append(
                {
                    "threadId": root + offset,
                    "threadState": "BLOCKED" if offset < 15 else "RUNNABLE",
                    "lockOwnerId": root + offset + 1 if offset < 15 else -1,
                }
            )
    state.responses["/actuator/threaddump"] = (
        200,
        json.dumps({"threads": rows}).encode(),
    )
    arguments: dict[str, Any] = {}
    collected = []
    snapshot_id = None
    for page in range(55):
        result = _call_server(services, "springboot_analyze_threads", arguments)
        assert not result["isError"]
        evidence = result["structuredContent"]
        assert (
            len(serialize_response(evidence, 1, server_meta=SERVER_INFO_META)) <= 16_384
        )
        assert evidence["totalMatched"] == 55
        assert evidence["data"]["waitChainCount"] == 55
        if page == 0:
            assert 0 < len(evidence["data"]["items"]) < 50
            snapshot_id = evidence["source"]["snapshotId"]
        assert evidence["source"]["snapshotId"] == snapshot_id
        collected.extend(item["threadIds"][0] for item in evidence["data"]["items"])
        if evidence["nextCursor"] is None:
            break
        arguments = {"cursor": evidence["nextCursor"]}
    assert collected == [str(9_000_000_000_000_000_000 + i * 20) for i in range(55)]
    assert state.requests == [("GET", "/actuator/threaddump")]


def test_thread_tool_preserves_unknown_owner_and_rejects_query_overrides(
    mounted: Any,
) -> None:
    server, state = mounted
    services = build_services(_base(server), thread_diagnostics=True)
    tool = "springboot_analyze_threads"
    invalid = _call_server(services, tool, {"path": "/actuator/health"})
    assert invalid["structuredContent"]["errors"][0]["code"] == "INVALID_ARGUMENT"
    assert state.requests == []
    state.responses["/actuator/threaddump"] = (
        200,
        b'{"threads":[{"threadId":1,"threadState":"BLOCKED","lockOwnerId":2}]}',
    )
    result = _call_server(services, tool, {})
    assert not result["isError"]
    evidence = result["structuredContent"]
    assert evidence["status"] == "partial"
    assert evidence["totalMatched"] is None
    assert evidence["data"]["waitCycleStatus"] == "unknown"
    assert evidence["data"]["items"] == [
        {"kind": "chain", "threadIds": ["1", "2"], "end": "ownerUnobserved"},
    ]
    assert evidence["coverage"]["gaps"] == ["THREAD_LOCK_OWNER_UNOBSERVED"]
