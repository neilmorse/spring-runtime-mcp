"""Health counts must remain unknown when component evidence is unreadable."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from spring_runtime_mcp.replay import FixtureReader, services_for
from spring_runtime_mcp.tools.registry import call_tool
from conformance.assertions import validator
from harness.host import dispatch


@pytest.mark.parametrize(
    ("components", "arguments", "expected_paths"),
    [
        ({"db": None}, {}, []),
        ({"db": None}, {"componentPath": ["db"]}, []),
        (
            {"db": None, "redis": {"status": "DOWN", "details": {"service": "redis"}}},
            {},
            [["redis"]],
        ),
        ({"x" * 129: {"status": "DOWN"}}, {}, []),
    ],
)
def test_unreadable_components_do_not_produce_a_known_total(
    components: dict[str, Any],
    arguments: dict[str, Any],
    expected_paths: list[list[str]],
) -> None:
    services = services_for("boot-3.4-servlet")
    assert isinstance(services.reader, FixtureReader)
    services.reader.bodies["health"] = {"status": "UP", "components": components}
    result = asyncio.run(call_tool("springboot_diagnose_health", arguments, services))
    validator("springboot_diagnose_health").validate(result)
    assert result["status"] == "partial"
    assert "HEALTH_COMPONENT_UNREADABLE" in result["coverage"]["gaps"]
    assert result["totalMatched"] is None
    assert [item["componentPath"] for item in result["data"]["items"]] == expected_paths


def test_readable_components_still_produce_a_known_total() -> None:
    services = services_for("boot-3.4-servlet")
    assert isinstance(services.reader, FixtureReader)
    services.reader.bodies["health"] = {
        "status": "UP",
        "components": {"db": {"status": "UP"}},
    }
    result = asyncio.run(call_tool("springboot_diagnose_health", {}, services))
    assert result["status"] == "ok"
    assert result["totalMatched"] == 0


def test_missing_component_status_makes_filtered_count_unknown() -> None:
    services = services_for("boot-3.4-servlet")
    assert isinstance(services.reader, FixtureReader)
    services.reader.bodies["health"] = {
        "status": "UP",
        "components": {"db": {"details": {"database": "H2"}}},
    }
    result = asyncio.run(call_tool("springboot_diagnose_health", {}, services))
    assert result["status"] == "partial"
    assert "HEALTH_STATUS_UNOBSERVED" in result["coverage"]["gaps"]
    assert result["data"]["items"][0]["status"] == "UNKNOWN"
    assert result["totalMatched"] is None


def test_unknown_count_survives_mcp_pagination_without_refresh() -> None:
    services = services_for("boot-3.4-servlet")
    assert isinstance(services.reader, FixtureReader)
    services.reader.bodies["health"] = {
        "status": "DOWN",
        "components": {
            "db": None,
            "redis": {"status": "DOWN", "details": {"service": "redis"}},
            "queue": {"status": "DOWN", "details": {"service": "queue"}},
        },
    }

    def page(arguments: dict[str, Any]) -> dict[str, Any]:
        frame = asyncio.run(
            dispatch(
                {
                    "jsonrpc": "2.0",
                    "id": "health-page",
                    "method": "tools/call",
                    "params": {
                        "name": "springboot_diagnose_health",
                        "arguments": arguments,
                    },
                },
                services,
            )
        )
        assert frame is not None
        assert len(frame) <= 16384
        result = json.loads(frame)["result"]
        assert result["isError"] is False
        return result["structuredContent"]

    first = page({"maxResults": 1})
    assert first["totalMatched"] is None
    assert "HEALTH_COMPONENT_UNREADABLE" in first["coverage"]["gaps"]
    assert first["nextCursor"]
    services.reader.bodies["health"] = {"status": "UP", "components": {}}
    second = page({"maxResults": 1, "cursor": first["nextCursor"]})
    assert second["totalMatched"] is None
    assert "HEALTH_COMPONENT_UNREADABLE" in second["coverage"]["gaps"]
    assert len(second["data"]["items"]) == 1
    assert second["source"]["snapshotId"] == first["source"]["snapshotId"]
