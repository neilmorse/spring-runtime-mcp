"""Opt-in acceptance for a disposable XXL-JOB v3.4.0 admin checkout.

XXL-JOB is a small production-used distributed scheduler. The admin runs with
a disposable MariaDB database on loopback. A temporary operator launcher adds a
bounded startup buffer; a plain Servlet filter protects Actuator while the
native SSO interceptor keeps protecting the business UI.
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

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples/xxl-job-matrix"
LAUNCHER = ROOT / "examples/large-project-matrix/LargeProjectLauncher.java"
JAVA21 = Path("/usr/lib/jvm/java-21-openjdk/bin/java")
JAVAC21 = JAVA21.with_name("javac")
DB_IMAGE = "mariadb:11.2"
DB_INIT = "doc/db/tables_xxl_job.sql"


class XxlJobAcceptance(Acceptance):
    def __init__(self, args: argparse.Namespace) -> None:
        super().__init__(args, fixture=FIXTURE)
        self.work = self.project / ".xxl-diagnostics"
        self.work.mkdir(exist_ok=True)
        self.report["database"] = "disposable-mariadb-11.2"
        self.report["startupBufferEvents"] = 2048
        self.db_container = "xxl-job-db-" + secrets.token_hex(6)
        self.db_port = free_port()
        self.db_password = secrets.token_urlsafe(24)
        self.db_admin_password = secrets.token_urlsafe(24)

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
        module_classes = [
            str(path)
            for path in sorted(self.project.glob("xxl-job-*/target/classes"))
            if path.is_dir()
        ]
        admin_classes = str(module / "target/classes")
        if admin_classes in module_classes:
            module_classes.remove(admin_classes)
        self.classpath = os.pathsep.join([admin_classes, *module_classes, *runtime])
        artifacts = [Path(entry).name for entry in runtime]
        self.report["runtimeArtifacts"] = artifacts
        self.report["runtimeArtifactsSha256"] = hashlib.sha256(
            "\n".join(sorted(artifacts)).encode()
        ).hexdigest()
        self.report["classpathEntryCount"] = len(module_classes) + len(runtime) + 1
        compiled = subprocess.run(
            [
                str(JAVAC21),
                "-cp",
                self.classpath,
                "-d",
                str(self.work),
                str(self.fixture / "DiagnosticSecurity.java"),
                str(LAUNCHER),
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
        properties += "\n" + (self.fixture / "xxl-job.properties").read_text()
        properties += (
            f"\nserver.port={self.port}\n"
            f"management.server.port={self.management_port}\n"
        )
        (self.work / "application.properties").unlink(missing_ok=True)
        (self.work / "logback.xml").write_text(
            (ROOT / "examples/project-matrix/logback-diagnostics.xml").read_text()
        )
        (self.work / "niche.properties").write_text(properties)

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
                f"MARIADB_ROOT_PASSWORD={self.db_admin_password}",
                "-e",
                "MARIADB_DATABASE=xxl_job",
                "-e",
                "MARIADB_USER=xxl",
                "-e",
                f"MARIADB_PASSWORD={self.db_password}",
                "-p",
                f"127.0.0.1:{self.db_port}:3306",
                "-v",
                f"{init}:/docker-entrypoint-initdb.d/01-xxl.sql:ro",
                "--health-cmd",
                "healthcheck.sh --su-mysql --connect --innodb_initialized",
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
        return probe.returncode != 0

    def start(self) -> None:
        env = environment()
        env["JAVA_HOME"] = str(JAVA21.parent.parent)
        env.update(
            NICHE_DIAGNOSTICS_ADMIN=self.admin,
            NICHE_DIAGNOSTICS_USER=self.user,
            SPRING_DATASOURCE_URL=(
                f"jdbc:mysql://127.0.0.1:{self.db_port}/xxl_job"
                "?useUnicode=true&characterEncoding=UTF-8"
                "&autoReconnect=true&serverTimezone=UTC"
                "&useSSL=false&allowPublicKeyRetrieval=true"
            ),
            SPRING_DATASOURCE_USERNAME="xxl",
            SPRING_DATASOURCE_PASSWORD=self.db_password,
        )
        self.process = subprocess.Popen(
            [
                str(JAVA21),
                "-Xmx1280m",
                "-Djava.awt.headless=true",
                "-Dspring.devtools.restart.enabled=false",
                "-cp",
                str(self.work) + os.pathsep + self.classpath,
                "LargeProjectLauncher",
                self.config["mainClass"],
                str(self.work / "niche.properties"),
                str(ROOT / "examples/project-matrix/logback-diagnostics.xml"),
            ],
            cwd=self.project,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        started = time.monotonic()
        port, java = ready(self.process, self.report, timeout=240)
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
            except Exception as exc:
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
    parser.add_argument("--name", default="xxl-job", choices=("xxl-job",))
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--soak-seconds", type=int, default=300)
    args = parser.parse_args()
    if not 65 <= args.soak_seconds <= 600:
        parser.error("--soak-seconds must be between 65 and 600")
    return XxlJobAcceptance(args).run()


if __name__ == "__main__":
    raise SystemExit(main())
