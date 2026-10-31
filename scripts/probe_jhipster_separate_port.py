"""Opt-in causal experiment on a prepared disposable JHipster checkout.

Disable only inclusion of Actuator operations in OpenAPI; keep native API-docs,
separate loopback ports and JWT. Never request a grouped/custom HTTP path.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import secrets
import shutil
import subprocess
import tempfile
from pathlib import Path

from check_project_runtime import FIXTURE, environment, jwt, ready

from spring_runtime_mcp.contracts.definitions import definition
from spring_runtime_mcp.policy.output_guard import ensure_safe_output
from spring_runtime_mcp.policy.sanitization import SanitizerPipeline
from spring_runtime_mcp.server import SERVER_INFO_META, _valid_envelope, build_services
from spring_runtime_mcp.tools.registry import call_tool
from spring_runtime_mcp.transport.responses import serialize_response


async def inspect(port: int, key: bytes) -> dict:
    admin = jwt(key, "ROLE_ADMIN")
    pipeline = SanitizerPipeline((admin, base64.b64encode(key).decode()))
    services = build_services(f"http://127.0.0.1:{port}", bearer_token=admin)
    checks = []
    for tool, arguments in (
        ("springboot_inspect_beans", {"beanNamePattern": "userService"}),
        ("springboot_search_openapi", {"schemaName": "AdminUserDTO"}),
        ("springboot_verify_mappings", {"pathPattern": "/actuator/openapi*"}),
        ("springboot_verify_mappings", {"controllerClassPattern": "*OpenApi*"}),
        (
            "springboot_inspect_beans",
            {"beanNamePattern": "multipleOpenApiActuatorResource", "maxDepth": 0},
        ),
        (
            "springboot_inspect_beans",
            {"beanNamePattern": "openAPIDefaultGroupedOpenAPI", "maxDepth": 0},
        ),
    ):
        result = await call_tool(tool, arguments, services)
        assert _valid_envelope(definition(tool)["outputSchema"], result)
        ensure_safe_output(result, sanitizer=pipeline)
        frame = serialize_response(
            result, chr(0) * 128, sanitizer=pipeline, server_meta=SERVER_INFO_META
        )
        checks.append(
            {
                "tool": tool,
                "arguments": arguments,
                "status": result["status"],
                "totalMatched": result["totalMatched"],
                "returnedItems": len((result.get("data") or {}).get("items", [])),
                "beanNames": [
                    row["name"]
                    for row in (result.get("data") or {}).get("items", [])
                    if "name" in row
                ],
                "errorCodes": [e["code"] for e in result["errors"]],
                "httpStatuses": [e["httpStatus"] for e in result["errors"]],
                "measuredResponseBytes": len(frame),
                "mappingPaths": sorted(
                    {
                        path
                        for row in (result.get("data") or {}).get("items", [])
                        for path in row.get("paths", [])
                    }
                ),
            }
        )
    return {"checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads((FIXTURE / "projects.json").read_text())["jhipster"]
    revision = subprocess.check_output(
        ["git", "-C", str(args.project), "rev-parse", "HEAD"], text=True
    ).strip()
    assert revision == config["revision"]
    key = secrets.token_bytes(64)
    env = environment()
    env["JHIPSTER_SECURITY_AUTHENTICATION_JWT_BASE64_SECRET"] = base64.b64encode(
        key
    ).decode()
    report = {
        "experiment": "separate-port-without-actuator-operation-docs",
        "sourceRevision": revision,
        "startupErrorTypes": [],
        "startupBeanIdentifiers": [],
        "started": False,
    }
    with tempfile.TemporaryDirectory(prefix="jhipster-docs-probe-") as temporary:
        properties = Path(temporary) / "diagnostics.properties"
        properties.write_text(
            (FIXTURE / "jhipster.properties").read_text()
            + "\nspringdoc.show-actuator=false\nspring.profiles.group.dev=api-docs\n"
        )
        shutil.copyfile(
            FIXTURE / "logback-diagnostics.xml",
            Path(temporary) / "logback-diagnostics.xml",
        )
        process = subprocess.Popen(
            [
                "java",
                "-Xmx512m",
                "-Dspring.devtools.restart.enabled=false",
                "-cp",
                str(args.project / "target/classes")
                + ":"
                + (args.project / "classpath.txt").read_text().strip(),
                str(FIXTURE / "ProjectDiagnosticsLauncher.java"),
                config["mainClass"],
                str(properties),
            ],
            cwd=args.project,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        try:
            port, major = ready(process, report)
            report["started"] = True
            report["javaMajor"] = major
            report.update(asyncio.run(inspect(port, key)))
        except Exception:
            report["experimentError"] = "PROBE_FAILED"
        finally:
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        report["targetProcessStopped"] = process.poll() is not None
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return int("experimentError" in report)


if __name__ == "__main__":
    raise SystemExit(main())
