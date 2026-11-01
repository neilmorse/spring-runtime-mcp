"""Build an isolated demo mutation and verify faults through MCP STDIO."""

from __future__ import annotations

import asyncio
import argparse
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from http.client import HTTPConnection, HTTPException
from pathlib import Path
from typing import Any

from mcp import Client, StdioServerParameters

from spring_runtime_mcp.contracts.definitions import definition
from spring_runtime_mcp.policy.output_guard import ensure_safe_output
from spring_runtime_mcp.policy.sanitization import SanitizerPipeline
from spring_runtime_mcp.server import SERVER_INFO_META, _valid_envelope
from spring_runtime_mcp.transport.responses import serialize_response

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "examples/injected-faults/runtime-results.json"


def clean_env() -> dict[str, str]:
    return {
        key: os.environ[key]
        for key in ("PATH", "HOME", "JAVA_HOME", "LANG", "TMPDIR")
        if key in os.environ
    }


def free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def stop(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def wait_ready(
    process: subprocess.Popen[bytes], port: int, token: str | None = None
) -> int:
    headers = {"Authorization": "Bearer " + token} if token else {}
    for _ in range(180):
        if process.poll() is not None:
            raise RuntimeError("TARGET_EXITED")
        connection = HTTPConnection("127.0.0.1", port, timeout=1)
        try:
            connection.request("GET", "/actuator/health", headers=headers)
            status = connection.getresponse().status
            if 300 <= status < 400:
                raise RuntimeError("READINESS_REDIRECT_BLOCKED")
            if status in (200, 503):
                return status
        except (HTTPException, TimeoutError, OSError):
            pass
        finally:
            connection.close()
        time.sleep(0.5)
    raise RuntimeError("TARGET_NOT_READY")


async def verify(
    port: int, phase: str, report: dict[str, Any], source_catalog: Path
) -> None:
    env = dict(clean_env(), PYTHONPATH=str(ROOT / "src"), PYTHONDONTWRITEBYTECODE="1")
    params = StdioServerParameters(
        command=sys.executable,
        args=[
            "-m",
            "spring_runtime_mcp.cli",
            "--base-url",
            f"http://127.0.0.1:{port}",
            "--source-catalog",
            str(source_catalog),
        ],
        env=env,
    )
    cases = [
        (
            "beans",
            "springboot_inspect_beans",
            {
                "beanNamePattern": "paymentGateway",
                "contextId": "demo",
                "conditionDepth": 4,
            },
        ),
        (
            "route",
            "springboot_verify_mappings",
            {"pathPattern": "/orders/{id}", "httpMethod": "GET", "contextId": "demo"},
        ),
        ("health", "springboot_diagnose_health", {}),
        ("migration", "springboot_check_migrations", {"engine": "flyway"}),
        (
            "drift",
            "springboot_detect_drift",
            {
                "expectedBeans": [{"name": "paymentGateway", "contextId": "demo"}],
                "expectedRoutes": [{"path": "/orders/{id}", "httpMethod": "GET"}],
                "expectedScopeComplete": True,
            },
        ),
    ]
    pipeline = SanitizerPipeline()
    async with Client(params, mode="legacy", read_timeout_seconds=30) as client:
        for case, tool, args in cases:
            response = await client.call_tool(tool, args)
            result = response.structured_content
            if not isinstance(result, dict):
                raise ValueError("MISSING_STRUCTURED_CONTENT")
            if (
                len(response.content) != 1
                or getattr(response.content[0], "type", None) != "text"
                or json.loads(response.content[0].text) != result
            ):
                raise ValueError("RESPONSE_COPIES_DIFFER")
            if not _valid_envelope(definition(tool)["outputSchema"], result):
                raise ValueError("INVALID_SCHEMA")
            ensure_safe_output(result, sanitizer=pipeline)
            frame = serialize_response(
                result, "\0" * 128, sanitizer=pipeline, server_meta=SERVER_INFO_META
            )
            if len(frame) > 16384:
                raise ValueError("FRAME_LIMIT")
            failure_count = len(report["failureCodes"])
            data = result["data"]
            if not isinstance(data, dict):
                raise ValueError("DATA_UNAVAILABLE")
            observation: dict[str, Any] = {}
            if case in {"beans", "route"}:
                observation["count"] = result["totalMatched"]
                expected = 0 if phase == "fault" else 1
                if result["totalMatched"] != expected:
                    report["failureCodes"].append(f"{phase}_{case}_count")
            if case == "beans":
                analysis = data["missingBeanAnalysis"]
                observation["conditionReasons"] = sorted(
                    {item["reasonCode"] for item in analysis["conditions"]}
                )
                if (
                    phase == "fault"
                    and "PROPERTY_VALUE_MISMATCH" not in observation["conditionReasons"]
                ):
                    report["failureCodes"].append("fault_condition_missing")
            if case == "health":
                observation["overallStatus"] = data["overallStatus"]
                if data["overallStatus"] != ("DOWN" if phase == "fault" else "UP"):
                    report["failureCodes"].append(f"{phase}_health_status")
            if case == "drift":
                dimensions = sorted(
                    item["dimension"] for item in data["missingInRuntime"]
                )
                observation["missingDimensions"] = dimensions
                if dimensions != (["beans", "routes"] if phase == "fault" else []):
                    report["failureCodes"].append(f"{phase}_drift_dimensions")
            if case == "migration":
                items = data["items"]
                observation.update(
                    {
                        "version": items[0]["version"] if len(items) == 1 else None,
                        "state": items[0]["state"] if len(items) == 1 else None,
                        "pendingVisibility": data["pendingVisibility"],
                    }
                )
                if observation != {
                    "version": "1",
                    "state": "APPLIED",
                    "pendingVisibility": "unknown",
                }:
                    report["failureCodes"].append(f"{phase}_migration_baseline")
            # Safe, bounded facts only; no remote prose or response bodies.
            report["checks"].append(
                {
                    "phase": phase,
                    "case": case,
                    "status": result["status"],
                    "totalMatched": result["totalMatched"],
                    "coverage": result["coverage"]["state"],
                    "gaps": result["coverage"]["gaps"],
                    "errorCodes": [x["code"] for x in result["errors"]],
                    "httpStatuses": [x["httpStatus"] for x in result["errors"]],
                    "reconstructedFrameBytes": len(frame),
                    "evidenceKind": "real_actuator_mcp",
                    "copiesEqual": True,
                    "passed": len(report["failureCodes"]) == failure_count,
                    "observation": observation,
                }
            )


async def verify_admin(
    port: int, token: str, phase: str, report: dict[str, Any]
) -> None:
    env = dict(clean_env(), PYTHONPATH=str(ROOT / "src"), ADMIN_TOKEN=token)
    params = StdioServerParameters(
        command=sys.executable,
        args=[
            "-m",
            "spring_runtime_mcp.cli",
            "--base-url",
            f"http://127.0.0.1:{port}",
            "--token-env",
            "ADMIN_TOKEN",
        ],
        env=env,
    )
    async with Client(params, mode="legacy", read_timeout_seconds=30) as client:
        response = await client.call_tool("springboot_diagnose_health", {})
        result = response.structured_content
        if (
            not isinstance(result, dict)
            or len(response.content) != 1
            or json.loads(response.content[0].text) != result
        ):
            raise ValueError("ADMIN_RESPONSE_COPIES")
        if not _valid_envelope(
            definition("springboot_diagnose_health")["outputSchema"], result
        ):
            raise ValueError("ADMIN_SCHEMA")
        pipeline = SanitizerPipeline((token,))
        ensure_safe_output(result, sanitizer=pipeline)
        size = len(
            serialize_response(
                result, "\0" * 128, sanitizer=pipeline, server_meta=SERVER_INFO_META
            )
        )
        data = result["data"]
        actual = data.get("overallStatus") if isinstance(data, dict) else None
        passed = size <= 16384 and actual == ("DOWN" if phase == "fault" else "UP")
        report["admin"]["checks"].append(
            {
                "phase": phase,
                "evidenceKind": "real_actuator_mcp_with_injected_health_indicator",
                "overallStatus": actual,
                "status": result["status"],
                "reconstructedFrameBytes": size,
                "copiesEqual": True,
                "passed": passed,
            }
        )
        if not passed:
            report["failureCodes"].append(f"admin_{phase}_health")


def startup_markers(output: bytes) -> dict[str, bool]:
    """Extract fixed local compiler/runtime markers; never retain process output."""
    return {
        "flywayMigrationFailure": b"FlywayMigrateException" in output,
        "flywayVersion2": b"V2__injected_failure.sql" in output,
        "circularDependency": b"BeanCurrentlyInCreationException" in output
        or b"the dependencies of some of the beans in the application context form a cycle"
        in output.lower(),
        "cycleA": b"cycleA" in output,
        "cycleB": b"cycleB" in output,
    }


def verify_java_warning(work: Path, report: dict[str, Any]) -> None:
    source = work / "WarningProbe.java"
    source.write_text("import java.util.List; class WarningProbe { List value; }\n")
    result = subprocess.run(
        [
            "javac",
            "-J-Xmx256m",
            "-proc:none",
            "-Xlint:rawtypes",
            "-XDrawDiagnostics",
            "-d",
            str(work),
            str(source),
        ],
        env=clean_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )
    passed = result.returncode == 0 and b"compiler.warn.raw.class.use" in result.stderr
    report["javaWarning"] = {
        "evidenceKind": "javac_synthetic_source",
        "compileSucceeded": result.returncode == 0,
        "rawTypeWarningObserved": passed,
        "passed": passed,
    }
    if not passed:
        report["failureCodes"].append("java_warning_missing")


async def verify_unavailable(port: int, case: str) -> dict[str, Any]:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "spring_runtime_mcp.cli", "--base-url", f"http://127.0.0.1:{port}"],
        env=dict(
            clean_env(), PYTHONPATH=str(ROOT / "src"), PYTHONDONTWRITEBYTECODE="1"
        ),
    )
    async with Client(params, mode="legacy", read_timeout_seconds=30) as client:
        response = await client.call_tool(
            "springboot_check_migrations", {"engine": "flyway"}
        )
        result = response.structured_content
        if (
            not isinstance(result, dict)
            or len(response.content) != 1
            or json.loads(response.content[0].text) != result
        ):
            raise ValueError("UNAVAILABLE_RESPONSE_COPIES")
        if not _valid_envelope(
            definition("springboot_check_migrations")["outputSchema"], result
        ):
            raise ValueError("UNAVAILABLE_SCHEMA")
        pipeline = SanitizerPipeline()
        ensure_safe_output(result, sanitizer=pipeline)
        size = len(
            serialize_response(
                result, "\0" * 128, sanitizer=pipeline, server_meta=SERVER_INFO_META
            )
        )
        codes = [item["code"] for item in result["errors"]]
        passed = (
            result["status"] == "unavailable"
            and result["coverage"]["state"] == "unavailable"
            and result["data"] is None
            and "TARGET_CONNECTION_REFUSED" in codes
            and size <= 16384
        )
        return {
            "case": case,
            "evidenceKind": "real_mcp_after_target_exit",
            "status": result["status"],
            "coverage": result["coverage"]["state"],
            "errorCodes": codes,
            "attribution": "unknown",
            "copiesEqual": True,
            "reconstructedFrameBytes": size,
            "passed": passed,
        }


def run_startup_failures(
    jar: Path, report: dict[str, Any], source_catalog: Path
) -> None:
    report["startupFailures"] = []
    for case, flags, required in (
        (
            "flyway",
            [
                "--spring.flyway.locations=classpath:db/migration,classpath:fault-migration"
            ],
            ("flywayMigrationFailure", "flywayVersion2"),
        ),
        (
            "constructorCycle",
            ["--spring.profiles.active=local-mcp,cycle"],
            ("circularDependency", "cycleA", "cycleB"),
        ),
    ):
        port, app_port = free_port(), free_port()
        command = [
            "java",
            "-Xmx384m",
            "-jar",
            str(jar),
            f"--server.port={app_port}",
            "--server.address=127.0.0.1",
            f"--management.server.port={port}",
        ]
        process = subprocess.Popen(
            command + flags,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=clean_env(),
        )
        try:
            output, _ = process.communicate(timeout=90)
            markers = startup_markers(output)
            del output
            passed = process.returncode != 0 and all(markers[key] for key in required)
            entry: dict[str, Any] = {
                "case": case,
                "evidenceKind": "local_target_startup_markers",
                "compile": "passed",
                "exitNonzero": process.returncode != 0,
                "markers": {key: markers[key] for key in required},
                "passed": passed,
            }
            report["startupFailures"].append(entry)
            if not passed:
                report["failureCodes"].append(f"{case}_startup_evidence")
            with socket.socket() as reservation:
                reservation.bind(("127.0.0.1", port))
                entry["mcp"] = asyncio.run(verify_unavailable(port, case))
            if not entry["mcp"]["passed"]:
                report["failureCodes"].append(f"{case}_unavailable")
        finally:
            stop(process)
        recovery_port, recovery_app_port = free_port(), free_port()
        recovery = subprocess.Popen(
            [
                "java",
                "-Xmx384m",
                "-jar",
                str(jar),
                f"--server.port={recovery_app_port}",
                "--server.address=127.0.0.1",
                f"--management.server.port={recovery_port}",
                "--stripe.enabled=true",
                "--fault.route.enabled=true",
                "--fault.health.down=false",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=clean_env(),
        )
        try:
            status = wait_ready(recovery, recovery_port)
            before = len(report["failureCodes"])
            first_check = len(report["checks"])
            asyncio.run(verify(recovery_port, "recovery", report, source_catalog))
            for check in report["checks"][first_check:]:
                check["recoveryFor"] = case
            entry["recovery"] = {
                "httpStatus": status,
                "passed": status == 200 and len(report["failureCodes"]) == before,
            }
            if not entry["recovery"]["passed"]:
                report["failureCodes"].append(f"{case}_recovery")
        finally:
            stop(recovery)


def run_admin(temp: str, project: Path, report: dict[str, Any]) -> None:
    module = project / "spring-boot-admin-samples/spring-boot-admin-sample-reactive"
    fixture = ROOT / "examples/large-project-matrix"
    work = Path(temp) / "admin-overlay"
    work.mkdir()
    report["admin"] = {
        "checks": [],
        "source": "cached spring-boot-admin 4.1.3 sample; isolated operator overlay",
        "cleanup": "pending",
    }
    config = json.loads((fixture / "projects.json").read_text())["spring-boot-admin"]
    revision = subprocess.check_output(
        ["git", "-C", str(project), "rev-parse", "HEAD"],
        text=True,
        env=clean_env(),
        stderr=subprocess.DEVNULL,
    ).strip()
    report["admin"]["revision"] = revision
    if revision != config["revision"]:
        raise ValueError("ADMIN_REVISION_MISMATCH")
    entries = (module / "classpath-runtime.txt").read_text().strip().split(os.pathsep)
    boot_jars = [
        Path(entry).name
        for entry in entries
        if Path(entry).name.startswith("spring-boot-")
        and Path(entry).name.removeprefix("spring-boot-")[0].isdigit()
    ]
    if len(boot_jars) != 1 or not all(Path(entry).is_file() for entry in entries):
        raise ValueError("ADMIN_CLASSPATH_INCOMPLETE")
    report["admin"]["actualSpringBootJar"] = boot_jars[0]
    classpath = os.pathsep.join([str(module / "target/classes"), *entries])
    (work / "DiagnosticSecurity.java").write_text(
        (fixture / "ReactiveSecurity.java.template").read_text()
    )
    launcher = (
        (fixture / "LargeProjectLauncher.java")
        .read_text()
        .replace(
            'Class.forName("DiagnosticSecurity")',
            'Class.forName("DiagnosticSecurity"), Class.forName("InjectedAdmin")',
        )
    )
    (work / "LargeProjectLauncher.java").write_text(launcher)
    (
        work / "InjectedAdmin.java"
    ).write_text("""import org.springframework.context.annotation.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.health.contributor.*;
@Configuration public class InjectedAdmin {
 @Bean HealthIndicator injectedHealth(@Value("${fault.health.down:false}") boolean down) {
  return () -> down ? Health.down().build() : Health.up().build();
 }
}
""")
    subprocess.run(
        [
            "javac",
            "-J-Xmx512m",
            "-proc:none",
            "-cp",
            classpath,
            "-d",
            str(work),
            *[
                str(work / name)
                for name in (
                    "DiagnosticSecurity.java",
                    "LargeProjectLauncher.java",
                    "InjectedAdmin.java",
                )
            ],
        ],
        check=True,
        timeout=90,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=clean_env(),
    )
    report["admin"]["overlayCompile"] = "passed"
    token = secrets.token_urlsafe(32)
    env = dict(clean_env(), LARGE_DIAGNOSTICS_ADMIN=token)
    for phase in ("fault", "recovery"):
        port, app_port = free_port(), free_port()
        properties = (
            (fixture / "common.properties").read_text()
            + "\n"
            + (fixture / "spring-boot-admin.properties").read_text()
        )
        properties += f"\nserver.port={app_port}\nmanagement.server.port={port}\nmanagement.server.address=127.0.0.1\nfault.health.down={'true' if phase == 'fault' else 'false'}\n"
        (work / "application.properties").write_text(properties)
        process = subprocess.Popen(
            [
                "java",
                "-Xmx384m",
                "-Dspring.devtools.restart.enabled=false",
                "-cp",
                str(work) + os.pathsep + classpath,
                "LargeProjectLauncher",
                "de.codecentric.boot.admin.sample.SpringBootAdminReactiveApplication",
                str(work / "application.properties"),
                str(ROOT / "examples/project-matrix/logback-diagnostics.xml"),
            ],
            cwd=work,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            http = wait_ready(process, port, token)
            report["admin"].setdefault("httpStatuses", {})[phase] = http
            if http != (503 if phase == "fault" else 200):
                report["failureCodes"].append(f"admin_{phase}_http")
            asyncio.run(verify_admin(port, token, phase, report))
        finally:
            stop(process)
    report["admin"]["cleanup"] = "owned target processes terminated"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument(
        "--source-catalog",
        type=Path,
        default=ROOT / "examples/spring-boot-demo/source-catalog.json",
    )
    parser.add_argument(
        "--admin-project",
        type=Path,
        default=Path.home()
        / ".cache/spring-runtime-mcp/large-matrix-20261022/spring-boot-admin",
    )
    args = parser.parse_args()
    report: dict[str, Any] = {
        "verifiedAt": datetime.now(UTC).isoformat(),
        "project": "spring-boot-demo",
        "checks": [],
        "failureCodes": ["RUN_INCOMPLETE"],
        "provenance": {
            "target": "real Spring Boot demo and Actuator in a disposable copy",
            "injection": "conditional route and synthetic health indicator added to copy; stripe property toggled",
            "migration": "invalid V2 migration is injected for startup failure; existing V1 is the recovery baseline",
        },
    }
    try:
        with tempfile.TemporaryDirectory(prefix="mcp-injected-") as temp:
            work = Path(temp) / "demo"
            shutil.copytree(
                ROOT / "examples/spring-boot-demo",
                work,
                ignore=shutil.ignore_patterns("target", "transcript.jsonl"),
            )
            controller = work / "src/main/java/example/OrderController.java"
            text = controller.read_text().replace(
                "@RestController",
                '@org.springframework.boot.autoconfigure.condition.ConditionalOnProperty(name="fault.route.enabled", havingValue="true", matchIfMissing=true)\n@RestController',
            )
            controller.write_text(text)
            fault_migration = (
                work / "src/main/resources/fault-migration/V2__injected_failure.sql"
            )
            fault_migration.parent.mkdir(parents=True)
            fault_migration.write_text("THIS IS NOT VALID SQL;\n")
            for name, dependency in (("CycleA", "CycleB"), ("CycleB", "CycleA")):
                (work / f"src/main/java/example/{name}.java").write_text(
                    "package example;\n"
                    "@org.springframework.stereotype.Component\n"
                    '@org.springframework.context.annotation.Profile("cycle")\n'
                    f"public class {name} {{ public {name}({dependency} dependency) {{}} }}\n"
                )
            (
                work / "src/main/java/example/InjectedHealth.java"
            ).write_text("""package example;
import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.HealthIndicator;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
@Component
public class InjectedHealth implements HealthIndicator {
  @Value("${fault.health.down:false}") boolean down;
  public Health health() { return down ? Health.down().build() : Health.up().build(); }
}
""")
            env = dict(clean_env(), MAVEN_OPTS="-Xmx512m")
            subprocess.run(
                ["mvn", "-o", "-q", "package", "-DskipTests"],
                cwd=work,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=180,
                check=True,
            )
            report["build"] = "passed"
            jar = work / "target/spring-runtime-mcp-demo-0.1.0.jar"
            verify_java_warning(work, report)
            run_startup_failures(jar, report, args.source_catalog.resolve())
            for phase in ("fault", "recovery"):
                port, app_port = free_port(), free_port()
                flags = (
                    [
                        "--stripe.enabled=false",
                        "--fault.route.enabled=false",
                        "--fault.health.down=true",
                    ]
                    if phase == "fault"
                    else [
                        "--stripe.enabled=true",
                        "--fault.route.enabled=true",
                        "--fault.health.down=false",
                    ]
                )
                process = subprocess.Popen(
                    [
                        "java",
                        "-Xmx384m",
                        "-jar",
                        str(jar),
                        f"--server.port={app_port}",
                        "--server.address=127.0.0.1",
                        f"--management.server.port={port}",
                        *flags,
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    env=clean_env(),
                )
                try:
                    http_status = wait_ready(process, port)
                    report.setdefault("actuatorHealthHttpStatus", {})[phase] = (
                        http_status
                    )
                    if http_status != (503 if phase == "fault" else 200):
                        report["failureCodes"].append(f"{phase}_health_http")
                    asyncio.run(
                        verify(port, phase, report, args.source_catalog.resolve())
                    )
                finally:
                    stop(process)
            run_admin(temp, args.admin_project.resolve(), report)
            report["failureCodes"].remove("RUN_INCOMPLETE")
    except (
        OSError,
        subprocess.SubprocessError,
        RuntimeError,
        ValueError,
        AssertionError,
    ) as error:
        report["failureCodes"].append(type(error).__name__)
    finally:
        if "admin" in report and report["admin"]["cleanup"] == "pending":
            report["admin"]["cleanup"] = (
                "owned target processes terminated or not started"
            )
        report["passed"] = not report["failureCodes"]
        report["cleanup"] = (
            "owned target processes terminated and temporary copy removed"
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
    return int(bool(report["failureCodes"]))


if __name__ == "__main__":
    raise SystemExit(main())
