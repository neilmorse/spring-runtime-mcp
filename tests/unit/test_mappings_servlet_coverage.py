"""Regressions for non-DispatcherServlet containers in Actuator mappings."""

from __future__ import annotations

import asyncio
from typing import Any

from spring_runtime_mcp.adapters.mappings import normalize_mappings
from spring_runtime_mcp.contracts.definitions import definition
from spring_runtime_mcp.server import _valid_envelope
from spring_runtime_mcp.tools.registry import call_tool
from unit.test_rw06_architecture_regressions import services_for_bodies


def _body(*, jersey: bool = True) -> dict[str, Any]:
    mappings: dict[str, Any] = {
        "dispatcherServlets": {
            "dispatcherServlet": [
                {
                    "predicate": "{GET [/actuator/health]}",
                    "details": {
                        "requestMappingConditions": {
                            "consumes": [],
                            "headers": [],
                            "methods": ["GET"],
                            "params": [],
                            "patterns": ["/actuator/health"],
                            "produces": [],
                        }
                    },
                }
            ]
        }
    }
    if jersey:
        mappings["servlets"] = [
            {
                "mappings": ["/api/*"],
                "name": "org.apache.fineract.infrastructure.core.jersey.JerseyConfig",
                "className": "org.glassfish.jersey.servlet.ServletContainer",
            },
            {
                "mappings": ["/"],
                "name": "dispatcherServlet",
                "className": "org.springframework.web.servlet.DispatcherServlet",
            },
        ]
    return {"contexts": {"application": {"mappings": mappings}}}


def test_dispatcher_zero_is_not_absence_when_jersey_covers_path() -> None:
    items, gaps = normalize_mappings(
        _body(),
        path_pattern="/api/v1/offices",
        http_method="GET",
        controller_pattern=None,
        context_id=None,
    )
    assert items == []
    assert "NON_DISPATCHER_SERVLET_ROUTES_UNOBSERVED" in gaps


def test_tool_downgrades_jersey_path_to_partial_and_unknown_total() -> None:
    result = asyncio.run(
        call_tool(
            "springboot_verify_mappings",
            {"pathPattern": "/api/v1/offices", "httpMethod": "GET"},
            services_for_bodies({"mappings": _body()}),
        )
    )
    assert result["status"] == "partial"
    assert result["totalMatched"] is None
    assert result["coverage"]["state"] == "partial"
    assert "NON_DISPATCHER_SERVLET_ROUTES_UNOBSERVED" in result["coverage"]["gaps"]
    assert result["data"] == {"items": []}
    assert _valid_envelope(
        definition("springboot_verify_mappings")["outputSchema"], result
    )


def test_visible_dispatcher_route_is_not_downgraded_by_jersey() -> None:
    result = asyncio.run(
        call_tool(
            "springboot_verify_mappings",
            {"pathPattern": "/actuator/health", "httpMethod": "GET"},
            services_for_bodies({"mappings": _body()}),
        )
    )
    assert result["status"] == "ok"
    assert result["totalMatched"] == 1
    assert "NON_DISPATCHER_SERVLET_ROUTES_UNOBSERVED" not in result["coverage"]["gaps"]
    assert result["data"]["items"][0]["paths"] == ["/actuator/health"]


def test_zero_without_non_dispatcher_servlets_remains_complete() -> None:
    result = asyncio.run(
        call_tool(
            "springboot_verify_mappings",
            {"pathPattern": "/api/v1/offices", "httpMethod": "GET"},
            services_for_bodies({"mappings": _body(jersey=False)}),
        )
    )
    assert result["status"] == "ok"
    assert result["totalMatched"] == 0
    assert result["coverage"]["gaps"] == []
