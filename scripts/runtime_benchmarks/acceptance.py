"""Assert against the actual JSON-RPC lines produced by the MCP executable."""

from __future__ import annotations

import asyncio
import base64
import hmac
import json
import secrets
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from jsonschema.exceptions import ValidationError

from spring_runtime_mcp.contracts.definitions import THREAD_TOOL, definition, list_tools
from spring_runtime_mcp.models.common import NormalizationError
from spring_runtime_mcp.policy.output_guard import ensure_safe_output
from spring_runtime_mcp.server import _valid_envelope

from .targets import STATION_TOKEN_ENV, Application, BenchmarkError, database

BEANS = "springboot_inspect_beans"
MAPPINGS = "springboot_verify_mappings"
HEALTH = "springboot_diagnose_health"
STARTUP = "springboot_analyze_startup"
CONFIG = "springboot_inspect_config"
DRIFT = "springboot_detect_drift"
OPENAPI = "springboot_search_openapi"
MIGRATIONS = "springboot_check_migrations"
HEALTH_QUERY = {"componentPath": ["benchmark"], "includeBeanEvidence": True}


def require(condition: object, code: str) -> None:
    if not condition:
        raise BenchmarkError(code)


def validate_frame(name: str, wire: bytes, request_id: int) -> dict[str, Any]:
    require(len(wire) <= 16_384, "WIRE_BUDGET_EXCEEDED")
    try:
        packet = json.loads(wire)
        require(
            packet["jsonrpc"] == "2.0" and packet["id"] == request_id, "RESPONSE_ID"
        )
        result = packet["result"]
        envelope = result["structuredContent"]
        require(isinstance(envelope, dict), "RESPONSE_ENVELOPE")
        require(
            _valid_envelope(definition(name)["outputSchema"], envelope), "OUTPUT_SCHEMA"
        )
        ensure_safe_output(envelope)
        require(
            len(result["content"]) == 1
            and result["content"][0]["type"] == "text"
            and json.loads(result["content"][0]["text"]) == envelope,
            "RESPONSE_COPIES_DIFFER",
        )
        require(
            result["isError"] is (envelope["status"] not in ("ok", "partial")),
            "TOOL_ERROR_FLAG",
        )
    except (
        KeyError,
        TypeError,
        IndexError,
        ValueError,
        ValidationError,
        NormalizationError,
    ):
        raise BenchmarkError("INVALID_TOOL_FRAME") from None
    return envelope


class Session:
    def __init__(
        self, process: asyncio.subprocess.Process, report: dict[str, Any]
    ) -> None:
        self.process = process
        self.report = report
        self.request_id = 0

    async def _send(self, message: dict[str, Any]) -> None:
        stream = self.process.stdin
        if stream is None:
            raise BenchmarkError("MCP_STDIN")
        try:
            stream.write(json.dumps({"jsonrpc": "2.0", **message}).encode() + b"\n")
            await asyncio.wait_for(stream.drain(), timeout=20)
        except (OSError, TimeoutError):
            raise BenchmarkError("MCP_STDIN") from None

    async def _request(self, method: str, params: dict[str, Any]) -> bytes:
        self.request_id += 1
        await self._send({"id": self.request_id, "method": method, "params": params})
        stream = self.process.stdout
        if stream is None:
            raise BenchmarkError("MCP_STDOUT")
        try:
            line = await asyncio.wait_for(stream.readline(), timeout=25)
        except (ValueError, OSError, TimeoutError):
            raise BenchmarkError("MCP_STDOUT") from None
        require(line.endswith(b"\n"), "MCP_STDOUT")
        return line[:-1]

    async def initialize(self, *, include_threads: bool = False) -> None:
        wire = await self._request(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "runtime-benchmark", "version": "1"},
            },
        )
        try:
            reply = json.loads(wire)
            require(
                reply["id"] == self.request_id and "serverInfo" in reply["result"],
                "MCP_INITIALIZE",
            )
            await self._send({"method": "notifications/initialized"})
            tools = json.loads(await self._request("tools/list", {}))["result"]["tools"]
            require(
                [item["name"] for item in tools]
                == [
                    item["name"] for item in list_tools(include_threads=include_threads)
                ],
                "MCP_TOOL_LIST",
            )
        except (KeyError, TypeError, ValueError):
            raise BenchmarkError("MCP_INITIALIZE") from None

    async def call(
        self, label: str, tool: str, args: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        wire = await self._request(
            "tools/call", {"name": tool, "arguments": args or {}}
        )
        envelope = validate_frame(tool, wire, self.request_id)
        coverage = envelope["coverage"]
        self.report["checks"].append(
            {
                "check": label,
                "tool": tool,
                "status": envelope["status"],
                "coverage": coverage["state"],
                "gaps": coverage["gaps"],
                "errorCodes": [error["code"] for error in envelope["errors"]],
                "wireBytes": len(wire),
            }
        )
        return envelope


@asynccontextmanager
async def connect(
    application: Application, report: dict[str, Any], *options: str
) -> AsyncIterator[Session]:
    process = await asyncio.create_subprocess_exec(
        *application.exec(
            "python",
            "-m",
            "spring_runtime_mcp.cli",
            "--base-url",
            application.origin,
            *options,
        ),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
        # Inventory carries the registered tool schemas. Tool-call frames have a
        # separate 16 KiB limit checked against the bytes received.
        limit=1024 * 1024,
    )
    session = Session(process, report)
    try:
        await session.initialize(
            include_threads="--enable-thread-diagnostics" in options
        )
        yield session
    finally:
        if process.stdin is not None:
            process.stdin.close()
        try:
            await asyncio.wait_for(process.wait(), timeout=5)
        except TimeoutError:
            process.kill()
            await process.wait()


def _rows(envelope: dict[str, Any]) -> list[dict[str, Any]]:
    return (envelope["data"] or {}).get("items", [])


async def _bean(session: Session, name: str) -> dict[str, Any]:
    result = await session.call("known-bean", BEANS, {"beanNamePattern": name})
    matches = [row for row in _rows(result) if row["name"] == name]
    require(len(matches) == 1, "KNOWN_BEAN_MISSING_OR_AMBIGUOUS")
    return matches[0]


async def _route(session: Session, path: str) -> None:
    result = await session.call(
        "known-get-mapping", MAPPINGS, {"pathPattern": path, "httpMethod": "GET"}
    )
    require(any(path in row["paths"] for row in _rows(result)), "KNOWN_MAPPING_MISSING")


async def _pagination(session: Session) -> None:
    args = {"beanNamePattern": "*", "maxResults": 5, "maxDepth": 1}
    first = await session.call("bean-page-1", BEANS, args)
    cursor = first["nextCursor"]
    require(cursor is not None and len(_rows(first)) == 5, "BEAN_FIRST_PAGE")
    second = await session.call("bean-page-2", BEANS, {**args, "cursor": cursor})
    require(
        bool(_rows(second))
        and first["source"]["snapshotId"] == second["source"]["snapshotId"]
        and not {row["id"] for row in _rows(first)}.intersection(
            row["id"] for row in _rows(second)
        ),
        "BEAN_CONTINUATION",
    )


def check_health(
    result: dict[str, Any], status: str, component: str | None = None
) -> None:
    require(
        (result["data"] or {}).get("overallStatus") == status, "HEALTH_OVERALL_STATUS"
    )
    if component is not None:
        require(
            any(
                row["componentPath"] == [component] and row["status"] == status
                for row in _rows(result)
            ),
            "HEALTH_COMPONENT_STATUS",
        )


_PETCLINIC_PROPERTIES = {
    "spring.application.name": "runtime-benchmark",
    "spring.docker.compose.enabled": "false",
    "spring.devtools.restart.enabled": "false",
    "spring.h2.console.enabled": "false",
    "spring.datasource.url": "jdbc:h2:mem:runtime_benchmark;DB_CLOSE_DELAY=-1;DB_CLOSE_ON_EXIT=FALSE",
    "spring.datasource.username": "sa",
    "spring.datasource.password": "",
    "management.health.mail.enabled": "false",
    "management.otlp.metrics.export.enabled": "false",
}


async def _baseline(run: Callable[..., Any], report: dict[str, Any]) -> None:
    settings = {
        **_PETCLINIC_PROPERTIES,
        "management.endpoint.health.show-components": "always",
    }
    with run(
        "health,beans,conditions,mappings,startup,env,configprops", settings
    ) as app:
        async with connect(app, report) as session:
            await _bean(session, "ownerController")
            await _route(session, "/owners/find")
            await _pagination(session)
            health = await session.call(
                "database-up", HEALTH, {"componentPath": ["db"], "includeHealthy": True}
            )
            check_health(health, "UP", "db")
            startup = await session.call(
                "buffered-startup", STARTUP, {"minDurationMs": 1, "maxResults": 5}
            )
            require(
                bool(_rows(startup))
                and startup["data"]["springBootVersion"] == report["target"]["boot"],
                "STARTUP_TIMELINE_MISSING",
            )
            disabled = await session.call(
                "configuration-disabled",
                CONFIG,
                {"propertyKeyPattern": "spring.application.name"},
            )
            require(
                any(
                    error["code"] == "CAPABILITY_DISABLED"
                    for error in disabled["errors"]
                ),
                "CONFIG_ENABLED_BY_DEFAULT",
            )
        async with connect(
            app, report, "--config-property", "spring.application.name"
        ) as session:
            properties = await session.call(
                "configuration-masked",
                CONFIG,
                {"propertyKeyPattern": "spring.application.name"},
            )
            rows = _rows(properties)
            require(
                bool(rows)
                and all(
                    row["propertyKey"] == "spring.application.name"
                    and row["effectiveValue"] is None
                    and row["bindingValue"] is None
                    and row["valueState"] != "visible"
                    and row["bindingState"] != "visible"
                    for row in rows
                ),
                "CONFIG_MASK_OR_SCOPE",
            )


async def _drift(run: Callable[..., Any], report: dict[str, Any]) -> None:
    expectations: dict[str, Any] = {
        "expectedRoutes": [{"path": "/benchmark/registered", "httpMethod": "GET"}],
    }
    for phase in ("baseline", "fault", "recovery"):
        missing = phase == "fault"
        settings = {
            **_PETCLINIC_PROPERTIES,
            "benchmark.route.enabled": str(not missing).lower(),
        }
        with run("health,beans,conditions,mappings,startup", settings) as app:
            async with connect(app, report) as session:
                if phase == "baseline":
                    controller = await _bean(session, "benchmarkController")
                    require(
                        controller["contextId"] is not None, "DRIFT_CONTEXT_UNOBSERVED"
                    )
                    expectations["expectedBeans"] = [
                        {
                            "name": "benchmarkController",
                            "contextId": controller["contextId"],
                        }
                    ]
                result = await session.call(f"{phase}-drift", DRIFT, expectations)
                data = result["data"]
                require(data is not None, "DRIFT_UNAVAILABLE")
                differences = data["missingInRuntime"]
                require(
                    {item["dimension"] for item in differences}
                    == ({"beans", "routes"} if missing else set())
                    and len(differences) == (2 if missing else 0)
                    and all(
                        item["evidenceLevel"] == "observed" for item in differences
                    ),
                    "DRIFT_PHASE_MISMATCH",
                )
                if missing:
                    beans = await session.call(
                        "conditional-bean-missing",
                        BEANS,
                        {"beanNamePattern": "benchmarkController"},
                    )
                    require(
                        beans["data"] is not None
                        and not _rows(beans)
                        and "conditions" in beans["source"]["endpointIds"],
                        "CONDITIONAL_BEAN_NOT_INSPECTED",
                    )
                if phase == "baseline":
                    slow = await session.call(
                        "known-slow-startup-bean",
                        STARTUP,
                        {"beanNamePattern": "benchmarkSlowBean", "minDurationMs": 250},
                    )
                    require(
                        any(
                            row["name"] == "spring.beans.instantiate"
                            and row["durationMs"] is not None
                            and row["durationMs"] >= 250
                            for row in _rows(slow)
                        ),
                        "KNOWN_SLOW_STARTUP_STEP_MISSING",
                    )


def _health_binding(app: Application, context_id: str) -> tuple[str, str]:
    name = "health-binding.json"
    (app.mount / name).write_text(
        json.dumps(
            {
                "componentPath": ["benchmark"],
                "contextId": context_id,
                "beanName": "benchmarkHealthIndicator",
            }
        )
    )
    return "--health-bean-binding", f"/work/runtime/{name}"


async def _chaos(run: Callable[..., Any], report: dict[str, Any]) -> None:
    settings = {
        **_PETCLINIC_PROPERTIES,
        "spring.profiles.active": "chaos-monkey",
        "management.health.defaults.enabled": "false",
        "management.endpoint.health.show-components": "always",
        "management.endpoint.health.show-details": "always",
        "chaos.monkey.enabled": "true",
        "chaos.monkey.watcher.actuator-health": "true",
        "chaos.monkey.assaults.level": "1",
        "chaos.monkey.assaults.deterministic": "true",
        "chaos.monkey.assaults.exceptions-active": "true",
    }
    with run("health,beans", settings) as app:
        async with connect(app, report) as session:
            bean = await _bean(session, "benchmarkHealthIndicator")
        binding = _health_binding(app, bean["contextId"])
        flag = app.mount / "health-down"
        async with connect(app, report, *binding) as session:
            healthy = await session.call(
                "chaos-baseline", HEALTH, {**HEALTH_QUERY, "includeHealthy": True}
            )
            check_health(healthy, "UP", "benchmark")
            require(
                healthy["data"]["beanEvidence"]["state"] == "notApplicable",
                "HEALTHY_BEAN_EVIDENCE",
            )
            flag.touch()
            require(app.health_http() == 503, "HEALTH_HTTP_503_MISSING")
            fault = await session.call("chaos-injected", HEALTH, HEALTH_QUERY)
            check_health(fault, "DOWN", "benchmark")
            evidence = fault["data"]["beanEvidence"]
            observed = evidence["bean"] or {}
            require(
                evidence["state"] == "observed"
                and observed.get("name") == "benchmarkHealthIndicator"
                and observed.get("contextId") == bean["contextId"]
                and any(
                    edge["requestedName"] == "benchmarkDependency"
                    and edge["targetName"] == "benchmarkDependency"
                    and edge["resolution"] == "resolved"
                    for edge in observed.get("dependencies", [])
                ),
                "HEALTH_BOUND_BEAN_MISSING",
            )
            flag.unlink()
            recovered = await session.call(
                "chaos-recovered", HEALTH, {**HEALTH_QUERY, "includeHealthy": True}
            )
            check_health(recovered, "UP", "benchmark")
            require(app.health_http() == 200, "HEALTH_HTTP_RECOVERY_MISSING")
            report["observedHealthHttp"] = [503, 200]
    settings.update(
        {
            "management.endpoint.health.show-components": "never",
            "management.endpoint.health.show-details": "never",
        }
    )
    with run("health,beans", settings) as app:
        (app.mount / "health-down").touch()
        async with connect(app, report, *binding) as session:
            hidden = await session.call("chaos-component-hidden", HEALTH, HEALTH_QUERY)
            check_health(hidden, "DOWN")
            evidence = hidden["data"]["beanEvidence"]
            require(
                hidden["coverage"]["state"] in ("partial", "unavailable")
                and evidence["state"] == "unknown"
                and evidence["bean"] is None
                and evidence["source"] is None,
                "HEALTH_HIDDEN_EVIDENCE_INVENTED",
            )


async def _rest(run: Callable[..., Any], report: dict[str, Any]) -> None:
    path = "/api/owners/{ownerId}"
    settings = {
        **_PETCLINIC_PROPERTIES,
        "spring.profiles.active": "h2,spring-data-jpa",
        "springdoc.use-management-port": "true",
        "springdoc.swagger-ui.enabled": "false",
    }
    with run("health,mappings,openapi", settings) as app:
        async with connect(app, report) as session:
            await _route(session, path)
            operation = await session.call(
                "owner-openapi-operation",
                OPENAPI,
                {"pathPattern": path, "httpMethod": "GET"},
            )
            require(
                any(
                    row["path"] == path and row["httpMethod"] == "GET"
                    for row in _rows(operation)
                ),
                "OPENAPI_OPERATION_MISSING",
            )
            schema = await session.call(
                "owner-openapi-schema",
                OPENAPI,
                {"schemaName": "Owner", "maxRefDepth": 2},
            )
            require(
                any(
                    row["schemaName"] == "Owner"
                    and {"firstName", "lastName"}.issubset(
                        (row["schema"] or {}).get("properties", {})
                    )
                    for row in _rows(schema)
                ),
                "OPENAPI_OWNER_FIELDS_MISSING",
            )


async def _wait_health(session: Session, label: str, status: str) -> None:
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        result = await session.call(
            label, HEALTH, {"componentPath": ["db"], "includeHealthy": True}
        )
        if (result["data"] or {}).get("overallStatus") == status:
            check_health(result, status, "db")
            return
        await asyncio.sleep(1)
    raise BenchmarkError("DATABASE_HEALTH_TRANSITION_MISSING")


async def _train(run: Callable[..., Any], report: dict[str, Any]) -> None:
    settings = {
        "spring.cloud.nacos.discovery.enabled": "false",
        "spring.cloud.service-registry.auto-registration.enabled": "false",
        "spring.datasource.url": "jdbc:mysql://station-db:3306/station?connectTimeout=1500&socketTimeout=2500",
        "spring.datasource.username": "station",
        "spring.datasource.hikari.connection-timeout": "1500",
        "spring.datasource.hikari.validation-timeout": "1000",
        "management.endpoint.health.show-components": "always",
    }
    key = secrets.token_bytes(64)
    token = _station_token(key)
    with (
        TemporaryDirectory(prefix="spring-mcp-management-tls-") as tls_directory,
        database() as db,
        run(
            "health,beans,mappings",
            settings,
            network=db.network,
            management_tls=Path(tls_directory),
            private_environment={
                "STATION_MYSQL_PASSWORD": db.password,
                "BENCHMARK_STATION_JWT_KEY": base64.b64encode(key).decode("ascii"),
                STATION_TOKEN_ENV: token,
            },
        ) as app,
    ):
        async with connect(app, report) as session:
            denied = await session.call(
                "anonymous-management-denied", BEANS, {"beanNamePattern": "*"}
            )
            require(
                denied["status"] == "denied"
                and any(
                    error["code"] == "ENDPOINT_UNAUTHORIZED"
                    for error in denied["errors"]
                ),
                "TRAINTICKET_ANONYMOUS_ACCESS",
            )
        async with connect(app, report, "--token-env", STATION_TOKEN_ENV) as session:
            await _route(session, "/api/v1/stationservice/stations")
            await _pagination(session)
            await _wait_health(session, "database-baseline", "UP")
            db.stop()
            await _wait_health(session, "database-stopped", "DOWN")
            require(app.health_http() == 503, "DATABASE_HTTP_503_MISSING")
            db.start()
            await _wait_health(session, "database-restored", "UP")


def _station_token(key: bytes) -> str:
    header = {"typ": "JWT", "alg": "HS512"}
    claims = {
        "sub": "benchmark-reader",
        "exp": int(time.time()) + 900,
        "roles": ["ROLE_USER"],
    }
    segments = [
        base64.urlsafe_b64encode(json.dumps(value).encode("utf-8")).rstrip(b"=")
        for value in (header, claims)
    ]
    signed = b".".join(segments)
    signature = base64.urlsafe_b64encode(hmac.digest(key, signed, "sha512")).rstrip(
        b"="
    )
    return (signed + b"." + signature).decode("ascii")


async def _webgoat(run: Callable[..., Any], report: dict[str, Any]) -> None:
    settings = {"webgoat.host": "127.0.0.1", "webwolf.host": "127.0.0.1"}
    with run("health,mappings,flyway", settings, webgoat=True) as app:
        async with connect(app, report) as session:
            await _route(session, "/login")
            migrations = await session.call(
                "webgoat-flyway", MIGRATIONS, {"engine": "flyway"}
            )
            require(
                any(row["state"] == "APPLIED" for row in _rows(migrations)),
                "WEBGOAT_FLYWAY_MISSING",
            )


async def _vulnerable(run: Callable[..., Any], report: dict[str, Any]) -> None:
    with run(
        "health,beans,mappings", {"management.health.mail.enabled": "false"}
    ) as app:
        async with connect(app, report) as session:
            check_health(await session.call("vulnerableapp-health", HEALTH), "UP")
            await _bean(session, "dispatcherServlet")
            mappings = await session.call(
                "vulnerableapp-mvc-mappings",
                MAPPINGS,
                {"controllerClassPattern": "org.sasanlabs.*", "maxResults": 10},
            )
            require(
                any(row["controllerClass"] and row["paths"] for row in _rows(mappings)),
                "VULNERABLEAPP_MAPPINGS_MISSING",
            )


async def _wait_for_fixture_file(path: Path) -> None:
    deadline = time.monotonic() + 30
    while not path.is_file():
        require(time.monotonic() < deadline, "THREAD_FIXTURE_TIMEOUT")
        await asyncio.sleep(0.05)


def _thread_requests(directory: Path) -> list[str]:
    return [
        line
        for log in sorted((directory / "tomcat/logs").glob("thread-access*.log"))
        for line in log.read_text(encoding="ascii").splitlines()
        if " /actuator/threaddump " in line
    ]


async def _check_thread_requests(directory: Path, count: int) -> None:
    deadline = time.monotonic() + 5
    while len(_thread_requests(directory)) < count and time.monotonic() < deadline:
        await asyncio.sleep(0.05)
    require(
        _thread_requests(directory) == ["GET /actuator/threaddump 200"] * count,
        "THREAD_FIXTURE_GET_COUNT",
    )


async def _threads(run: Callable[..., Any], report: dict[str, Any]) -> None:
    report["threadScenarios"] = []
    for mode in ("blocked", "deadlock", "timed"):
        settings = {
            "benchmark.thread.mode": mode,
            "management.endpoints.web.discovery.enabled": "false",
            "server.tomcat.basedir": f"/work/runtime/{mode}/tomcat",
            "server.tomcat.accesslog.enabled": "true",
            "server.tomcat.accesslog.buffered": "false",
            "server.tomcat.accesslog.prefix": "thread-access",
            "server.tomcat.accesslog.pattern": "%m %U %s",
        }
        with run("health,threaddump", settings, shared_management=True) as app:
            directory = app.mount / mode
            directory.mkdir(exist_ok=True)
            async with connect(app, report, "--enable-thread-diagnostics") as session:
                require(not _thread_requests(directory), "THREAD_READ_DURING_DISCOVERY")
                (directory / "start").touch()
                oracle_file = directory / "oracle.json"
                await _wait_for_fixture_file(oracle_file)
                oracle = json.loads(oracle_file.read_text())
                require(
                    oracle["bootVersion"] == report["target"]["boot"],
                    "THREAD_BOOT_VERSION",
                )
                ids = [str(oracle["waiterId"]), str(oracle["ownerId"])]
                jvm_deadlocked = {str(value) for value in oracle["deadlockedIds"]}
                expected_states = {
                    "blocked": ["BLOCKED", "WAITING"],
                    "deadlock": ["BLOCKED", "BLOCKED"],
                    "timed": ["TIMED_WAITING", "TIMED_WAITING"],
                }
                require(
                    [oracle["waiterState"], oracle["ownerState"]]
                    == expected_states[mode],
                    "THREAD_FIXTURE_STATES",
                )
                query = {"maxResults": 1} if mode == "deadlock" else {}
                first = await session.call(f"{mode}-initial", THREAD_TOOL, query)
                require(first["status"] in {"ok", "partial"}, "THREAD_DIAGNOSIS_FAILED")
                require(
                    first["source"]["endpointIds"] == ["threaddump"], "THREAD_SOURCE"
                )
                counts = {
                    row["state"]: row["count"] for row in first["data"]["stateCounts"]
                }
                require(
                    all(
                        counts.get(state, 0) >= expected_states[mode].count(state)
                        for state in expected_states[mode]
                    ),
                    "THREAD_STATE_COUNTS",
                )
                if mode == "blocked":
                    require(
                        not jvm_deadlocked
                        and first["data"]["waitCycleStatus"] == "noneObserved"
                        and any(
                            item["kind"] == "chain"
                            and item["threadIds"] == ids
                            and item["end"] == "endOfObservedChain"
                            for item in _rows(first)
                        ),
                        "THREAD_BLOCKED_CHAIN",
                    )
                else:
                    require(
                        first["data"]["waitCycleStatus"] == "observed"
                        and any(
                            item["kind"] == "cycle"
                            and set(item["threadIds"]) == set(ids)
                            and item["length"] == 2
                            and item["containsTimedWait"] == (mode == "timed")
                            for item in _rows(first)
                        ),
                        "THREAD_WAIT_CYCLE",
                    )
                if mode == "deadlock":
                    require(jvm_deadlocked == set(ids), "THREAD_JVM_DEADLOCK_MISMATCH")
                    cursor = first["nextCursor"]
                    require(isinstance(cursor, str) and cursor, "THREAD_CURSOR_MISSING")
                    next_page = await session.call(
                        "deadlock-next-page", THREAD_TOOL, {**query, "cursor": cursor}
                    )
                    require(
                        next_page["source"] == first["source"]
                        and next_page["totalMatched"] == first["totalMatched"]
                        and any(item["kind"] == "chain" for item in _rows(next_page)),
                        "THREAD_CURSOR_SNAPSHOT",
                    )
                await _check_thread_requests(directory, 1)
                scenario = {
                    "scenario": mode,
                    "workerStates": expected_states[mode],
                    "jvmDeadlockDetected": bool(jvm_deadlocked),
                    "waitCycleStatus": first["data"]["waitCycleStatus"],
                    "observedWaitCycles": first["data"]["waitCycleCount"],
                    "containsTimedWait": mode == "timed",
                    "initialAndContinuationGets": 1,
                }
                if mode == "timed":
                    await _wait_for_fixture_file(directory / "recovered")
                    recovered = await session.call("timed-recovered", THREAD_TOOL)
                    require(
                        recovered["status"] in {"ok", "partial"}
                        and recovered["source"] != first["source"]
                        and recovered["data"]["waitCycleStatus"] == "noneObserved"
                        and recovered["data"]["waitCycleCount"] == 0,
                        "THREAD_TIMED_WAIT_RECOVERY",
                    )
                    await _check_thread_requests(directory, 2)
                    scenario["recovery"] = {
                        "waitCycleStatus": "noneObserved",
                        "freshGets": 1,
                    }
                report["threadScenarios"].append(scenario)


CASES = {
    "jvm-threads": _threads,
    "petclinic": _baseline,
    "petclinic-drift": _drift,
    "petclinic-chaos": _chaos,
    "petclinic-rest": _rest,
    "trainticket-db": _train,
    "webgoat": _webgoat,
    "vulnerableapp": _vulnerable,
}
