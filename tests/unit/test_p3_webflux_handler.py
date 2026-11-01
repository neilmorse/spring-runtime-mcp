"""Synthetic handler metadata regression discovered by protected P3 WebFlux reads."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from spring_runtime_mcp.adapters.mappings import normalize_mappings
from spring_runtime_mcp.tools.registry import call_tool
from unit.test_rw06_architecture_regressions import services_for_bodies
from unit.test_webflux_predicates import mappings


@pytest.mark.parametrize("function", ["example.Function", None, {"className": 7}])
def test_legacy_or_unreadable_function_metadata_keeps_route_evidence(
    function: Any,
) -> None:
    body = mappings("(GET && /example)")
    record = body["contexts"]["application"]["mappings"]["dispatcherHandlers"][
        "webHandler"
    ][0]
    record["details"]["handlerFunction"] = function
    rows, gaps = normalize_mappings(
        body,
        path_pattern="/example",
        http_method="GET",
        controller_pattern=None,
        context_id=None,
    )
    assert not gaps and len(rows) == 1
    assert rows[0]["handlerKind"] == "function"
    assert rows[0]["controllerClass"] is None
    assert rows[0]["handlerMethod"] is None


def test_structured_method_metadata_remains_authoritative() -> None:
    body = mappings("(GET && /example)")
    record = body["contexts"]["application"]["mappings"]["dispatcherHandlers"][
        "webHandler"
    ][0]
    record["details"]["handlerMethod"] = {
        "className": "example.Controller",
        "name": "read",
        "descriptor": "()V",
    }
    rows, _ = normalize_mappings(
        body,
        path_pattern="/example",
        http_method="GET",
        controller_pattern=None,
        context_id=None,
    )
    assert rows[0]["controllerClass"] == "example.Controller"
    assert rows[0]["handlerKind"] == "method"
    assert rows[0]["handlerMethod"] == "read"


@pytest.mark.parametrize("class_filter", [None, "example.GreetingHandler"])
def test_structured_function_class_is_retained_and_can_be_filtered(
    class_filter: str | None,
) -> None:
    arguments = {"pathPattern": "/example", "httpMethod": "GET"}
    if class_filter:
        arguments["controllerClassPattern"] = class_filter
    result = asyncio.run(
        call_tool(
            "springboot_verify_mappings",
            arguments,
            services_for_bodies(
                {
                    "mappings": mappings(
                        "((GET && /example) && Accept: application/json)"
                    )
                }
            ),
        )
    )
    assert result["status"] == "ok"
    assert result["totalMatched"] == 1
    row = result["data"]["items"][0]
    assert row["controllerClass"] == "example.GreetingHandler"
    assert row["handlerKind"] == "function"
    # A function class does not prove a Java business method or its descriptor.
    assert row["handlerMethod"] is None and row["descriptor"] is None
