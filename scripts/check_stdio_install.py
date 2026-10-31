"""Check installed MCP pipes and resources using only a disposable loopback fixture."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import queue
import shutil
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from typing import Any
from typing import Literal

from jsonschema import Draft202012Validator
from mcp import Client, StdioServerParameters

CALLS: dict[str, tuple[dict[str, Any], str]] = {
    "springboot_analyze_startup": ({}, "startup"),
    "springboot_check_migrations": ({"engine": "flyway"}, "flyway"),
    "springboot_detect_drift": (
        {"expectedBeans": [{"name": "orderService"}]},
        "beans",
    ),
    "springboot_diagnose_health": ({}, "health"),
    "springboot_inspect_beans": ({"beanNamePattern": "orderService"}, "beans"),
    "springboot_inspect_config": (
        {"prefix": "spring.application", "includeValues": True},
        "env",
    ),
    "springboot_search_openapi": ({"schemaName": "Address"}, "openapi"),
    "springboot_verify_mappings": ({"pathPattern": "/orders"}, "mappings"),
}
SECRET = "synthetic-release-gate-secret"
FIELD_SECRET = "synthetic-config-value"


def verify_pipes(command: str) -> None:
    """Read initialize before sending later requests; inspect every stdout byte."""
    resource = files("spring_runtime_mcp")
    profile = resource.joinpath("replay_data/conformance/boot-3.4-servlet")
    bodies = {
        f"/actuator/{endpoint}": json.loads(
            profile.joinpath(
                "health-v3.json" if endpoint == "health" else f"{endpoint}.json"
            ).read_text(encoding="utf-8")
        )
        for endpoint in (
            "beans",
            "conditions",
            "health",
            "flyway",
            "liquibase",
            "startup",
            "openapi",
            "mappings",
            "env",
            "configprops",
        )
    }
    bodies["/actuator/env"]["propertySources"][0]["properties"].update(
        {
            f"spring.application.{key}": {"value": value}
            for key, value in {
                "password": FIELD_SECRET + "-password",
                "secret": FIELD_SECRET + "-secret",
                "token": FIELD_SECRET + "-token",
                "privateKey": f"-----BEGIN PRIVATE KEY-----{FIELD_SECRET}",  # fake PEM header
                "jdbcUrl": f"jdbc:postgresql://user:{FIELD_SECRET}@localhost/db",
            }.items()
        }
    )
    config_bean = next(
        iter(
            bodies["/actuator/configprops"]["contexts"]["application"]["beans"].values()
        )
    )
    for key, prop in bodies["/actuator/env"]["propertySources"][0][
        "properties"
    ].items():
        field = key.removeprefix("spring.application.")
        config_bean["properties"][field] = prop["value"]
        config_bean["inputs"][field] = prop
    requests: list[tuple[str, str]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            requests.append((self.command, self.path))
            payload = json.dumps(bodies.get(self.path, {})).encode()
            self.send_response(200 if self.path in bodies else 404)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args: Any) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("SPRING_RUNTIME_")
        and key not in {"PYTHONPATH", "PYTHONHOME"}
    }
    environment["RELEASE_GATE_TOKEN"] = SECRET
    command_args = [
        command,
        "--base-url",
        f"http://127.0.0.1:{server.server_port}",
        "--token-env",
        "RELEASE_GATE_TOKEN",
        "--config-prefix",
        "spring.application",
        "--config-allow-values",
    ]
    lines: queue.Queue[bytes] = queue.Queue()
    with tempfile.TemporaryFile() as errors, tempfile.TemporaryDirectory() as cwd:
        process = subprocess.Popen(
            command_args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=errors,
            env=environment,
            cwd=cwd,
        )

        def collect() -> None:
            assert process.stdout is not None
            while True:
                line = process.stdout.readline(512 * 1024 + 1)
                lines.put(line)
                if not line or len(line) > 512 * 1024:
                    return

        reader = threading.Thread(target=collect, daemon=True)
        reader.start()

        def send(payload: dict[str, Any]) -> None:
            assert process.stdin is not None
            process.stdin.write(json.dumps(payload).encode() + b"\n")
            process.stdin.flush()

        def request(
            identifier: int, method: str, params: dict[str, Any]
        ) -> dict[str, Any]:
            send(
                {"jsonrpc": "2.0", "id": identifier, "method": method, "params": params}
            )
            line = lines.get(timeout=15)
            assert line.endswith(b"\n")
            assert SECRET.encode() not in line and FIELD_SECRET.encode() not in line
            response = json.loads(line)
            assert response["jsonrpc"] == "2.0" and response["id"] == identifier
            assert "result" in response, f"{method} returned a protocol error"
            if method == "tools/call":
                assert len(line.rstrip(b"\n")) <= 16384
            return response["result"]

        try:
            initialized = request(
                1,
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "release-gate", "version": "1"},
                },
            )
            assert initialized["protocolVersion"] == "2024-11-05"
            send({"jsonrpc": "2.0", "method": "notifications/initialized"})
            tools = request(2, "tools/list", {})["tools"]
            assert [tool["name"] for tool in tools] == list(CALLS)
            assert requests == [], "discovery must not access a target"
            for identifier, tool in enumerate(tools, 3):
                Draft202012Validator.check_schema(tool["inputSchema"])
                Draft202012Validator.check_schema(tool["outputSchema"])
                for hint, expected in {
                    "readOnlyHint": True,
                    "destructiveHint": False,
                    "idempotentHint": True,
                    "openWorldHint": False,
                }.items():
                    assert tool["annotations"][hint] is expected
                arguments, endpoint = CALLS[tool["name"]]
                Draft202012Validator(tool["inputSchema"]).validate(arguments)
                before = len(requests)
                result = request(
                    identifier,
                    "tools/call",
                    {
                        "name": tool["name"],
                        "arguments": arguments,
                    },
                )
                envelope = result["structuredContent"]
                Draft202012Validator(tool["outputSchema"]).validate(envelope)
                assert json.loads(result["content"][0]["text"]) == envelope
                assert not result.get("isError", False), tool["name"]
                assert ("GET", f"/actuator/{endpoint}") in requests[before:]
            assert all(method == "GET" and path in bodies for method, path in requests)
            assert process.stdin is not None
            process.stdin.close()
            assert process.wait(timeout=15) == 0
            reader.join(timeout=5)
            assert not reader.is_alive()
            assert lines.get(timeout=1) == b"", "unexpected stdout after final response"
            assert lines.empty()
            errors.seek(0)
            stderr = errors.read()
            assert SECRET.encode() not in stderr and FIELD_SECRET.encode() not in stderr
            assert b"Traceback" not in stderr
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
    print(
        "Raw stdio passed: staged 2024-11-05 handshake, 8 real HTTP handlers, schemas, hints, sanitization and 16 KiB frames."
    )


def verify_replay(command: str) -> None:
    """Use the installed interpreter beside the console entrypoint, outside the repo."""
    python = Path(command).with_name("python.exe" if os.name == "nt" else "python")
    with tempfile.TemporaryDirectory() as cwd:
        for scenario in (
            "parent-child",
            "stripe-missing",
            "factory-method",
            "nested-conditions",
            "boot-2.7-servlet",
            "boot-3.4-servlet",
            "boot-4.1-webflux",
        ):
            completed = subprocess.run(
                [
                    str(python),
                    "-I",
                    "-m",
                    "spring_runtime_mcp.replay",
                    "--scenario",
                    scenario,
                    "--tool",
                    "springboot_inspect_beans",
                    "--arguments-json",
                    '{"beanNamePattern":"orderService"}',
                ],
                cwd=cwd,
                capture_output=True,
                check=True,
                timeout=15,
            )
            assert len(completed.stdout.splitlines()) == 1
            frame = json.loads(completed.stdout)
            assert not frame["result"]["isError"], scenario
            envelope = frame["result"]["structuredContent"]
            assert json.loads(frame["result"]["content"][0]["text"]) == envelope
            if scenario in {"stripe-missing", "factory-method"}:
                assert "FIXTURE_SUBSTITUTED" in envelope["coverage"]["gaps"]
    print("Installed replay passed all 7 packaged scenarios outside the source tree.")


async def verify(command: str) -> None:
    modes: tuple[Literal["legacy", "2026-07-28"], ...] = ("legacy", "2026-07-28")
    for mode in modes:
        async with Client(
            StdioServerParameters(command=command),
            mode=mode,
            read_timeout_seconds=15,
        ) as client:
            tools = (await client.list_tools()).tools
            assert len(tools) == 8
            assert [tool.name for tool in tools] == sorted(tool.name for tool in tools)
            assert all(tool.output_schema for tool in tools)
            result = await client.call_tool(
                "springboot_diagnose_health", {"maxResults": 0}
            )
            assert (
                result.is_error
                and isinstance(result.structured_content, dict)
                and result.structured_content["errors"][0]["code"] == "INVALID_ARGUMENT"
            )
            disabled = await client.call_tool(
                "springboot_inspect_config", {"prefix": "spring.application"}
            )
            assert disabled.is_error and isinstance(disabled.structured_content, dict)
            assert (
                disabled.structured_content["errors"][0]["code"]
                == "CAPABILITY_DISABLED"
            )
    print(
        "Installed stdio entrypoint passed legacy and 2026-07-28 discovery and tool-error checks."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--command", required=True)
    args = parser.parse_args()
    installed_command = shutil.which(args.command)
    if installed_command is None:
        parser.error("--command must name an installed spring-runtime-mcp entrypoint")
    command = str(Path(installed_command).absolute())
    asyncio.run(verify(command))
    verify_pipes(command)
    verify_replay(command)


if __name__ == "__main__":
    main()
