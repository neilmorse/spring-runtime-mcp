"""Opt-in acceptance for a disposable ultra-large Fineract checkout.

The target is Apache Fineract 1.9.0 at a fixed revision. Only the provider
classes are built from source; a temporary external launcher adds a startup
buffer and a management-only Bearer filter. PostgreSQL runs in a disposable
container bound to loopback. No production instance or business write is used.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from mcp import Client

from check_large_project_runtime import Acceptance, environment, free_port
from check_project_runtime import ready
from spring_runtime_mcp.policy.sanitization import SanitizerPipeline

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples/ultra-project-matrix"
JAVA17 = Path("/usr/lib/jvm/java-17-openjdk/bin/java")
JAVAC17 = JAVA17.with_name("javac")
DB_IMAGE = "postgres:16-alpine"
DB_INIT = "config/docker/postgresql/docker-entrypoint-initdb.d/01-init.sh"
JAVA_OPENS = (
    "--add-exports=java.naming/com.sun.jndi.ldap=ALL-UNNAMED",
    "--add-opens=java.base/java.lang=ALL-UNNAMED",
    "--add-opens=java.base/java.lang.invoke=ALL-UNNAMED",
    "--add-opens=java.base/java.io=ALL-UNNAMED",
    "--add-opens=java.base/java.security=ALL-UNNAMED",
    "--add-opens=java.base/java.util=ALL-UNNAMED",
    "--add-opens=java.management/javax.management=ALL-UNNAMED",
    "--add-opens=java.naming/javax.naming=ALL-UNNAMED",
)


class UltraAcceptance(Acceptance):
    def __init__(self, args: argparse.Namespace) -> None:
        super().__init__(args, fixture=FIXTURE)
        self.work = self.project / ".ultra-diagnostics"
        self.work.mkdir(exist_ok=True)
        self.report["database"] = "disposable-postgresql-16-alpine"
        self.report["buildSystem"] = "gradle-8.5"
        self.report["startupBufferEvents"] = 2048
        self.db_container = "ultra-fineract-db-" + secrets.token_hex(6)
        self.db_port = free_port()
        self.db_password = secrets.token_urlsafe(24)
        self.db_admin_password = secrets.token_urlsafe(24)
        self.pipeline = SanitizerPipeline(
            (self.admin, self.user, self.db_password, self.db_admin_password)
        )
        self.db_started = False

    def prepare(self) -> None:
        revision = subprocess.check_output(
            ["git", "-C", str(self.project), "rev-parse", "HEAD"], text=True
        ).strip()
        if revision != self.config["revision"]:
            raise ValueError("UNEXPECTED_REVISION")
        module = self.project / self.config["module"]
        classpath_file = module / "classpath-runtime.txt"
        if not classpath_file.exists():
            raise ValueError("RUNTIME_CLASSPATH_MISSING")
        runtime = [
            entry
            for entry in classpath_file.read_text().strip().split(os.pathsep)
            if entry
        ]
        self.classpath = os.pathsep.join(
            [
                str(module / "build/classes/java/main"),
                str(module / "build/resources/main"),
                *runtime,
            ]
        )
        artifacts = [Path(entry).name for entry in runtime]
        self.report["runtimeArtifacts"] = artifacts
        self.report["runtimeArtifactsSha256"] = hashlib.sha256(
            "\n".join(sorted(artifacts)).encode()
        ).hexdigest()
        self.report["classpathEntryCount"] = len(runtime) + 2
        template = (
            ROOT / "examples/large-project-matrix/ServletSecurity.java.template"
        ).read_text()
        source = template.replace("SERVLET_PACKAGE", "jakarta").replace(
            "MATCHER_METHOD", "securityMatcher"
        )
        (self.work / "DiagnosticSecurity.java").write_text(source)
        compiled = subprocess.run(
            [
                str(JAVAC17),
                "-cp",
                self.classpath,
                "-d",
                str(self.work),
                str(self.work / "DiagnosticSecurity.java"),
                str(self.fixture / "FineractDiagnosticsLauncher.java"),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.report["operatorLauncherCompileExit"] = compiled.returncode
        if compiled.returncode:
            print(compiled.stderr.decode(errors="replace")[:5000], file=sys.stderr)
            raise ValueError("OPERATOR_LAUNCHER_COMPILE_FAILED")
        properties = (self.fixture / "common.properties").read_text()
        properties += "\n" + (self.fixture / "fineract.properties").read_text()
        properties += (
            f"\nserver.port={self.port}\n"
            f"management.server.port={self.management_port}\n"
        )
        # Keep the external file out of the classpath name application.properties:
        # Fineract's native defaults live under build/classes/java/main and must
        # remain visible to Spring Boot config data loading.
        (self.work / "application.properties").unlink(missing_ok=True)
        (self.work / "ultra.properties").write_text(properties)

    def start_database(self) -> None:
        init = self.project / DB_INIT
        if not init.exists():
            raise ValueError("DATABASE_INIT_SCRIPT_MISSING")
        result = subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                self.db_container,
                "-e",
                "POSTGRES_USER=root",
                "-e",
                f"POSTGRES_PASSWORD={self.db_admin_password}",
                "-e",
                "POSTGRES_DB=postgres",
                "-e",
                "FINERACT_DB_USER=fineract",
                "-e",
                f"FINERACT_DB_PASS={self.db_password}",
                "-e",
                "FINERACT_TENANTS_DB_NAME=fineract_tenants",
                "-e",
                "FINERACT_TENANT_DEFAULT_DB_NAME=fineract_default",
                "-p",
                f"127.0.0.1:{self.db_port}:5432",
                "-v",
                f"{init}:/docker-entrypoint-initdb.d/01-init.sh:ro",
                "--health-cmd",
                "pg_isready -U root -d postgres",
                "--health-interval",
                "2s",
                "--health-timeout",
                "2s",
                "--health-retries",
                "60",
                DB_IMAGE,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode:
            raise RuntimeError("DATABASE_CONTAINER_START_FAILED")
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            probe = subprocess.run(
                [
                    "docker",
                    "inspect",
                    "--format",
                    "{{.State.Health.Status}}",
                    self.db_container,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if probe.stdout.strip() == "healthy":
                self.db_started = True
                return
            time.sleep(1)
        self.stop_database()
        raise RuntimeError("DATABASE_NOT_HEALTHY")

    def stop_database(self) -> bool:
        subprocess.run(
            ["docker", "rm", "-f", self.db_container],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        probe = subprocess.run(
            ["docker", "inspect", self.db_container],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        self.db_started = False
        return probe.returncode != 0

    def start(self) -> None:
        env = environment()
        env["JAVA_HOME"] = str(JAVA17.parent.parent)
        env.update(
            LARGE_DIAGNOSTICS_ADMIN=self.admin,
            LARGE_DIAGNOSTICS_USER=self.user,
            FINERACT_HIKARI_JDBC_URL=(
                f"jdbc:postgresql://127.0.0.1:{self.db_port}/fineract_tenants"
            ),
            FINERACT_HIKARI_DRIVER_SOURCE_CLASS_NAME="org.postgresql.Driver",
            FINERACT_HIKARI_USERNAME="fineract",
            FINERACT_HIKARI_PASSWORD=self.db_password,
            FINERACT_HIKARI_CONNECTION_TIMEOUT="3000",
            FINERACT_HIKARI_MAXIMUM_POOL_SIZE="5",
            FINERACT_HIKARI_MINIMUM_IDLE="1",
            FINERACT_DEFAULT_TENANTDB_HOSTNAME="127.0.0.1",
            FINERACT_DEFAULT_TENANTDB_PORT=str(self.db_port),
            FINERACT_DEFAULT_TENANTDB_UID="fineract",
            FINERACT_DEFAULT_TENANTDB_PWD=self.db_password,
            FINERACT_DEFAULT_TENANTDB_NAME="fineract_default",
            FINERACT_DEFAULT_TENANTDB_IDENTIFIER="default",
            FINERACT_DEFAULT_TENANTDB_DESCRIPTION="Disposable ultra diagnostics tenant",
            FINERACT_DEFAULT_TENANTDB_TIMEZONE="UTC",
            FINERACT_DEFAULT_TENANTDB_MASTER_PASSWORD="fineract-ultra-master",
            FINERACT_LIQUIBASE_ENABLED="true",
            FINERACT_MODE_BATCH_MANAGER_ENABLED="false",
            FINERACT_MODE_BATCH_WORKER_ENABLED="false",
            FINERACT_REMOTE_JOB_MESSAGE_HANDLER_SPRING_EVENTS_ENABLED="false",
            FINERACT_REMOTE_JOB_MESSAGE_HANDLER_JMS_ENABLED="false",
            FINERACT_REMOTE_JOB_MESSAGE_HANDLER_KAFKA_ENABLED="false",
            FINERACT_EXTERNAL_EVENTS_ENABLED="false",
            FINERACT_AWS_CREDENTIALS_INSTANCE_PROFILE="false",
            FINERACT_MANAGEMENT_PROMETHEUS_ENABLED="false",
            FINERACT_MANAGEMENT_OLTP_ENABLED="false",
            FINERACT_MANAGEMENT_CLOUDWATCH_ENABLED="false",
            FINERACT_MANAGEMENT_TRACIING_ENABLED="false",
        )
        self.process = subprocess.Popen(
            [
                str(JAVA17),
                "-Xmx1536m",
                "-Djava.awt.headless=true",
                "-Dspring.devtools.restart.enabled=false",
                *JAVA_OPENS,
                "-cp",
                str(self.work) + os.pathsep + self.classpath,
                "FineractDiagnosticsLauncher",
                self.config["mainClass"],
                str(self.work / "ultra.properties"),
                str(ROOT / "examples/project-matrix/logback-diagnostics.xml"),
            ],
            cwd=self.project,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        started = time.monotonic()
        port, java = ready(self.process, self.report, timeout=300)
        self.expect(port == self.management_port, "MANAGEMENT_PORT_MISMATCH")
        self.report["javaMajor"] = java
        self.report.setdefault("startupSeconds", []).append(
            round(time.monotonic() - started, 3)
        )

    async def verify(self) -> None:
        await super().verify()
        if self.process is None or self.process.poll() is not None:
            self.expect(False, "TARGET_NOT_RUNNING_FOR_DATABASE_CHECK")
            return
        async with Client(
            self.parameters("business-route", self.admin),
            mode="legacy",
            read_timeout_seconds=30,
        ) as client:
            self.pid("business-route")
            try:
                result = await self.call(
                    client,
                    "verify_mappings",
                    {
                        "pathPattern": self.config["businessRoute"],
                        "httpMethod": "GET",
                    },
                    "jaxrs-business-route",
                )
                self.report["jaxRsBusinessRoute"] = {
                    "observed": bool(
                        result.get("data") and result["data"].get("items")
                    ),
                    "status": result["status"],
                    "coverage": result["coverage"]["state"],
                    "gaps": result["coverage"]["gaps"],
                    "errorCodes": [row["code"] for row in result["errors"]],
                }
                self.expect(
                    result["status"] == "partial"
                    and "NON_DISPATCHER_SERVLET_ROUTES_UNOBSERVED"
                    in result["coverage"]["gaps"],
                    "JAXRS_ROUTE_FALSE_CERTAINTY",
                )
            except Exception as exc:
                self.report["jaxRsBusinessRoute"] = {
                    "observed": False,
                    "exceptionType": type(exc).__name__,
                }
        async with Client(
            self.parameters("database-availability", self.admin),
            mode="legacy",
            read_timeout_seconds=30,
        ) as client:
            self.pid("database-availability")
            await self.database_availability(client)

    async def database_availability(self, client: Client) -> None:
        health_args: dict[str, Any] = {
            "includeDetails": True,
            "includeHealthy": True,
        }
        before = await self.call(
            client, "diagnose_health", health_args, "db-health-before-pause"
        )
        before_state = (before.get("data") or {}).get("overallStatus")
        self.expect(before_state == "UP", "DB_HEALTH_NOT_UP_BEFORE_PAUSE")
        paused: dict[str, Any] = {}
        paused_state = None
        try:
            subprocess.run(
                ["docker", "pause", self.db_container],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            await asyncio.sleep(3)
            try:
                paused = await self.call(
                    client, "diagnose_health", health_args, "db-health-paused"
                )
                paused_state = (paused.get("data") or {}).get("overallStatus")
            except Exception as exc:  # tool timeout is a valid degraded observation
                self.report["databasePauseToolException"] = type(exc).__name__
            degraded = paused.get("status") == "unavailable" or (
                paused.get("status") in {"ok", "partial"} and paused_state != "UP"
            )
            self.expect(degraded, "DB_PAUSE_NOT_OBSERVED")
            beans = await self.call(
                client,
                "inspect_beans",
                {"beanNamePattern": self.config["bean"]},
                "beans-during-db-pause",
            )
            self.expect(
                bool(beans.get("data")) and bool(beans["data"].get("items")),
                "BEANS_UNAVAILABLE_DURING_DB_PAUSE",
            )
        finally:
            subprocess.run(
                ["docker", "unpause", self.db_container],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        recovered_state = None
        attempts = 0
        for attempts in range(1, 13):
            await asyncio.sleep(2)
            recovered = await self.call(
                client, "diagnose_health", health_args, "db-health-recovered"
            )
            recovered_state = (recovered.get("data") or {}).get("overallStatus")
            if recovered_state == "UP":
                break
        self.expect(recovered_state == "UP", "DB_HEALTH_DID_NOT_RECOVER")
        self.report["databasePause"] = {
            "before": before_state,
            "pausedStatus": paused.get("status"),
            "pausedOverall": paused_state,
            "recovered": recovered_state,
            "recoveryAttempts": attempts,
        }

    def run(self) -> int:
        try:
            self.start_database()
        except Exception as exc:
            self.report["failureCodes"].append("DATABASE_START_FAILED")
            self.report["harnessExceptionType"] = type(exc).__name__
            self.report["databaseContainerStopped"] = self.stop_database()
            self.report["accepted"] = False
            self.args.output.parent.mkdir(parents=True, exist_ok=True)
            self.args.output.write_text(
                json.dumps(self.report, ensure_ascii=False, indent=2) + "\n"
            )
            return 1
        try:
            super().run()
        finally:
            stopped = self.stop_database()
        self.report["databaseContainerStopped"] = stopped
        self.report["databaseImage"] = DB_IMAGE
        self.report["databasePortLoopbackOnly"] = True
        if not stopped:
            self.report["failureCodes"].append("DATABASE_CONTAINER_LEAK")
        self.report["accepted"] = not self.report["failureCodes"]
        self.args.output.parent.mkdir(parents=True, exist_ok=True)
        self.args.output.write_text(
            json.dumps(self.report, ensure_ascii=False, indent=2) + "\n"
        )
        return 0 if self.report["accepted"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default="fineract", choices=("fineract",))
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--soak-seconds", type=int, default=300)
    args = parser.parse_args()
    if not 65 <= args.soak_seconds <= 600:
        parser.error("--soak-seconds must be between 65 and 600")
    return UltraAcceptance(args).run()


if __name__ == "__main__":
    raise SystemExit(main())
