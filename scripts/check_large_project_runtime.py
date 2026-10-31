"""Opt-in native public-project soak; never part of the offline test suite.

Only operator-prepared fixed revisions run. Target output is discarded except for
bounded startup identifiers. Persist sanitized aggregates, never target bodies.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import secrets
import socket
import statistics
import subprocess
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from zipfile import ZipFile

from check_project_runtime import environment, ready
from mcp import Client, StdioServerParameters

from spring_runtime_mcp.contracts.definitions import definition
from spring_runtime_mcp.policy.output_guard import ensure_safe_output
from spring_runtime_mcp.policy.sanitization import MARKER, SanitizerPipeline
from spring_runtime_mcp.server import SERVER_INFO_META, _valid_envelope, build_services
from spring_runtime_mcp.transport.responses import serialize_response

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples/large-project-matrix"


def stop(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def memory(pid: int) -> dict[str, int]:
    try:
        status = Path(f"/proc/{pid}/status").read_text()
        rss = next(line for line in status.splitlines() if line.startswith("VmRSS:"))
        return {
            "rssKiB": int(rss.split()[1]),
            "openFiles": len(list(Path(f"/proc/{pid}/fd").iterdir())),
        }
    except (OSError, StopIteration):
        return {}


class Acceptance:
    def __init__(self, args: argparse.Namespace, *, fixture: Path = FIXTURE) -> None:
        self.args = args
        self.fixture = fixture
        self.config = json.loads((self.fixture / "projects.json").read_text())[
            args.name
        ]
        self.project = args.project.resolve()
        self.work = self.project / ".large-diagnostics"
        self.work.mkdir(exist_ok=True)
        self.admin, self.user = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        self.pipeline = SanitizerPipeline((self.admin, self.user))
        self.port = free_port()
        self.management_port = free_port() if self.config["separatePort"] else self.port
        self.target = f"http://127.0.0.1:{self.management_port}"
        self.process: subprocess.Popen[bytes] | None = None
        self.phase = "prepare"
        self.clients: list[int] = []
        self.latencies: list[float] = []
        self.statuses: Counter[str] = Counter()
        self.errors: Counter[str] = Counter()
        self.soak_gaps: Counter[str] = Counter()
        self.soak_tools: Counter[str] = Counter()
        self.calls = 0
        self.max_bytes = 0
        self.report: dict[str, Any] = {
            "verifiedAt": datetime.now(UTC).isoformat(),
            "project": args.name,
            "sourceRepository": self.config["repository"],
            "sourceRevision": self.config["revision"],
            "sourceTag": self.config["tag"],
            "configuredBootVersion": self.config["bootVersion"],
            "stack": self.config["stack"],
            "authentication": "operator-management-only-Bearer",
            "database": "disposable-in-memory-H2" if self.config["database"] else None,
            "mainJavaSourceFiles": sum(
                "/src/main/java/" in str(path) for path in self.project.rglob("*.java")
            ),
            "checks": [],
            "failureCodes": [],
            "startupErrorTypes": [],
            "startupBeanIdentifiers": [],
        }

    def expect(self, condition: bool, code: str) -> None:
        if not condition and code not in self.report["failureCodes"]:
            self.report["failureCodes"].append(code)

    def prepare(self) -> None:
        revision = subprocess.check_output(
            ["git", "-C", str(self.project), "rev-parse", "HEAD"], text=True
        ).strip()
        if revision != self.config["revision"]:
            raise ValueError("UNEXPECTED_REVISION")
        module = self.project / self.config["module"]
        runtime = (
            (module / "classpath-runtime.txt").read_text().strip().split(os.pathsep)
        )
        provided: list[str] = []
        if self.args.name == "flowable":
            # Native executable WAR marks its own embedded container as provided.
            # Recover only that WAR's lib-provided jars, never test dependencies.
            directory = self.work / "provided"
            directory.mkdir(exist_ok=True)
            with ZipFile(module / "target/flowable-rest.war") as archive:
                for name in archive.namelist():
                    if name.startswith("WEB-INF/lib-provided/") and name.endswith(
                        ".jar"
                    ):
                        destination = directory / Path(name).name
                        destination.write_bytes(archive.read(name))
                        provided.append(str(destination))
        artifacts = [Path(path).name for path in runtime + provided]
        self.report["runtimeArtifacts"] = artifacts
        self.report["runtimeArtifactsSha256"] = hashlib.sha256(
            "\n".join(sorted(artifacts)).encode()
        ).hexdigest()
        self.report["nativeProvidedArtifacts"] = [Path(path).name for path in provided]
        self.classpath = os.pathsep.join(
            [str(module / "target/classes"), *runtime, *provided]
        )
        if self.config["stack"] == "reactive":
            source = (self.fixture / "ReactiveSecurity.java.template").read_text()
        elif self.config["stack"] == "servlet-javax":
            source = (self.fixture / "LegacyServletSecurity.java.template").read_text()
        else:
            namespace = self.config["stack"].split("-")[1]
            source = (self.fixture / "ServletSecurity.java.template").read_text()
            source = source.replace("SERVLET_PACKAGE", namespace).replace(
                "MATCHER_METHOD",
                "requestMatcher" if namespace == "javax" else "securityMatcher",
            )
        (self.work / "DiagnosticSecurity.java").write_text(source)
        compiled = subprocess.run(
            [
                "javac",
                "-cp",
                self.classpath,
                "-d",
                str(self.work),
                str(self.work / "DiagnosticSecurity.java"),
                str(self.fixture / "LargeProjectLauncher.java"),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.report["operatorLauncherCompileExit"] = compiled.returncode
        if compiled.returncode:
            # Compiler output contains only operator source, but is not persisted.
            print(compiled.stderr.decode(errors="replace")[:5000], file=sys.stderr)
            raise ValueError("OPERATOR_LAUNCHER_COMPILE_FAILED")
        properties = (self.fixture / "common.properties").read_text()
        properties += (
            "\n" + (self.fixture / (self.args.name + ".properties")).read_text()
        )
        properties += f"\nserver.port={self.port}\nmanagement.server.port={self.management_port}\n"
        if self.config["separatePort"]:
            properties += "management.server.address=127.0.0.1\n"
        (self.work / "application.properties").write_text(properties)

    def start(self) -> None:
        env = environment()
        env.update(LARGE_DIAGNOSTICS_ADMIN=self.admin, LARGE_DIAGNOSTICS_USER=self.user)
        self.process = subprocess.Popen(
            [
                "java",
                "-Xmx768m",
                "-Dspring.devtools.restart.enabled=false",
                "-cp",
                str(self.work) + os.pathsep + self.classpath,
                "LargeProjectLauncher",
                self.config["mainClass"],
                str(self.work / "application.properties"),
                str(ROOT / "examples/project-matrix/logback-diagnostics.xml"),
            ],
            cwd=self.project,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        started = time.monotonic()
        port, java = ready(self.process, self.report)
        self.expect(port == self.management_port, "MANAGEMENT_PORT_MISMATCH")
        self.report["javaMajor"] = java
        self.report.setdefault("startupSeconds", []).append(
            round(time.monotonic() - started, 3)
        )

    def parameters(self, label: str, token: str | None) -> StdioServerParameters:
        env = environment()
        env["PYTHONPATH"] = str(ROOT / "src")
        pidfile = self.work / (label + ".pid")
        pidfile.unlink(missing_ok=True)
        env["LARGE_DIAGNOSTICS_PIDFILE"] = str(pidfile)
        # The wrapper records its own pid before starting the unchanged CLI.
        wrapper = (
            "import os; from pathlib import Path; "
            "Path(os.environ['LARGE_DIAGNOSTICS_PIDFILE']).write_text(str(os.getpid())); "
            "from spring_runtime_mcp.cli import main; main()"
        )
        args = ["-c", wrapper, "--base-url", self.target]
        if token:
            env["LARGE_DIAGNOSTICS_BEARER"] = token
            args += ["--token-env", "LARGE_DIAGNOSTICS_BEARER"]
        return StdioServerParameters(command=sys.executable, args=args, env=env)

    def pid(self, label: str) -> int:
        pid = int((self.work / (label + ".pid")).read_text())
        self.clients.append(pid)
        return pid

    async def call(
        self,
        client: Client,
        tool: str,
        args: dict[str, Any],
        case: str,
        *,
        aggregate: bool = False,
    ) -> dict[str, Any]:
        self.phase = case
        started = time.monotonic()
        response = await client.call_tool("springboot_" + tool, args)
        elapsed = (time.monotonic() - started) * 1000
        result = response.structured_content
        assert isinstance(result, dict)
        assert _valid_envelope(definition("springboot_" + tool)["outputSchema"], result)
        ensure_safe_output(result, sanitizer=self.pipeline)
        frame = serialize_response(
            result, "\0" * 128, sanitizer=self.pipeline, server_meta=SERVER_INFO_META
        )
        self.calls += 1
        self.latencies.append(elapsed)
        self.max_bytes = max(self.max_bytes, len(frame))
        self.statuses[result["status"]] += 1
        codes = [row["code"] for row in result["errors"]]
        self.errors.update(codes)
        if aggregate:
            self.soak_gaps.update(result["coverage"]["gaps"])
            self.soak_tools[tool] += 1
            self.expect(
                result["status"] in {"ok", "partial"} and result["data"] is not None,
                "SOAK_POSITIVE_CALL_FAILED",
            )
            self.expect(not codes, "SOAK_UNEXPECTED_ERROR")
            self.expect(
                bool(result["data"]) and bool(result["data"].get("items")),
                "SOAK_EXPECTED_FACTS_MISSING",
            )
        if not aggregate or codes:
            self.report["checks"].append(
                {
                    "case": case,
                    "tool": tool,
                    "status": result["status"],
                    "totalMatched": result["totalMatched"],
                    "coverage": result["coverage"]["state"],
                    "gaps": result["coverage"]["gaps"],
                    "truncated": result["truncated"],
                    "errorCodes": codes,
                    "httpStatuses": [row["httpStatus"] for row in result["errors"]],
                    "responseBytes": len(frame),
                    "elapsedMs": round(elapsed, 3),
                }
            )
        return result

    async def verify(self) -> None:
        bean_args = {"beanNamePattern": self.config["bean"]}
        for label, token, status in (
            ("anonymous", None, 401),
            ("non-admin", self.user, 403),
        ):
            async with Client(
                self.parameters(label, token), mode="legacy", read_timeout_seconds=25
            ) as client:
                self.pid(label)
                result = await self.call(client, "inspect_beans", bean_args, label)
                self.expect(
                    result["status"] == "denied"
                    and result["data"] is None
                    and any(row["httpStatus"] == status for row in result["errors"]),
                    "AUTHORIZATION_NOT_ENFORCED",
                )
        modes: tuple[Literal["legacy", "2026-07-28"], ...] = ("legacy", "2026-07-28")
        for mode in modes:
            self.phase = mode + "-discovery"
            async with Client(
                self.parameters(mode, self.admin), mode=mode, read_timeout_seconds=25
            ) as client:
                tools = (await client.list_tools()).tools
                pid = self.pid(mode)
                self.expect(
                    len(tools) == 8
                    and [tool.name for tool in tools]
                    == sorted(tool.name for tool in tools),
                    "TOOL_DISCOVERY_MISMATCH",
                )
                self.expect(
                    all(
                        tool.annotations is not None
                        and tool.annotations.read_only_hint
                        and tool.annotations.idempotent_hint
                        and not tool.annotations.destructive_hint
                        and not tool.annotations.open_world_hint
                        for tool in tools
                    ),
                    "RISK_ANNOTATIONS_MISMATCH",
                )
                result = await self.call(
                    client, "inspect_beans", bean_args, mode + "-known-bean"
                )
                self.expect(
                    bool(result["data"])
                    and any(
                        row["name"] == self.config["bean"]
                        for row in result["data"]["items"]
                    ),
                    "KNOWN_BEAN_NOT_RETURNED",
                )
                result = await self.call(
                    client,
                    "diagnose_health",
                    {"maxResults": 0},
                    mode + "-invalid-arguments",
                )
                self.expect(
                    any(row["code"] == "INVALID_ARGUMENT" for row in result["errors"]),
                    "INVALID_ARGUMENT_NOT_REJECTED",
                )
                if mode == "legacy":
                    await self.baseline(client)
                    page_args = {
                        "beanNamePattern": "*",
                        "maxResults": 20,
                        "maxDepth": 0,
                    }
                    first = await self.call(
                        client, "inspect_beans", page_args, "expiry-seed"
                    )
                    expiry_cursor = first["nextCursor"]
                    result = await self.call(
                        client,
                        "inspect_beans",
                        {**page_args, "maxResults": 1, "cursor": expiry_cursor},
                        "cursor-query-mismatch",
                    )
                    self.expect(
                        result["data"] is None and bool(result["errors"]),
                        "CURSOR_QUERY_NOT_BOUND",
                    )
                    self.report["hostAfterWarmup"] = memory(pid)
                    await self.soak(client)
                    self.report["hostAfterSoak"] = memory(pid)
                    result = await self.call(
                        client,
                        "inspect_beans",
                        {**page_args, "cursor": expiry_cursor},
                        "cursor-expired",
                    )
                    self.expect(
                        result["data"] is None and bool(result["errors"]),
                        "CURSOR_DID_NOT_EXPIRE",
                    )
                    self.report["hostAliveAfterSoak"] = bool(memory(pid))
                    assert self.process is not None
                    stop(self.process)
                    result = await self.call(
                        client, "inspect_beans", bean_args, "target-stopped"
                    )
                    self.expect(
                        any(
                            row["code"] == "TARGET_CONNECTION_REFUSED"
                            for row in result["errors"]
                        ),
                        "TARGET_STOP_NOT_REPORTED",
                    )
                    self.phase = "restart"
                    await asyncio.to_thread(self.start)
                    result = await self.call(
                        client, "inspect_beans", bean_args, "target-recovered-same-host"
                    )
                    self.expect(
                        bool(result["data"]) and bool(result["data"]["items"]),
                        "RECOVERY_FAILED",
                    )

    async def baseline(self, client: Client) -> None:
        observation = await build_services(self.target, bearer_token=self.admin).read(
            "local", "beans", snapshot_id="large-matrix-inventory"
        )
        contexts = (observation.body or {}).get("contexts", {})
        expected_visible = sum(
            any(
                self.pipeline.identifier(value) != MARKER
                for value in (name, *bean.get("aliases", []))
            )
            for context in contexts.values()
            for name, bean in context.get("beans", {}).items()
        )
        self.report["reportedInventory"] = {
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
        attempts = []
        for attempt in range(2):
            query = {"beanNamePattern": "*", "maxResults": 20, "maxDepth": 0}
            ids: set[str] = set()
            pages = 0
            snapshot = None
            exhausted = False
            while True:
                result = await self.call(
                    client, "inspect_beans", query, "full-bean-page"
                )
                if result["data"] is None:
                    self.expect(False, "PAGINATION_CALL_FAILED")
                    break
                page_ids = [row["id"] for row in result["data"]["items"]]
                self.expect(
                    len(set(page_ids)) == len(page_ids)
                    and not ids.intersection(page_ids),
                    "DUPLICATE_PAGE_RECORDS",
                )
                ids.update(page_ids)
                current = result["source"]["snapshotId"]
                self.expect(
                    snapshot is None or snapshot == current, "PAGE_SNAPSHOT_CHANGED"
                )
                snapshot = current
                pages += 1
                if not result["nextCursor"]:
                    self.expect(
                        result["totalMatched"] is None
                        or len(ids) == result["totalMatched"],
                        "INCOMPLETE_PAGINATION",
                    )
                    exhausted = True
                    break
                assert pages < 1000
                query["cursor"] = result["nextCursor"]
            attempts.append(
                {
                    "attempt": attempt + 1,
                    "pages": pages,
                    "uniqueBeans": len(ids),
                    "exhausted": exhausted,
                    "reportedTotalMatched": result["totalMatched"],
                    "expectedVisibleBeans": expected_visible,
                    "coverageGaps": result["coverage"]["gaps"],
                    "terminalErrorCodes": [row["code"] for row in result["errors"]],
                }
            )
            if exhausted:
                self.expect(
                    len(ids) == expected_visible,
                    "PAGINATION_DIFFERS_FROM_VISIBLE_NATIVE_INVENTORY",
                )
                break
        self.report["pagination"] = attempts[-1]
        self.report["paginationAttempts"] = attempts
        self.expect(exhausted, "PAGINATION_NOT_EXHAUSTED")
        result = await self.call(
            client,
            "inspect_beans",
            {"beanNamePattern": "missingLargeDiagnosticsBean"},
            "missing-bean-conditions",
        )
        self.expect(
            "conditions" in result["source"]["endpointIds"], "CONDITIONS_NOT_READ"
        )
        result = await self.call(
            client,
            "verify_mappings",
            {"pathPattern": self.config["route"], "httpMethod": "GET"},
            "native-route",
        )
        self.expect(
            bool(result["data"])
            and any(
                self.config["route"] in row["paths"] for row in result["data"]["items"]
            ),
            "NATIVE_ROUTE_UNOBSERVED",
        )
        health = {"includeDetails": True, "includeHealthy": True}
        if self.config["database"]:
            health["componentPath"] = ["db"]
        result = await self.call(client, "diagnose_health", health, "native-health")
        self.expect(
            bool(result["data"]) and bool(result["data"]["items"]), "HEALTH_UNOBSERVED"
        )
        result = await self.call(
            client,
            "analyze_startup",
            {"minDurationMs": 1, "maxResults": 5},
            "native-startup",
        )
        self.expect(
            bool(result["data"])
            and bool(result["data"]["items"])
            and result["data"]["springBootVersion"] == self.config["bootVersion"],
            "STARTUP_UNOBSERVED",
        )
        result = await self.call(
            client,
            "check_migrations",
            {"engine": self.config["migrationEngine"] or "flyway"},
            "native-migrations",
        )
        if self.config["migrationEngine"]:
            self.expect(
                bool(result["data"])
                and any(row["state"] == "APPLIED" for row in result["data"]["items"]),
                "MIGRATIONS_UNOBSERVED",
            )
        else:
            self.expect(
                result["data"] is None
                and any(
                    row["code"] == self.config["unexposedErrorCode"]
                    if "unexposedErrorCode" in self.config
                    else row["httpStatus"]
                    == self.config.get("unexposedHttpStatus", 404)
                    for row in result["errors"]
                ),
                "UNEXPOSED_MIGRATION_MISREPORTED",
            )
        result = await self.call(
            client,
            "search_openapi",
            {"pathPattern": self.config["route"]},
            "native-openapi-unexposed",
        )
        self.expect(
            result["data"] is None
            and any(
                row["code"] == self.config["unexposedErrorCode"]
                if "unexposedErrorCode" in self.config
                else row["httpStatus"] == self.config.get("unexposedHttpStatus", 404)
                for row in result["errors"]
            ),
            "UNEXPOSED_OPENAPI_MISREPORTED",
        )
        result = await self.call(
            client, "inspect_config", {"prefix": "spring"}, "config-default-disabled"
        )
        self.expect(
            any(row["code"] == "CAPABILITY_DISABLED" for row in result["errors"]),
            "CONFIG_DEFAULT_ENABLED",
        )
        result = await self.call(
            client,
            "detect_drift",
            {
                "expectedBeans": [{"name": self.config["bean"]}],
                "expectedRoutes": [{"path": self.config["route"], "httpMethod": "GET"}],
                "sourceModifiedAt": "2020-01-01T00:00:00Z",
            },
            "cross-domain-drift",
        )
        self.expect(
            bool(result["data"]) and not result["data"]["missingInRuntime"],
            "DRIFT_FACTS_MISMATCHED",
        )

    async def soak(self, client: Client) -> None:
        started = time.monotonic()
        before = self.calls
        queries = [
            ("inspect_beans", {"beanNamePattern": self.config["bean"]}),
            (
                "verify_mappings",
                {"pathPattern": self.config["route"], "httpMethod": "GET"},
            ),
            ("diagnose_health", {"includeHealthy": True, "maxResults": 5}),
            ("analyze_startup", {"minDurationMs": 1, "maxResults": 3}),
        ]

        async def worker(offset: int) -> None:
            index = offset
            while time.monotonic() - started < self.args.soak_seconds:
                tool, args = queries[index % len(queries)]
                await self.call(client, tool, args, "soak-" + tool, aggregate=True)
                index += 1
                await asyncio.sleep(0.2)

        tasks = [asyncio.create_task(worker(index)) for index in range(4)]
        while not all(task.done() for task in tasks):
            await asyncio.sleep(10)
            print(self.args.name, "soakCalls=" + str(self.calls - before), flush=True)
        await asyncio.gather(*tasks)
        self.report["soak"] = {
            "workers": 4,
            "seconds": round(time.monotonic() - started, 3),
            "calls": self.calls - before,
            "toolCalls": dict(self.soak_tools),
            "coverageGaps": dict(self.soak_gaps),
        }

    def run(self) -> int:
        try:
            self.prepare()
            self.phase = "startup"
            self.start()
            print(self.args.name, "native-startup-ready", flush=True)
            asyncio.run(self.verify())
        except (Exception, KeyboardInterrupt) as exc:
            self.report["failureCodes"].append(
                "HARNESS_FAILED_AT_" + self.phase.upper().replace("-", "_")
            )
            self.report["harnessExceptionType"] = type(exc).__name__
            pending = [exc]
            types: set[str] = set()
            while pending and len(types) < 8:
                failure = pending.pop()
                types.add(type(failure).__name__)
                if isinstance(failure, BaseExceptionGroup):
                    pending.extend(failure.exceptions)
            self.report["harnessExceptionTypes"] = sorted(types)
        finally:
            if self.process is not None:
                stop(self.process)
            self.report["targetProcessStopped"] = (
                self.process is None or self.process.poll() is not None
            )
            self.report["allMcpProcessesStopped"] = all(
                not Path(f"/proc/{pid}").exists() for pid in self.clients
            )
        self.report.update(
            calls=self.calls,
            statuses=dict(self.statuses),
            errorCodes=dict(self.errors),
            maxResponseBytes=self.max_bytes,
        )
        if self.latencies:
            ordered = sorted(self.latencies)
            self.report["latencyMs"] = {
                "median": round(statistics.median(ordered), 3),
                "p95": round(ordered[int((len(ordered) - 1) * 0.95)], 3),
                "max": round(max(ordered), 3),
            }
        self.expect(self.report["allMcpProcessesStopped"], "MCP_PROCESS_LEAK")
        self.report["accepted"] = not self.report["failureCodes"]
        self.args.output.write_text(
            json.dumps(self.report, ensure_ascii=False, indent=2) + "\n"
        )
        print(
            self.args.name,
            "accepted=" + str(self.report["accepted"]),
            "calls=" + str(self.calls),
            "summary:",
            self.args.output,
            flush=True,
        )
        return 0 if self.report["accepted"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--name", choices=("flowable", "dataflow", "spring-boot-admin"), required=True
    )
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--soak-seconds", type=int, default=90)
    args = parser.parse_args()
    if not 65 <= args.soak_seconds <= 600:
        parser.error(
            "--soak-seconds must be between 65 and 600 (cursor TTL is 60 seconds)"
        )
    return Acceptance(args).run()


if __name__ == "__main__":
    raise SystemExit(main())
