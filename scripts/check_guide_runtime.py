"""Opt-in acceptance against a disposable, operator-prepared Spring guide.

Never imported by default tests. Reads only the launcher's random loopback
management port through the real MCP STDIO host; saves safe summaries only.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import queue
import re
import secrets
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mcp import Client, StdioServerParameters

from spring_runtime_mcp.adapters.mappings import _parse_predicate
from spring_runtime_mcp.contracts.definitions import definition
from spring_runtime_mcp.policy.output_guard import ensure_safe_output
from spring_runtime_mcp.policy.sanitization import MARKER, SanitizerPipeline
from spring_runtime_mcp.server import SERVER_INFO_META, _valid_envelope, build_services
from spring_runtime_mcp.transport.responses import serialize_response

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "examples/upstream-guides/GuideDiagnosticsLauncher.java"


def environment() -> dict[str, str]:
    # No inherited Spring, JVM, proxy or business credential overrides.
    return {
        key: value
        for key, value in os.environ.items()
        if key in {"PATH", "HOME", "LANG", "TMPDIR", "JAVA_HOME"}
    }


def ready(process: subprocess.Popen[bytes]) -> tuple[int, int]:
    ports: queue.Queue[tuple[int, int]] = queue.Queue(maxsize=1)

    def drain() -> None:
        assert process.stdout is not None
        while line := process.stdout.readline(8192):
            match = re.fullmatch(
                rb"GUIDE_DIAGNOSTICS_READY=([0-9]+);JAVA=([0-9]+)\s*", line
            )
            if match and ports.empty():
                ports.put((int(match[1]), int(match[2])))
            # Discard framework logs and exceptions without storing raw output.

    threading.Thread(target=drain, daemon=True).start()
    deadline = time.monotonic() + 60
    while process.poll() is None and time.monotonic() < deadline:
        try:
            return ports.get(timeout=0.2)
        except queue.Empty:
            continue
    raise RuntimeError("GUIDE_STARTUP_FAILED")


async def verify(
    port: int, args: argparse.Namespace, secret: str, phase: list[str]
) -> dict[str, Any]:
    env = environment()
    env["PYTHONPATH"] = str(ROOT / "src")
    command = [
        "-m",
        "spring_runtime_mcp.cli",
        "--base-url",
        f"http://127.0.0.1:{port}",
    ]
    pipeline = SanitizerPipeline((secret,))
    summaries: list[dict[str, Any]] = []
    failures: list[str] = []
    predicate_probe: dict[str, bool] | None = None

    async def call(
        client: Client, tool: str, arguments: dict[str, Any], case: str
    ) -> dict[str, Any]:
        phase[0] = case
        response = await client.call_tool(tool, arguments)
        result = response.structured_content
        assert isinstance(result, dict), case + "_NO_RESULT"
        assert _valid_envelope(definition(tool)["outputSchema"], result), (
            case + "_INVALID_SCHEMA"
        )
        ensure_safe_output(result, sanitizer=pipeline)
        encoded = serialize_response(
            result, "guide-check", sanitizer=pipeline, server_meta=SERVER_INFO_META
        )
        assert secret.encode() not in encoded, case + "_SECRET_EXPORTED"
        summaries.append(
            {
                "case": case,
                "tool": tool,
                "status": result["status"],
                "totalMatched": result["totalMatched"],
                "gaps": result["coverage"]["gaps"],
                "truncated": result["truncated"],
                "errorCodes": [error["code"] for error in result["errors"]],
                "measuredResponseBytes": len(encoded),
            }
        )
        return result

    async with Client(
        StdioServerParameters(command=sys.executable, args=command, env=env),
        mode="legacy",
        read_timeout_seconds=20,
    ) as client:
        tools = (await client.list_tools()).tools
        assert len(tools) == 8
        assert [tool.name for tool in tools] == sorted(tool.name for tool in tools)
        result = await call(
            client, "springboot_inspect_config", {"prefix": "guide"}, "config-default"
        )
        assert result["errors"][0]["code"] == "CAPABILITY_DISABLED"
        bean = "greetingController" if args.stack == "mvc" else "greetingHandler"
        result = await call(
            client,
            "springboot_inspect_beans",
            {"beanNamePattern": bean},
            "real-bean",
        )
        assert result["status"] in {"ok", "partial"}
        assert any(row["name"] == bean for row in result["data"]["items"])
        result = await call(
            client,
            "springboot_inspect_beans",
            {"beanNamePattern": "missingGuideDiagnosticsBean"},
            "missing-bean-conditions",
        )
        assert result["status"] in {"ok", "partial"}
        assert "conditions" in result["source"]["endpointIds"]
        result = await call(
            client,
            "springboot_verify_mappings",
            {"pathPattern": args.route, "httpMethod": "GET"},
            "real-route",
        )
        assert result["status"] in {"ok", "partial"}
        route_rows = [
            row for row in result["data"]["items"] if args.route in row["paths"]
        ]
        summaries[-1]["routeFacts"] = {
            "expectedRouteFound": bool(route_rows),
            "getMethodObserved": any("GET" in row["httpMethods"] for row in route_rows),
            "matchingComplete": bool(route_rows)
            and all(row["matchingComplete"] for row in route_rows),
            "acceptJsonConditionObserved": any(
                condition
                == {
                    "kind": "header",
                    "name": "Accept",
                    "value": "application/json",
                    "negated": False,
                }
                for row in route_rows
                for condition in row["conditions"]
            ),
        }
        if not route_rows:
            # Keep this a failed acceptance check, but finish independent reads.
            failures.append("REGISTERED_ROUTE_NOT_RETURNED")
            if args.stack == "webflux":
                # Export no predicate or other original response text, only
                # fixed boolean facts about this locally registered guide.
                observation = await build_services(f"http://127.0.0.1:{port}").read(
                    "local", "mappings", snapshot_id="guide-predicate-check"
                )
                body = observation.body or {}
                predicates = [
                    record["predicate"]
                    for context in body.get("contexts", {}).values()
                    for records in context.get("mappings", {})
                    .get("dispatcherHandlers", {})
                    .values()
                    for record in records
                    if isinstance(record.get("predicate"), str)
                    and "/hello" in record["predicate"]
                ]
                predicate_probe = {
                    "guidePathTokenObserved": bool(predicates),
                    "conjunctionObserved": any("&&" in text for text in predicates),
                    "acceptConditionObserved": any(
                        "Accept:" in text for text in predicates
                    ),
                    "parserAcceptedGuidePredicate": any(
                        _parse_predicate(text)[3] for text in predicates
                    ),
                }
        else:
            assert summaries[-1]["routeFacts"]["getMethodObserved"]
            assert summaries[-1]["routeFacts"]["matchingComplete"]
            if args.stack == "webflux":
                assert summaries[-1]["routeFacts"]["acceptJsonConditionObserved"]
        result = await call(
            client,
            "springboot_diagnose_health",
            {"componentPath": ["db"]},
            "hidden-health",
        )
        assert result["data"]["overallStatus"] == "UP"
        assert result["status"] == "partial" and result["totalMatched"] is None
        startup_pages = []
        for repeat in (1, 2):
            result = await call(
                client,
                "springboot_analyze_startup",
                {"minDurationMs": 1, "maxResults": 2},
                "startup-get-" + str(repeat),
            )
            assert result["status"] in {"ok", "partial"}
            assert result["data"]["springBootVersion"] == args.boot_version
            assert result["data"]["items"]
            startup_pages.append(
                [
                    (row["stepId"], row["durationNanos"])
                    for row in result["data"]["items"]
                ]
            )
        assert startup_pages[0] == startup_pages[1]
        result = await call(
            client,
            "springboot_detect_drift",
            {
                "expectedBeans": [{"name": bean}],
                "expectedRoutes": [{"path": args.route, "httpMethod": "GET"}],
                "sourceModifiedAt": "2020-01-01T00:00:00Z",
            },
            "real-drift",
        )
        assert result["status"] in {"ok", "partial"}
        assert result["data"]["missingInRuntime"] == []
        result = await call(
            client,
            "springboot_check_migrations",
            {
                "expectedMigrations": [
                    {
                        "engine": "flyway",
                        "contextId": "guide-diagnostics",
                        "migrationBean": "flyway",
                        "identity": "flyway:1",
                        "version": "1",
                    }
                ],
                "expectedSetComplete": True,
            },
            "unexposed-migrations",
        )
        assert result["data"] is None
        assert result["errors"][0]["code"] == "ENDPOINT_NOT_EXPOSED"
        result = await call(
            client,
            "springboot_search_openapi",
            {"pathPattern": args.route},
            "unexposed-openapi",
        )
        assert result["data"] is None
        assert result["errors"][0]["code"] == "ENDPOINT_NOT_EXPOSED"

    async with Client(
        StdioServerParameters(
            command=sys.executable,
            args=command
            + [
                "--config-prefix",
                "guide",
                "--config-profiles",
                "--config-allow-values",
            ],
            env=env,
        ),
        mode="legacy",
        read_timeout_seconds=20,
    ) as client:
        result = await call(
            client,
            "springboot_inspect_config",
            {"prefix": "guide", "includeValues": True},
            "registered-config",
        )
        assert result["status"] in {"ok", "partial"}
        rows = result["data"]["items"]
        assert any(
            row["propertyKey"] == "guide.mode"
            and row["effectiveValue"] == "diagnostics"
            for row in rows
        )
        assert any(
            row["propertyKey"] == MARKER
            and row["effectiveValue"] == MARKER
            and row["valueState"] == "redacted"
            for row in rows
        )
        assert any(
            row["propertyKey"] == MARKER
            and row["bindingValue"] == MARKER
            and row["bindingState"] == "redacted"
            for row in rows
        )
        result = await call(
            client,
            "springboot_detect_drift",
            {"expectedProfiles": []},
            "registered-profiles",
        )
        assert result["status"] in {"ok", "partial"}
        assert result["data"]["profileMismatch"]["state"] == "match"
    return {
        "verifiedAt": datetime.now(UTC).isoformat(),
        "sourceRevision": args.source_revision,
        "sourceRepository": args.source_repository,
        "bootVersion": args.boot_version,
        "webStack": args.stack,
        "target": "disposable-random-loopback-ports",
        "accepted": not failures,
        "failureCodes": failures,
        "predicateProbe": predicate_probe,
        "checks": summaries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--main-class", required=True)
    parser.add_argument("--boot-version", required=True)
    parser.add_argument("--stack", choices=("mvc", "webflux"), required=True)
    parser.add_argument("--route", required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--source-repository", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.source_revision):
        parser.error("source revision must be a full Git commit ID")
    classpath = os.pathsep.join(
        [
            str(args.project / "target/classes"),
            (args.project / "classpath.txt").read_text().strip(),
        ]
    )
    secret = secrets.token_urlsafe(24)
    env = environment()
    env["GUIDE_SYNTHETIC_SECRET"] = secret
    process = subprocess.Popen(
        ["java", "-cp", classpath, str(LAUNCHER), args.main_class],
        cwd=args.project,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    phase = ["startup"]
    try:
        port, java_major = ready(process)
        report = asyncio.run(verify(port, args, secret, phase))
        report["javaMajor"] = java_major
    except Exception:
        print("Guide runtime acceptance failed at " + phase[0], file=sys.stderr)
        return 1
    finally:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    report["targetProcessStopped"] = process.poll() is not None
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(
        "Guide runtime acceptance "
        + ("passed" if report["accepted"] else "failed")
        + "; safe summary:",
        args.output,
    )
    return 0 if report["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
