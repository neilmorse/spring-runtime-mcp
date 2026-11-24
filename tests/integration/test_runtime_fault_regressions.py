"""Keep unavailable-attribution and readiness assertions independent of Spring."""

from __future__ import annotations

import asyncio
import json
import os
import socket
import ssl
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from mcp import Client, StdioServerParameters

from conformance.assertions import assert_contract
from harness.protocol_fixture import ProtocolFaultFixture
from scripts.runtime_benchmarks.targets import STATION_TOKEN_ENV, _HEALTH_HTTP


def test_failed_target_does_not_invent_migration_cause() -> None:
    async def query(port: int) -> None:
        params = StdioServerParameters(
            command=sys.executable,
            args=[
                "-m",
                "spring_runtime_mcp.cli",
                "--base-url",
                f"http://127.0.0.1:{port}",
            ],
        )
        tool = "springboot_check_migrations"
        async with Client(params, mode="legacy", read_timeout_seconds=30) as client:
            reply = await client.call_tool(tool, {"engine": "flyway"})
        assert reply.is_error
        result = reply.structured_content
        assert isinstance(result, dict)
        assert json.loads(reply.content[0].text) == result
        assert_contract(tool, result)
        assert result["status"] == "unavailable"
        assert result["coverage"]["state"] == "unavailable"
        assert result["data"] is None and result["totalMatched"] is None
        assert [error["code"] for error in result["errors"]] == [
            "TARGET_CONNECTION_REFUSED"
        ]

    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        asyncio.run(query(reservation.getsockname()[1]))


@pytest.mark.parametrize("scheme", ["http", "https"])
def test_runtime_readiness_never_follows_redirects(
    scheme: str, loopback_tls: tuple[ssl.SSLContext, Path]
) -> None:
    paths: list[str] = []
    token = "synthetic-readiness-token"

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            pass

        def do_GET(self) -> None:
            paths.append(self.path)
            if (
                scheme == "https"
                and self.headers.get("Authorization") != "Bearer " + token
            ):
                self.send_error(401)
                return
            self.send_response(302)
            self.send_header("Location", "/trap")
            self.end_headers()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    context, ca_file = loopback_tls
    if scheme == "https":
        server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        args = [sys.executable, "-c", _HEALTH_HTTP, str(server.server_port), scheme]
        env = {
            key: os.environ[key]
            for key in ("PATH", "SYSTEMROOT", "WINDIR")
            if key in os.environ
        }
        env[STATION_TOKEN_ENV] = token
        rejected = subprocess.run(args, env=env, capture_output=True, timeout=10)
        assert rejected.returncode != 0 and token.encode() not in rejected.stderr
        assert paths == []
        if scheme == "https":
            env["SSL_CERT_FILE"] = str(ca_file)
        else:
            del env[STATION_TOKEN_ENV]
        result = subprocess.run(args, env=env, capture_output=True, timeout=10)
        assert result.returncode == 0 and result.stdout == b"302\n"
        assert paths == ["/actuator/health"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.parametrize(
    "trust_fixture", [False, True], ids=["unknown-ca", "wrong-san"]
)
def test_host_checks_tls_identity_before_sending_bearer(
    trust_fixture: bool, loopback_tls: tuple[ssl.SSLContext, Path]
) -> None:
    context, ca_file = loopback_tls
    token = "synthetic-identity-check"
    fixture = ProtocolFaultFixture(token, context)

    async def query() -> None:
        # The leaf SAN contains only 127.0.0.1. localhost exercises name validation.
        origin = (
            fixture.origin.replace("127.0.0.1", "localhost")
            if trust_fixture
            else fixture.origin
        )
        env = {"FIXTURE_TOKEN": token}
        if trust_fixture:
            env["SSL_CERT_FILE"] = str(ca_file)
        params = StdioServerParameters(
            command=sys.executable,
            args=[
                "-m",
                "spring_runtime_mcp.cli",
                "--base-url",
                origin,
                "--token-env",
                "FIXTURE_TOKEN",
            ],
            env=env,
        )
        async with Client(params, mode="legacy", read_timeout_seconds=15) as client:
            reply = await client.call_tool("springboot_diagnose_health", {})
        result = reply.structured_content
        assert reply.is_error and isinstance(result, dict)
        assert [error["code"] for error in result["errors"]] == [
            "TLS_VERIFICATION_FAILED"
        ]
        assert token not in reply.model_dump_json()

    try:
        asyncio.run(query())
        assert not fixture.requests
    finally:
        fixture.close()
