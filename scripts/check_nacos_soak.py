"""Opt-in four-hour Nacos production soak; never part of the offline test suite.

Only a fixed Nacos checkout and an operator-built distribution run. The target
is bound to loopback, uses a disposable MariaDB container, and receives only
GET requests. Persist sanitized aggregates and per-minute resource samples.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import http.client
import json
import os
import secrets
import shutil
import statistics
import subprocess
import sys
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from check_large_project_runtime import Acceptance, free_port, memory, stop
from check_project_runtime import environment, ready
from mcp import Client

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples/nacos-soak-matrix"
JAVA21 = Path("/usr/lib/jvm/java-21-openjdk/bin/java")
JAVAC21 = JAVA21.with_name("javac")
DB_IMAGE = "mariadb:11.2"
EXPECTED_ERROR_CODES = {
    "AUTHORIZATION_DENIED",
    "CAPABILITY_DISABLED",
    "CURSOR_EXPIRED",
    "CURSOR_QUERY_MISMATCH",
    "ENDPOINT_NOT_EXPOSED",
    "ENDPOINT_UNAUTHORIZED",
    "FORBIDDEN",
    "INVALID_ARGUMENT",
    "TARGET_CONNECTION_REFUSED",
    "TARGET_TIMEOUT",
    "UNAUTHORIZED",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def process_metrics(pid: int, previous: dict[str, Any] | None = None) -> dict[str, Any]:
    base = memory(pid)
    if not base:
        return {}
    try:
        status = Path(f"/proc/{pid}/status").read_text()
        threads = next(
            int(line.split()[1])
            for line in status.splitlines()
            if line.startswith("Threads:")
        )
        stat_fields = Path(f"/proc/{pid}/stat").read_text().split()
        ticks = int(stat_fields[13]) + int(stat_fields[14])
    except (OSError, StopIteration, ValueError, IndexError):
        return base
    result = {**base, "threads": threads, "cpuTicks": ticks}
    if previous and previous.get("cpuTicks") is not None:
        elapsed = time.monotonic() - float(previous["monotonic"])
        clock = os.sysconf("SC_CLK_TCK")
        if elapsed > 0:
            result["cpuPercent"] = round(
                100 * (ticks - previous["cpuTicks"]) / (clock * elapsed), 3
            )
    result["monotonic"] = time.monotonic()
    return result


def direct_get(
    port: int, path: str, *, timeout: float = 3, bearer: str | None = None
) -> dict[str, Any]:
    started = time.monotonic()
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    headers = {"Accept": "application/json, text/plain"}
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    try:
        connection.request("GET", path, headers=headers)
        response = connection.getresponse()
        body = response.read(4096)
        result: dict[str, Any] = {
            "httpStatus": response.status,
            "elapsedMs": round((time.monotonic() - started) * 1000, 3),
        }
        if path.startswith("/actuator/health"):
            try:
                result["overallStatus"] = json.loads(body).get("status")
            except (ValueError, AttributeError):
                result["overallStatus"] = None
        return result
    except (OSError, http.client.HTTPException) as exc:
        return {
            "httpStatus": None,
            "elapsedMs": round((time.monotonic() - started) * 1000, 3),
            "exceptionType": type(exc).__name__,
        }
    finally:
        connection.close()


class NacosSoakAcceptance(Acceptance):
    def __init__(self, args: argparse.Namespace) -> None:
        super().__init__(args, fixture=FIXTURE)
        self.work = self.project / ".nacos-diagnostics"
        self.work.mkdir(exist_ok=True)
        self.report["database"] = "disposable-mariadb-11.2"
        self.report["databaseSummary"] = "external persistence, loopback only"
        self.report["selection"] = {
            "method": "shuf -n 1 over a curated popular production Spring Boot pool",
            "candidates": self.config["randomPool"],
            "selected": "alibaba/nacos",
        }
        self.db_container = "nacos-soak-db-" + secrets.token_hex(6)
        self.db_port = free_port()
        self.db_password = secrets.token_urlsafe(24)
        self.pid_labels: dict[str, int] = {}
        self.active_calls = 0
        self.phase_name = "startup"
        self.pause = asyncio.Event()
        self.samples: list[dict[str, Any]] = []
        self.phase_events: list[dict[str, Any]] = []
        self.inventory_checks: list[dict[str, Any]] = []
        self.boundary_results: list[dict[str, Any]] = []
        self.target_restarts: list[dict[str, Any]] = []
        self.database_pauses: list[dict[str, Any]] = []
        self.phase_errors: list[dict[str, Any]] = []
        self.expected_codes = set(EXPECTED_ERROR_CODES)
        self.progress_path = args.progress or args.output.with_suffix(".jsonl")
        self.progress_path.parent.mkdir(parents=True, exist_ok=True)
        self.phase_schedule = (
            [
                (10, "inventory-boundary"),
                (40, "target-restart"),
                (70, "database-pause"),
                (100, "inventory-boundary"),
            ]
            if args.smoke_phases
            else [
                (1800, "inventory-boundary"),
                (3600, "target-restart"),
                (5400, "database-pause"),
                (7200, "inventory-boundary"),
                (9000, "target-restart"),
                (10800, "database-pause"),
                (12600, "inventory-boundary"),
            ]
        )

    def pid(self, label: str) -> int:
        pid = super().pid(label)
        self.pid_labels[label] = pid
        return pid

    def progress(self, event: dict[str, Any]) -> None:
        record = {"timestamp": datetime.now(UTC).isoformat(), **event}
        with self.progress_path.open("a") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
            stream.flush()

    def prepare(self) -> None:
        revision = subprocess.check_output(
            ["git", "-C", str(self.project), "rev-parse", "HEAD"], text=True
        ).strip()
        if revision != self.config["revision"]:
            raise ValueError("UNEXPECTED_REVISION")
        distribution = (
            self.args.distribution
            or self.project / self.config["distributionDirectory"]
        )
        original_jar = distribution / "target/nacos-server.jar"
        if not original_jar.is_file():
            raise ValueError("NACOS_DISTRIBUTION_JAR_MISSING")
        classes = self.work / "classes"
        classes.mkdir(exist_ok=True)
        imports = (
            classes
            / "META-INF/spring/org.springframework.boot.actuate.autoconfigure.web."
            "ManagementContextConfiguration.imports"
        )
        imports.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(
            FIXTURE
            / "META-INF/spring/org.springframework.boot.actuate.autoconfigure.web."
            "ManagementContextConfiguration.imports",
            imports,
        )
        shutil.copytree(distribution / "conf", self.work / "conf", dirs_exist_ok=True)
        for directory in ("logs", "data", "target"):
            (self.work / directory).mkdir(exist_ok=True)
        classpath_file = (
            self.args.classpath_file or self.project / "console/classpath-runtime.txt"
        )
        if not classpath_file.is_file():
            generated = subprocess.run(
                [
                    "mvn",
                    "-B",
                    "-q",
                    "--no-transfer-progress",
                    "-pl",
                    "console",
                    "dependency:build-classpath",
                    f"-Dmdep.outputFile={classpath_file}",
                    "-DincludeScope=runtime",
                ],
                cwd=self.project,
                env={**environment(), "JAVA_HOME": str(JAVA21.parent.parent)},
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                check=False,
            )
            if generated.returncode:
                raise ValueError("NACOS_CLASSPATH_BUILD_FAILED")
        classpath = classpath_file.read_text().strip().split(os.pathsep)
        classpath.append(str(self.project / "console/target/classes"))
        compiled = subprocess.run(
            [
                str(JAVAC21),
                "-cp",
                os.pathsep.join(classpath),
                "-d",
                str(classes),
                str(FIXTURE / "DiagnosticManagementSecurity.java"),
                str(FIXTURE / "NacosDiagnosticsLauncher.java"),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.report["operatorLauncherCompileExit"] = compiled.returncode
        if compiled.returncode:
            print(compiled.stderr.decode(errors="replace")[:5000], file=sys.stderr)
            raise ValueError("OPERATOR_LAUNCHER_COMPILE_FAILED")
        self.patched_jar = self.work / "target/nacos-server.jar"
        self.patch_jar(original_jar, self.patched_jar)
        properties = (FIXTURE / "common.properties").read_text()
        properties += "\n" + (FIXTURE / "nacos.properties").read_text()
        properties += (
            f"\nserver.port={self.port}\n"
            f"management.server.port={self.management_port}\n"
            "spring.sql.init.platform=mysql\n"
            "db.num=1\n"
            f"db.url.0=jdbc:mysql://127.0.0.1:{self.db_port}/nacos_config"
            "?characterEncoding=utf8&connectTimeout=3000&socketTimeout=10000"
            "&autoReconnect=true&useUnicode=true&useSSL=false"
            "&allowPublicKeyRetrieval=true&serverTimezone=UTC\n"
            "db.user.0=nacos\n"
        )
        (self.work / "nacos.properties").write_text(properties)
        self.report["classpathEntryCount"] = len(classpath)
        self.report["nacosDistributionJarSha256"] = sha256_file(original_jar)
        self.report["patchedJarSha256"] = sha256_file(self.patched_jar)

    def patch_jar(self, source: Path, destination: Path) -> None:
        if destination.is_file():
            return
        removed: list[str] = []
        with (
            zipfile.ZipFile(source) as archive,
            zipfile.ZipFile(destination, "w", zipfile.ZIP_STORED) as output,
        ):
            for item in archive.infolist():
                if item.filename == "BOOT-INF/lib/hessian-3.3.6.jar":
                    removed.append(item.filename)
                    continue
                data = archive.read(item.filename)
                if item.filename == "BOOT-INF/classpath.idx":
                    data = (
                        "\n".join(
                            line
                            for line in data.decode().splitlines()
                            if "hessian-3.3.6.jar" not in line
                        )
                        + "\n"
                    ).encode()
                output.writestr(item, data)
        self.report["jarPatch"] = {
            "reason": (
                "SOFA JRaft ships hessian-3.3.6 with the same com.caucho package; "
                "NacosHessianSerializerFactory requires 4.0.63"
            ),
            "removed": removed,
            "scope": "operator copy only; source and original distribution untouched",
        }

    def start_database(self) -> None:
        schema = self.project / "distribution/conf/mysql-schema.sql"
        if not schema.is_file():
            raise ValueError("DATABASE_INIT_SCRIPT_MISSING")
        subprocess.run(
            ["docker", "rm", "-f", self.db_container],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        result = subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                self.db_container,
                "-e",
                f"MARIADB_ROOT_PASSWORD={secrets.token_urlsafe(24)}",
                "-e",
                "MARIADB_DATABASE=nacos_config",
                "-e",
                "MARIADB_USER=nacos",
                "-e",
                f"MARIADB_PASSWORD={self.db_password}",
                "-p",
                f"127.0.0.1:{self.db_port}:3306",
                "-v",
                f"{schema}:/docker-entrypoint-initdb.d/01-nacos-schema.sql:ro",
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
            NACOS_DIAGNOSTICS_ADMIN=self.admin,
            NACOS_DIAGNOSTICS_USER=self.user,
            NACOS_DB_PASSWORD=self.db_password,
        )
        self.process = subprocess.Popen(
            [
                str(JAVA21),
                "-Xms512m",
                "-Xmx1280m",
                "-Dnacos.standalone=true",
                f"-Dnacos.home={self.work}",
                f"-Dloader.path={self.work / 'classes'}",
                "-Dloader.main=com.alibaba.nacos.diagnostics.NacosDiagnosticsLauncher",
                "-jar",
                str(self.patched_jar),
                str(self.work / "nacos.properties"),
                str(self.work / "conf/nacos-logback.xml"),
            ],
            cwd=self.work,
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

    def business_readiness(self, timeout: float = 5) -> dict[str, Any]:
        return direct_get(
            self.port, "/nacos/v1/console/health/readiness", timeout=timeout
        )

    def database_state(self) -> str:
        probe = subprocess.run(
            [
                "docker",
                "inspect",
                "--format",
                "{{.State.Status}} paused={{.State.Paused}}",
                self.db_container,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        return probe.stdout.strip() or "missing"

    async def wait_until_idle(self, timeout: float = 30) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.active_calls == 0:
                return True
            await asyncio.sleep(0.1)
        return False

    async def sample(self, started: float) -> None:
        target_pid = self.process.pid if self.process else 0
        host_pid = self.pid_labels.get("legacy", 0)
        previous = self.samples[-1] if self.samples else {}
        target = (
            process_metrics(target_pid, previous.get("target")) if target_pid else {}
        )
        host = process_metrics(host_pid, previous.get("host")) if host_pid else {}
        self.samples.append(
            {
                "elapsedSeconds": round(time.monotonic() - started, 3),
                "phase": self.phase_name,
                "calls": self.calls,
                "target": target,
                "host": host,
                "database": self.database_state(),
                "actuatorHealth": direct_get(
                    self.management_port,
                    "/actuator/health",
                    timeout=2,
                    bearer=self.admin,
                ),
                "businessReadiness": self.business_readiness(timeout=2),
            }
        )
        self.progress(
            {"event": "sample", **self.samples[-1], "statuses": dict(self.statuses)}
        )

    async def monitor(self, started: float) -> None:
        while True:
            await asyncio.sleep(self.args.sample_seconds)
            try:
                await self.sample(started)
            except Exception as exc:
                self.progress(
                    {
                        "event": "sample-error",
                        "elapsedSeconds": round(time.monotonic() - started, 3),
                        "exceptionType": type(exc).__name__,
                    }
                )

    async def full_inventory(self, client: Client, label: str) -> None:
        started = time.monotonic()
        query: dict[str, Any] = {
            "beanNamePattern": "*",
            "maxResults": 50,
            "maxDepth": 0,
        }
        ids: set[str] = set()
        pages = 0
        snapshot = None
        exhausted = False
        terminal = None
        while True:
            result = await self.call(
                client, "inspect_beans", query, f"{label}-page-{pages}"
            )
            terminal = result
            if result["data"] is None:
                self.expect(False, "INVENTORY_PAGE_FAILED")
                break
            page_ids = [row["id"] for row in result["data"]["items"]]
            self.expect(
                len(set(page_ids)) == len(page_ids) and not ids.intersection(page_ids),
                "INVENTORY_DUPLICATE_PAGE",
            )
            ids.update(page_ids)
            current = result["source"]["snapshotId"]
            self.expect(
                snapshot is None or snapshot == current, "INVENTORY_SNAPSHOT_CHANGED"
            )
            snapshot = current
            pages += 1
            if not result["nextCursor"]:
                exhausted = True
                break
            if pages >= 500:
                break
            query["cursor"] = result["nextCursor"]
        expected = (self.report.get("pagination") or {}).get("expectedVisibleBeans")
        if exhausted and expected is not None:
            self.expect(len(ids) == expected, "INVENTORY_DRIFT")
        record = {
            "label": label,
            "elapsedSeconds": round(time.monotonic() - started, 3),
            "pages": pages,
            "uniqueBeans": len(ids),
            "expectedVisibleBeans": expected,
            "exhausted": exhausted,
            "reportedTotalMatched": terminal["totalMatched"] if terminal else None,
            "coverage": terminal["coverage"] if terminal else None,
        }
        self.inventory_checks.append(record)
        self.progress({"event": "inventory", **record})

    async def boundary_checks(self, client: Client, label: str) -> None:
        checks: list[tuple[str, str, dict[str, Any], set[str]]] = [
            (
                "invalid-arguments",
                "diagnose_health",
                {"maxResults": 0},
                {"INVALID_ARGUMENT"},
            ),
            (
                "config-disabled",
                "inspect_config",
                {"prefix": "spring"},
                {"CAPABILITY_DISABLED"},
            ),
            (
                "openapi-unexposed",
                "search_openapi",
                {"pathPattern": self.config["route"]},
                {"ENDPOINT_NOT_EXPOSED"},
            ),
            (
                "migrations-unexposed",
                "check_migrations",
                {"engine": "flyway"},
                {"ENDPOINT_NOT_EXPOSED"},
            ),
        ]
        for name, tool, arguments, expected in checks:
            result = await self.call(client, tool, arguments, f"{label}-{name}")
            codes = {row["code"] for row in result["errors"]}
            self.expect(bool(codes & expected), f"BOUNDARY_{name.upper()}_NOT_REJECTED")
            self.boundary_results.append(
                {
                    "label": f"{label}-{name}",
                    "tool": tool,
                    "status": result["status"],
                    "errorCodes": sorted(codes),
                    "expected": sorted(expected),
                }
            )
        seed = await self.call(
            client,
            "inspect_beans",
            {"beanNamePattern": "*", "maxResults": 20, "maxDepth": 0},
            f"{label}-cursor-seed",
        )
        if seed["nextCursor"]:
            mismatch = await self.call(
                client,
                "inspect_beans",
                {
                    "beanNamePattern": "*",
                    "maxResults": 1,
                    "maxDepth": 0,
                    "cursor": seed["nextCursor"],
                },
                f"{label}-cursor-mismatch",
            )
            codes = {row["code"] for row in mismatch["errors"]}
            self.expect(
                mismatch["data"] is None and bool(codes),
                "BOUNDARY_CURSOR_NOT_BOUND",
            )
            self.expected_codes.update(codes)
            self.boundary_results.append(
                {
                    "label": f"{label}-cursor-mismatch",
                    "tool": "inspect_beans",
                    "status": mismatch["status"],
                    "errorCodes": sorted(codes),
                    "expected": ["cursor query binding"],
                }
            )
        drift = await self.call(
            client,
            "detect_drift",
            {
                "expectedBeans": [{"name": self.config["bean"]}],
                "expectedRoutes": [{"path": self.config["route"], "httpMethod": "GET"}],
            },
            f"{label}-drift",
        )
        self.expect(
            bool(drift["data"]) and not drift["data"]["missingInRuntime"],
            "BOUNDARY_DRIFT_MISMATCH",
        )
        mappings = await self.call(
            client,
            "verify_mappings",
            {"pathPattern": self.config["route"], "httpMethod": "GET"},
            f"{label}-mappings",
        )
        self.expect(
            bool(mappings["data"]) and bool(mappings["data"]["items"]),
            "BOUNDARY_ROUTE_MISSING",
        )
        health = await self.call(
            client,
            "diagnose_health",
            {"includeDetails": True, "includeHealthy": True},
            f"{label}-health",
        )
        self.expect(
            bool(health["data"]) and bool(health["data"]["items"]),
            "BOUNDARY_HEALTH_MISSING",
        )
        startup = await self.call(
            client,
            "analyze_startup",
            {"minDurationMs": 1, "maxResults": 5},
            f"{label}-startup",
        )
        self.expect(
            bool(startup["data"]) and bool(startup["data"]["items"]),
            "BOUNDARY_STARTUP_MISSING",
        )
        self.boundary_results.append(
            {
                "label": f"{label}-positive-domain",
                "tools": [
                    "detect_drift",
                    "verify_mappings",
                    "diagnose_health",
                    "analyze_startup",
                ],
                "status": "ok",
            }
        )

    async def restart_target(self, client: Client, started: float) -> None:
        old_pid = self.process.pid if self.process else None
        event_started = time.monotonic()
        self.progress({"event": "target-restart-start", "oldPid": old_pid})
        if self.process is not None:
            stop(self.process)
        stopped = await self.call(
            client,
            "inspect_beans",
            {"beanNamePattern": self.config["bean"]},
            "phase-target-stopped",
        )
        self.expect(
            any(
                row["code"] == "TARGET_CONNECTION_REFUSED" for row in stopped["errors"]
            ),
            "TARGET_STOP_NOT_REPORTED",
        )
        self.expected_codes.update(row["code"] for row in stopped["errors"])
        await asyncio.to_thread(self.start)
        recovered = await self.call(
            client,
            "inspect_beans",
            {"beanNamePattern": self.config["bean"]},
            "phase-target-recovered",
        )
        self.expect(
            bool(recovered["data"]) and bool(recovered["data"]["items"]),
            "TARGET_RESTART_RECOVERY_FAILED",
        )
        record = {
            "atSeconds": round(event_started - started, 3),
            "recoverySeconds": round(time.monotonic() - event_started, 3),
            "oldPid": old_pid,
            "newPid": self.process.pid if self.process else None,
            "startupSeconds": (self.report.get("startupSeconds") or [None])[-1],
        }
        self.target_restarts.append(record)
        self.progress({"event": "target-restart-complete", **record})

    async def pause_database(self, client: Client, started: float) -> None:
        event_started = time.monotonic()
        health_args = {"includeDetails": True, "includeHealthy": True}
        before = await self.call(
            client, "diagnose_health", health_args, "phase-db-before"
        )
        before_status = (before["data"] or {}).get("overallStatus")
        before_ready = self.business_readiness()
        self.progress(
            {
                "event": "database-pause-start",
                "beforeActuator": before_status,
                "beforeReadiness": before_ready,
            }
        )
        paused = subprocess.run(
            ["docker", "pause", self.db_container],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        self.expect(paused.returncode == 0, "DATABASE_PAUSE_FAILED")
        await asyncio.sleep(6)
        during = await self.call(
            client, "diagnose_health", health_args, "phase-db-during"
        )
        during_status = (during["data"] or {}).get("overallStatus")
        during_ready = self.business_readiness()
        during_state = self.database_state()
        subprocess.run(
            ["docker", "unpause", self.db_container],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        recovered = None
        attempts = 0
        for attempts in range(1, 31):
            await asyncio.sleep(2)
            probe = self.business_readiness(timeout=4)
            if probe.get("httpStatus") == 200:
                recovered = probe
                break
        self.expect(recovered is not None, "DATABASE_RECOVERY_FAILED")
        after = await self.call(
            client, "diagnose_health", health_args, "phase-db-after"
        )
        after_status = (after["data"] or {}).get("overallStatus")
        record = {
            "atSeconds": round(event_started - started, 3),
            "actuatorBefore": before_status,
            "actuatorDuring": during_status,
            "actuatorAfter": after_status,
            "readinessBefore": before_ready,
            "readinessDuring": during_ready,
            "readinessRecovered": recovered,
            "databaseDuring": during_state,
            "recoveryAttempts": attempts,
            "actuatorObservedExternalDbOutage": during_status != "UP",
        }
        self.database_pauses.append(record)
        self.progress({"event": "database-pause-complete", **record})

    async def phase_controller(self, client: Client, started: float) -> None:
        for offset, name in self.phase_schedule:
            if offset >= self.args.soak_seconds - 60:
                break
            delay = started + offset - time.monotonic()
            if delay > 0:
                await asyncio.sleep(delay)
            self.pause.set()
            await self.wait_until_idle()
            self.phase_name = name
            self.progress({"event": "phase-start", "phase": name, "offset": offset})
            try:
                if name == "inventory-boundary":
                    await self.full_inventory(client, f"{name}-{offset}")
                    await self.boundary_checks(client, f"{name}-{offset}")
                elif name == "target-restart":
                    await self.restart_target(client, started)
                elif name == "database-pause":
                    await self.pause_database(client, started)
            except Exception as exc:
                code = "PHASE_" + name.upper().replace("-", "_") + "_FAILED"
                self.expect(False, code)
                self.phase_errors.append(
                    {
                        "phase": name,
                        "offset": offset,
                        "exceptionType": type(exc).__name__,
                    }
                )
                print("nacos phase-error", name, type(exc).__name__, flush=True)
                self.progress(
                    {
                        "event": "phase-error",
                        "phase": name,
                        "offset": offset,
                        "exceptionType": type(exc).__name__,
                    }
                )
            finally:
                self.phase_name = "soak"
                self.pause.clear()
                self.progress({"event": "phase-end", "phase": name})

    async def soak(self, client: Client) -> None:
        started = time.monotonic()
        before = self.calls
        self.phase_name = "soak"
        self.progress(
            {
                "event": "soak-start",
                "seconds": self.args.soak_seconds,
                "workers": self.args.workers,
                "workerDelaySeconds": self.args.worker_delay,
            }
        )
        queries = [
            ("inspect_beans", {"beanNamePattern": self.config["bean"], "maxDepth": 0}),
            (
                "inspect_beans",
                {
                    "beanNamePattern": self.config["bean"],
                    "maxDepth": 1,
                    "maxResults": 5,
                },
            ),
            (
                "verify_mappings",
                {"pathPattern": self.config["route"], "httpMethod": "GET"},
            ),
            ("diagnose_health", {"includeHealthy": True, "maxResults": 5}),
            (
                "diagnose_health",
                {"includeDetails": True, "includeHealthy": True},
            ),
            ("analyze_startup", {"minDurationMs": 1, "maxResults": 3}),
            ("analyze_startup", {"minDurationMs": 10, "maxResults": 5}),
            (
                "inspect_beans",
                {"beanNamePattern": "data*", "maxDepth": 2, "maxResults": 10},
            ),
        ]
        stop_at = started + self.args.soak_seconds

        async def worker(offset: int) -> None:
            index = offset
            while time.monotonic() < stop_at:
                if self.pause.is_set():
                    await asyncio.sleep(0.2)
                    continue
                tool, arguments = queries[index % len(queries)]
                self.active_calls += 1
                try:
                    await self.call(
                        client, tool, arguments, "soak-" + tool, aggregate=True
                    )
                finally:
                    self.active_calls -= 1
                index += 1
                await asyncio.sleep(self.args.worker_delay)

        tasks = [
            asyncio.create_task(worker(index)) for index in range(self.args.workers)
        ]
        monitor_task = asyncio.create_task(self.monitor(started))
        phase_task = (
            asyncio.create_task(self.phase_controller(client, started))
            if self.args.smoke_phases or self.args.soak_seconds >= 1800
            else None
        )
        last_report = started
        try:
            while not all(task.done() for task in tasks):
                await asyncio.sleep(1)
                if time.monotonic() - last_report >= 300:
                    print(
                        "nacos soakCalls=" + str(self.calls - before),
                        flush=True,
                    )
                    last_report = time.monotonic()
            await asyncio.gather(*tasks)
        finally:
            for task in (monitor_task, phase_task):
                if task is not None:
                    task.cancel()
            await asyncio.gather(
                *(task for task in (monitor_task, phase_task) if task is not None),
                return_exceptions=True,
            )
        await self.sample(started)
        elapsed = time.monotonic() - started
        unexpected = {
            code: count
            for code, count in self.errors.items()
            if code not in self.expected_codes
        }
        self.expect(not unexpected, "UNEXPECTED_ERROR_CODES")
        resource_summary: dict[str, Any] = {}
        for key in ("target", "host"):
            values = [sample[key] for sample in self.samples if sample.get(key)]
            if not values:
                continue
            resource_summary[key] = {
                "samples": len(values),
                "rssKiB": {
                    "first": values[0].get("rssKiB"),
                    "last": values[-1].get("rssKiB"),
                    "min": min(value.get("rssKiB", 0) for value in values),
                    "max": max(value.get("rssKiB", 0) for value in values),
                    "median": round(
                        statistics.median(value.get("rssKiB", 0) for value in values), 3
                    ),
                },
                "openFiles": {
                    "first": values[0].get("openFiles"),
                    "last": values[-1].get("openFiles"),
                    "max": max(value.get("openFiles", 0) for value in values),
                },
                "threads": {
                    "first": values[0].get("threads"),
                    "last": values[-1].get("threads"),
                    "max": max(value.get("threads", 0) for value in values),
                },
            }
        self.report["soak"] = {
            "workers": self.args.workers,
            "workerDelaySeconds": self.args.worker_delay,
            "plannedSeconds": self.args.soak_seconds,
            "seconds": round(elapsed, 3),
            "calls": self.calls - before,
            "toolCalls": dict(self.soak_tools),
            "coverageGaps": dict(self.soak_gaps),
            "samples": len(self.samples),
            "progressFile": str(self.progress_path),
            "inventoryChecks": self.inventory_checks,
            "boundaryChecks": self.boundary_results,
            "targetRestarts": self.target_restarts,
            "databasePauses": self.database_pauses,
            "phaseErrors": self.phase_errors,
            "resourceSummary": resource_summary,
            "expectedErrorCodes": sorted(self.expected_codes),
            "unexpectedErrorCodes": unexpected,
        }
        self.progress(
            {
                "event": "soak-complete",
                "seconds": round(elapsed, 3),
                "calls": self.calls - before,
                "unexpectedErrorCodes": unexpected,
            }
        )

    def run(self) -> int:
        try:
            self.start_database()
        except Exception as exc:
            self.report["failureCodes"].append("DATABASE_START_FAILED")
            self.report["harnessExceptionType"] = type(exc).__name__
            self.report["databaseStopped"] = self.stop_database()
            self.report["accepted"] = False
            self.args.output.parent.mkdir(parents=True, exist_ok=True)
            self.args.output.write_text(
                json.dumps(self.report, ensure_ascii=False, indent=2) + "\n"
            )
            return 1
        try:
            return super().run()
        finally:
            stopped = self.stop_database()
            self.report["databaseStopped"] = stopped
            self.report["databasePortLoopbackOnly"] = True
            if not stopped:
                self.report["failureCodes"].append("DATABASE_CONTAINER_LEAK")
            self.report["accepted"] = not self.report["failureCodes"]
            self.args.output.parent.mkdir(parents=True, exist_ok=True)
            self.args.output.write_text(
                json.dumps(self.report, ensure_ascii=False, indent=2) + "\n"
            )


def _reserve_result_paths(output: Path, progress: Path) -> None:
    """Claim both result files before any target resources are initialized."""
    if output == progress:
        raise ValueError("result paths must differ")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x"):
        pass
    try:
        progress.parent.mkdir(parents=True, exist_ok=True)
        with progress.open("x"):
            pass
    except OSError:
        output.unlink()
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default="nacos", choices=("nacos",))
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--distribution", type=Path)
    parser.add_argument("--classpath-file", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--progress", type=Path)
    parser.add_argument("--soak-seconds", type=int, default=14400)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--worker-delay", type=float, default=0.5)
    parser.add_argument("--sample-seconds", type=int, default=60)
    parser.add_argument(
        "--smoke-phases",
        action="store_true",
        help="run compressed inventory/restart/database phases for a short acceptance",
    )
    args = parser.parse_args()
    if not 65 <= args.soak_seconds <= 14400:
        parser.error("--soak-seconds must be between 65 and 14400")
    if not 1 <= args.workers <= 8:
        parser.error("--workers must be between 1 and 8")
    if not 0.1 <= args.worker_delay <= 10:
        parser.error("--worker-delay must be between 0.1 and 10")
    if not 5 <= args.sample_seconds <= 300:
        parser.error("--sample-seconds must be between 5 and 300")
    args.progress = args.progress or args.output.with_suffix(".jsonl")
    try:
        _reserve_result_paths(args.output, args.progress)
    except (OSError, ValueError):
        parser.error("output and progress must be distinct new writable files")
    return NacosSoakAcceptance(args).run()


if __name__ == "__main__":
    raise SystemExit(main())
