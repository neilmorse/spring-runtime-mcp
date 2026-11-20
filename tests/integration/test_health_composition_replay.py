"""Compare two ordinary tool results with one test-only health evidence frame."""

from __future__ import annotations

import asyncio
import json
from copy import deepcopy
from statistics import median
from time import perf_counter
from typing import Any

import pytest

from spring_runtime_mcp.models.common import ParsedObservation
from spring_runtime_mcp.replay import FixtureReader, services_for
from spring_runtime_mcp.server import SERVER_INFO_META
from spring_runtime_mcp.services import Services
from spring_runtime_mcp.tools.registry import call_tool
from spring_runtime_mcp.transport.response_gate import EndpointReadError
from spring_runtime_mcp.transport.responses import (
    MAX_RESPONSE_BYTES,
    serialize_response,
)

_HEALTH_TOOL = "springboot_diagnose_health"
_BEAN_TOOL = "springboot_inspect_beans"
_HEALTH_QUERY = {"componentPath": ["db"], "includeDetails": True}
_BEAN_QUERY = {"contextId": "application", "beanNamePattern": "dataSource"}
_ASSOCIATIONS = {("db",): _BEAN_QUERY}


class _ReplayReader(FixtureReader):
    def __init__(
        self, bodies: dict[str, dict[str, Any]], bean_fault: str | None
    ) -> None:
        super().__init__(bodies)
        self.bean_fault = bean_fault

    async def read(
        self, target_id: str, endpoint_id: str, *, snapshot_id: str
    ) -> ParsedObservation:
        if endpoint_id == "beans" and self.bean_fault is not None:
            self.calls.append(endpoint_id)
            if self.bean_fault == "timeout":
                raise TimeoutError
            raise EndpointReadError("ENDPOINT_UNAUTHORIZED", endpoint_id, 403)
        return await super().read(target_id, endpoint_id, snapshot_id=snapshot_id)


def _replay(case: str = "down") -> tuple[Services, _ReplayReader]:
    services = services_for("boot-3.4-servlet")
    assert isinstance(services.reader, FixtureReader)
    bodies = services.reader.bodies
    contexts = bodies["beans"]["contexts"]
    # The stock profile has the dataSource in the parent. Add a child Bean
    # for this scenario, with its dependency still resolved from the parent.
    contexts["application"]["beans"]["dataSource"] = deepcopy(
        contexts["infrastructure"]["beans"]["dataSource"]
    )
    if case == "healthy":
        bodies["health"] = {"status": "UP", "components": {"db": {"status": "UP"}}}
    if case == "hidden":
        bodies["health"] = {"status": "DOWN", "components": {"db": {"status": "DOWN"}}}
    reader = _ReplayReader(bodies, case if case in {"denied", "timeout"} else None)
    services.reader = reader
    return services, reader


async def _compose(
    services: Services, associations: dict[tuple[str, ...], dict[str, str]]
) -> dict[str, Any]:
    health = await call_tool(_HEALTH_TOOL, _HEALTH_QUERY, services)
    if health["data"] is None:
        return health

    bean_evidence = None
    for component in health["data"]["items"]:
        selector = associations.get(tuple(component["componentPath"]))
        if (
            selector is None
            or component["status"] not in {"DOWN", "OUT_OF_SERVICE"}
            or "REVIEW_HEALTH_DETAILS_VISIBILITY" in component["remediationCodes"]
        ):
            continue
        beans = await call_tool(_BEAN_TOOL, selector, services)
        rows = beans["data"]["items"] if beans["data"] is not None else None
        bean_evidence = {
            "componentPath": list(component["componentPath"]),
            "source": beans["source"],
            "coverage": beans["coverage"],
            "errors": beans["errors"],
            "items": [
                {
                    field: row[field]
                    for field in (
                        "id",
                        "endpointId",
                        "observationId",
                        "contextId",
                        "name",
                        "type",
                        "dependencies",
                        "dependents",
                    )
                }
                for row in rows
            ]
            if rows is not None
            else None,
        }
        break

    return {
        "status": "partial"
        if bean_evidence is not None
        and bean_evidence["coverage"]["state"] != "complete"
        else health["status"],
        "data": {
            "health": {
                "source": health["source"],
                "coverage": health["coverage"],
                **health["data"],
            },
            "beanEvidence": bean_evidence,
        },
    }


def _frame(result: dict[str, Any], services: Services) -> bytes:
    return serialize_response(
        result, "replay", sanitizer=services.sanitizer, server_meta=SERVER_INFO_META
    )


async def _baseline(services: Services) -> tuple[bytes, bytes]:
    health = await call_tool(_HEALTH_TOOL, _HEALTH_QUERY, services)
    health_frame = _frame(health, services)
    beans = await call_tool(_BEAN_TOOL, _BEAN_QUERY, services)
    return health_frame, _frame(beans, services)


def test_health_composition_replay() -> None:
    async def compare() -> None:
        baseline_ms = []
        combined_ms = []
        for _ in range(20):
            baseline, baseline_reader = _replay()
            combined, combined_reader = _replay()
            started = perf_counter()
            separate_frames = await _baseline(baseline)
            baseline_ms.append((perf_counter() - started) * 1000)
            started = perf_counter()
            candidate = await _compose(combined, _ASSOCIATIONS)
            candidate_frame = _frame(candidate, combined)
            combined_ms.append((perf_counter() - started) * 1000)

            assert baseline_reader.calls == combined_reader.calls == ["health", "beans"]
            assert len(separate_frames) == 2
            baseline_bytes = sum(map(len, separate_frames))
            assert len(candidate_frame) < baseline_bytes
            assert len(candidate_frame) <= MAX_RESPONSE_BYTES
            result = json.loads(candidate_frame)["result"]
            assert result["isError"] is False
            assert (
                json.loads(result["content"][0]["text"]) == result["structuredContent"]
            )
            health_result, bean_result = (
                json.loads(frame)["result"] for frame in separate_frames
            )
            assert health_result["isError"] is bean_result["isError"] is False
            baseline_health = health_result["structuredContent"]
            baseline_beans = bean_result["structuredContent"]
            health = candidate["data"]["health"]
            assert health["source"]["endpointIds"] == ["health"]
            assert health["coverage"] == baseline_health["coverage"]
            assert health["overallStatus"] == "DOWN"
            assert health["items"] == baseline_health["data"]["items"]
            assert health["items"][0]["componentPath"] == ["db"]
            assert health["items"][0]["status"] == "DOWN"
            evidence = candidate["data"]["beanEvidence"]
            assert evidence["source"]["endpointIds"] == ["beans"]
            assert evidence["coverage"] == baseline_beans["coverage"]
            assert evidence["componentPath"] == ["db"]
            (bean,) = evidence["items"]
            assert (bean["contextId"], bean["name"]) == ("application", "dataSource")
            assert (
                bean["dependencies"]
                == baseline_beans["data"]["items"][0]["dependencies"]
            )
            assert any(
                edge["targetName"] == "connectionFactory"
                and edge["targetContextId"] == "infrastructure"
                and edge["resolution"] == "resolved"
                for edge in bean["dependencies"]
            )
        print(
            f"Synthetic replay (20 samples): "
            f"baseline {baseline_bytes} bytes, median {median(baseline_ms):.2f} ms; "
            f"candidate {len(candidate_frame)} bytes, median {median(combined_ms):.2f} ms"
        )

    asyncio.run(compare())


@pytest.mark.parametrize("case", ["healthy", "hidden", "unknown-association"])
def test_health_composition_skips_unjustified_reads(case: str) -> None:
    services, reader = _replay(case)
    associations = {} if case == "unknown-association" else _ASSOCIATIONS
    candidate = asyncio.run(_compose(services, associations))

    assert reader.calls == ["health"]
    assert candidate["data"]["beanEvidence"] is None
    health = candidate["data"]["health"]
    assert health["overallStatus"] == ("UP" if case == "healthy" else "DOWN")
    if case == "hidden":
        assert "HEALTH_DETAILS_NOT_VISIBLE" in health["coverage"]["gaps"]
    _frame(candidate, services)


@pytest.mark.parametrize(
    ("case", "code", "status"),
    [("denied", "ENDPOINT_UNAUTHORIZED", 403), ("timeout", "TARGET_TIMEOUT", None)],
)
def test_health_composition_keeps_health_when_bean_read_fails(
    case: str, code: str, status: int | None
) -> None:
    services, reader = _replay(case)
    candidate = asyncio.run(_compose(services, _ASSOCIATIONS))

    assert reader.calls == ["health", "beans"]
    assert candidate["status"] == "partial"
    assert candidate["data"]["health"]["items"][0]["status"] == "DOWN"
    evidence = candidate["data"]["beanEvidence"]
    assert evidence["items"] is None
    assert evidence["coverage"]["state"] == "unavailable"
    (error,) = evidence["errors"]
    assert (error["code"], error["httpStatus"]) == (code, status)
    assert json.loads(_frame(candidate, services))["result"]["isError"] is False
