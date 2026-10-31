"""Opt-in real-project acceptance; launch only prepared disposable checkouts.

Uses original application configuration and isolated in-memory data. All target
HTTP reads go through registered endpoints; only safe result summaries persist.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import hmac
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

from spring_runtime_mcp.contracts.definitions import definition
from spring_runtime_mcp.policy.output_guard import ensure_safe_output
from spring_runtime_mcp.policy.sanitization import SanitizerPipeline
from spring_runtime_mcp.server import SERVER_INFO_META, _valid_envelope, build_services
from spring_runtime_mcp.transport.responses import serialize_response

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples/project-matrix"


def environment() -> dict[str, str]:
    return {
        key: value
        for key, value in os.environ.items()
        if key in {"PATH", "HOME", "LANG", "TMPDIR", "JAVA_HOME"}
    }


def jwt(key: bytes, authority: str) -> str:
    def encode(value: object) -> bytes:
        return base64.urlsafe_b64encode(
            json.dumps(value, separators=(",", ":")).encode()
        ).rstrip(b"=")

    now = int(time.time())
    body = (
        encode({"alg": "HS512", "typ": "JWT"})
        + b"."
        + encode(
            {
                "sub": "diagnostics",
                "auth": authority,
                "iat": now,
                "exp": now + 1200,
                "jti": secrets.token_hex(16),
            }
        )
    )
    return (
        body
        + b"."
        + base64.urlsafe_b64encode(hmac.new(key, body, hashlib.sha512).digest()).rstrip(
            b"="
        )
    ).decode()


def ready(
    process: subprocess.Popen[bytes], report: dict[str, Any], *, timeout: float = 120
) -> tuple[int, int]:
    ports: queue.Queue[tuple[int, int]] = queue.Queue(maxsize=1)

    def drain() -> None:
        assert process.stdout is not None
        while line := process.stdout.readline(8192):
            mode = re.fullmatch(
                rb"PROJECT_DIAGNOSTICS_PORT_MODE=(shared|separate)\s*", line
            )
            if mode:
                report["portMode"] = mode[1].decode()
            match = re.fullmatch(
                rb"GUIDE_DIAGNOSTICS_READY=([0-9]+);JAVA=([0-9]+)\s*", line
            )
            if match and ports.empty():
                ports.put((int(match[1]), int(match[2])))
            failed = re.fullmatch(
                rb"PROJECT_DIAGNOSTICS_ERROR=([A-Za-z0-9_.$]{1,256})\s*", line
            )
            if failed and len(report["startupErrorTypes"]) < 8:
                report["startupErrorTypes"].append(
                    SanitizerPipeline().identifier(failed[1].decode())
                )
            bean = re.fullmatch(
                rb"PROJECT_DIAGNOSTICS_(?:BEAN|CLASS)=([A-Za-z0-9_.$-]{1,256})\s*", line
            )
            if bean and len(report["startupBeanIdentifiers"]) < 8:
                report["startupBeanIdentifiers"].append(
                    SanitizerPipeline().identifier(bean[1].decode())
                )
            # All other output, including messages and stack traces, is discarded.

    threading.Thread(target=drain, daemon=True).start()
    deadline = time.monotonic() + timeout
    while process.poll() is None and time.monotonic() < deadline:
        try:
            return ports.get(timeout=0.2)
        except queue.Empty:
            continue
    raise RuntimeError("PROJECT_STARTUP_FAILED")


async def verify(
    port: int,
    config: dict[str, Any],
    key: bytes,
    report: dict[str, Any],
    phase: list[str],
) -> None:
    target = f"http://127.0.0.1:{port}"
    authenticated = config["authentication"] == "HS512-admin"
    admin = jwt(key, "ROLE_ADMIN") if authenticated else None
    user = jwt(key, "ROLE_USER") if authenticated else None
    pipeline = SanitizerPipeline(
        tuple(value for value in (admin, user, base64.b64encode(key).decode()) if value)
    )

    def parameters(
        token: str | None, *, registered_config: bool = False
    ) -> StdioServerParameters:
        env = environment()
        env["PYTHONPATH"] = str(ROOT / "src")
        args = ["-m", "spring_runtime_mcp.cli", "--base-url", target]
        if token:
            env["PROJECT_DIAGNOSTICS_BEARER"] = token
            args += ["--token-env", "PROJECT_DIAGNOSTICS_BEARER"]
        if registered_config:
            args += [
                "--config-property",
                "spring.application.name",
                "--config-profiles",
            ]
        return StdioServerParameters(command=sys.executable, args=args, env=env)

    def expect(condition: bool, code: str) -> None:
        if not condition:
            report["failureCodes"].append(code)

    async def call(
        client: Client, tool: str, args: dict[str, Any], case: str
    ) -> dict[str, Any]:
        phase[0] = case
        result = (await client.call_tool(tool, args)).structured_content
        assert isinstance(result, dict)
        assert _valid_envelope(definition(tool)["outputSchema"], result)
        ensure_safe_output(result, sanitizer=pipeline)
        frame = serialize_response(
            result, "\0" * 128, sanitizer=pipeline, server_meta=SERVER_INFO_META
        )
        report["checks"].append(
            {
                "case": case,
                "tool": tool,
                "status": result["status"],
                "totalMatched": result["totalMatched"],
                "coverage": result["coverage"]["state"],
                "gaps": result["coverage"]["gaps"],
                "truncated": result["truncated"],
                "errorCodes": [error["code"] for error in result["errors"]],
                "httpStatuses": [error["httpStatus"] for error in result["errors"]],
                "measuredResponseBytes": len(frame),
            }
        )
        return result

    if authenticated:
        for label, token in (("anonymous", None), ("non-admin", user)):
            async with Client(
                parameters(token), mode="legacy", read_timeout_seconds=20
            ) as client:
                result = await call(
                    client,
                    "springboot_inspect_beans",
                    {"beanNamePattern": config["bean"]},
                    "authorization-" + label,
                )
                expect(result["status"] == "denied", "AUTHORIZATION_NOT_ENFORCED")
                if config["openapi"]:
                    result = await call(
                        client,
                        "springboot_search_openapi",
                        {"schemaName": config["schemaName"]},
                        "openapi-authorization-" + label,
                    )
                    expect(
                        result["status"] == "denied"
                        and result["data"] is None
                        and any(
                            error["httpStatus"] == (401 if token is None else 403)
                            for error in result["errors"]
                        ),
                        "OPENAPI_AUTHORIZATION_NOT_ENFORCED",
                    )
    async with Client(
        parameters(admin), mode="legacy", read_timeout_seconds=20
    ) as client:
        tools = (await client.list_tools()).tools
        assert len(tools) == 8
        assert [tool.name for tool in tools] == sorted(tool.name for tool in tools)
        phase[0] = "reported-inventory"
        observation = await build_services(target, bearer_token=admin).read(
            "local", "beans", snapshot_id="matrix-inventory"
        )
        contexts = (observation.body or {}).get("contexts", {})
        report["reportedInventory"] = {
            "contextCount": len(contexts),
            "beanCount": sum(
                len(context.get("beans", {})) for context in contexts.values()
            ),
            "dependencyCount": sum(
                len(bean.get("dependencies", []))
                for context in contexts.values()
                for bean in context.get("beans", {}).values()
            ),
        }
        result = await call(
            client,
            "springboot_inspect_beans",
            {"beanNamePattern": config["bean"]},
            "known-bean",
        )
        expect(
            bool(result["data"])
            and any(row["name"] == config["bean"] for row in result["data"]["items"]),
            "KNOWN_BEAN_NOT_RETURNED",
        )
        result = await call(
            client,
            "springboot_inspect_beans",
            {"beanNamePattern": "missingMatrixDiagnosticsBean"},
            "missing-bean-conditions",
        )
        expect("conditions" in result["source"]["endpointIds"], "CONDITIONS_NOT_READ")
        page_args: dict[str, Any] = {
            "beanNamePattern": "*",
            "maxResults": 5,
            "maxDepth": 1,
        }
        result = await call(
            client, "springboot_inspect_beans", page_args, "bean-page-1"
        )
        cursor = result["nextCursor"]
        expect(bool(cursor), "LARGE_INVENTORY_NOT_PAGEABLE")
        if cursor:
            snapshot = result["source"]["snapshotId"]
            identifiers = {row["id"] for row in result["data"]["items"]}
            result = await call(
                client,
                "springboot_inspect_beans",
                {**page_args, "cursor": cursor},
                "bean-page-2",
            )
            expect(result["source"]["snapshotId"] == snapshot, "PAGE_SNAPSHOT_CHANGED")
            expect(
                not identifiers.intersection(
                    row["id"] for row in result["data"]["items"]
                ),
                "PAGE_DUPLICATED_RECORDS",
            )
        result = await call(
            client,
            "springboot_verify_mappings",
            {"pathPattern": config["route"], "httpMethod": "GET"},
            "known-route",
        )
        expect(
            bool(result["data"])
            and any(config["route"] in row["paths"] for row in result["data"]["items"]),
            "KNOWN_ROUTE_NOT_RETURNED",
        )
        result = await call(
            client,
            "springboot_diagnose_health",
            {"componentPath": ["db"], "includeDetails": True, "includeHealthy": True},
            "database-health",
        )
        expect(
            bool(result["data"]) and bool(result["data"]["items"]),
            "DB_HEALTH_UNOBSERVED",
        )
        result = await call(
            client,
            "springboot_analyze_startup",
            {"minDurationMs": 1, "maxResults": 5, "maxDepth": 16},
            "buffered-startup",
        )
        expect(
            bool(result["data"])
            and result["data"]["springBootVersion"] == config["bootVersion"]
            and bool(result["data"]["items"]),
            "STARTUP_VERSION_OR_STEPS_UNOBSERVED",
        )
        engine = config["migrationEngine"] or "flyway"
        result = await call(
            client, "springboot_check_migrations", {"engine": engine}, "migrations"
        )
        if config["migrationEngine"]:
            expect(
                bool(result["data"])
                and any(row["state"] == "APPLIED" for row in result["data"]["items"]),
                "APPLIED_MIGRATIONS_UNOBSERVED",
            )
            if result["data"]:
                report["checks"][-1]["appliedOnPage"] = sum(
                    row["state"] == "APPLIED" for row in result["data"]["items"]
                )
        else:
            negative = config.get(
                "expectedUnexposedMigrationError",
                {"code": "ENDPOINT_NOT_EXPOSED", "httpStatus": 404},
            )
            expect(
                bool(result["errors"])
                and result["data"] is None
                and result["errors"][0]["code"] == negative["code"]
                and result["errors"][0]["httpStatus"] == negative["httpStatus"],
                "UNEXPOSED_MIGRATION_MISREPORTED",
            )
        result = await call(
            client,
            "springboot_search_openapi",
            {"pathPattern": config["route"], "httpMethod": "GET"},
            "openapi-operation",
        )
        if config["openapi"]:
            expect(
                bool(result["data"]) and bool(result["data"]["items"]),
                "OPENAPI_OPERATION_UNOBSERVED",
            )
            result = await call(
                client,
                "springboot_search_openapi",
                {"schemaName": config["schemaName"], "maxRefDepth": 2},
                "openapi-schema",
            )
            expect(
                bool(result["data"]) and bool(result["data"]["items"]),
                "OPENAPI_SCHEMA_UNOBSERVED",
            )
            if config.get("supplementalSchemaName"):
                result = await call(
                    client,
                    "springboot_search_openapi",
                    {"schemaName": config["supplementalSchemaName"]},
                    "openapi-simple-schema",
                )
                expect(
                    bool(result["data"]) and bool(result["data"]["items"]),
                    "OPENAPI_SIMPLE_SCHEMA_UNOBSERVED",
                )
        else:
            expect(
                bool(result["errors"])
                and result["errors"][0]["code"] == "ENDPOINT_NOT_EXPOSED",
                "UNEXPOSED_OPENAPI_MISREPORTED",
            )
        result = await call(
            client, "springboot_inspect_config", {"prefix": "spring"}, "config-default"
        )
        expect(
            result["errors"][0]["code"] == "CAPABILITY_DISABLED",
            "CONFIG_DEFAULT_ENABLED",
        )
        result = await call(
            client,
            "springboot_detect_drift",
            {
                "expectedBeans": [{"name": config["bean"]}],
                "expectedRoutes": [{"path": config["route"], "httpMethod": "GET"}],
                "sourceModifiedAt": "2020-01-01T00:00:00Z",
            },
            "cross-domain-drift",
        )
        expect(
            bool(result["data"]) and not result["data"]["missingInRuntime"],
            "EXPECTED_RUNTIME_FACTS_MISMATCHED",
        )
    async with Client(
        parameters(admin, registered_config=True),
        mode="legacy",
        read_timeout_seconds=20,
    ) as client:
        result = await call(
            client,
            "springboot_inspect_config",
            {"propertyKeyPattern": "spring.application.name"},
            "registered-config",
        )
        expect(
            bool(result["data"]) and bool(result["data"]["items"]),
            "REGISTERED_CONFIG_UNOBSERVED",
        )
        result = await call(
            client,
            "springboot_detect_drift",
            {"expectedProfiles": config["profiles"]},
            "registered-profiles",
        )
        expect(
            bool(result["data"])
            and result["data"]["profileMismatch"]["state"] == "match",
            "ACTIVE_PROFILES_MISMATCHED",
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--name",
        choices=(
            "petclinic",
            "petclinic-rest",
            "jhipster",
            "jhipster-core",
            "jhipster-same-port",
            "jhipster-fixed",
        ),
        required=True,
    )
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads((FIXTURE / "projects.json").read_text())[args.name]
    report: dict[str, Any] = {
        "verifiedAt": datetime.now(UTC).isoformat(),
        "project": args.name,
        "sourceRepository": config["repository"],
        "sourceRevision": config["revision"],
        "configuredBootVersion": config["bootVersion"],
        "authentication": config["authentication"],
        "database": "disposable-in-memory-H2",
        "mainJavaSourceFiles": len(
            list((args.project / "src/main/java").rglob("*.java"))
        ),
        "checks": [],
        "failureCodes": [],
        "startupErrorTypes": [],
        "startupBeanIdentifiers": [],
    }
    revision = subprocess.check_output(
        ["git", "-C", str(args.project), "rev-parse", "HEAD"], text=True
    ).strip()
    assert revision == config["revision"]
    classpath_parts = [
        str(args.project / "target/classes"),
        (args.project / "classpath.txt").read_text().strip(),
    ]
    if config.get("classpathOverlay"):
        overlay = args.project / config["classpathOverlay"]
        patch_manifest = json.loads((overlay / "patch-manifest.json").read_text())
        assert (
            patch_manifest["patchSha256"]
            == hashlib.sha256(
                (FIXTURE / "springdoc-3.1.1-diagnostics.patch").read_bytes()
            ).hexdigest()
        )
        for name, digest in patch_manifest["classes"].items():
            assert hashlib.sha256((overlay / name).read_bytes()).hexdigest() == digest
        classpath_parts.insert(0, str(overlay))
        report["springdocPatch"] = patch_manifest
    classpath = os.pathsep.join(classpath_parts)
    key = secrets.token_bytes(64)
    env = environment()
    if config["authentication"] == "HS512-admin":
        env["JHIPSTER_SECURITY_AUTHENTICATION_JWT_BASE64_SECRET"] = base64.b64encode(
            key
        ).decode()
    process = subprocess.Popen(
        [
            "java",
            "-Xmx512m",
            "-Dspring.devtools.restart.enabled=false",
            "-cp",
            classpath,
            str(FIXTURE / "ProjectDiagnosticsLauncher.java"),
            config["mainClass"],
            str(FIXTURE / (args.name + ".properties")),
        ],
        cwd=args.project,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    phase = ["startup"]
    try:
        port, java_major = ready(process, report)
        report["javaMajor"] = java_major
        if config.get("expectedPortMode"):
            assert report.get("portMode") == config["expectedPortMode"]
        asyncio.run(verify(port, config, key, report, phase))
    except Exception:
        report["failureCodes"].append(
            "HARNESS_FAILED_AT_" + phase[0].upper().replace("-", "_")
        )
    finally:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    report["targetProcessStopped"] = process.poll() is not None
    report["accepted"] = not report["failureCodes"]
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(
        args.name,
        "accepted=" + str(report["accepted"]),
        "checks=" + str(len(report["checks"])),
        "summary:",
        args.output,
    )
    return 0 if report["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
