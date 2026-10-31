"""Synthetic grammar regressions for real WebFlux functional route shapes."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from spring_runtime_mcp.adapters.mappings import _parse_predicate
from spring_runtime_mcp.contracts.definitions import definition
from spring_runtime_mcp.server import _valid_envelope
from spring_runtime_mcp.tools.registry import call_tool
from unit.test_rw06_architecture_regressions import services_for_bodies


def mappings(predicate: str) -> dict[str, Any]:
    return {
        "contexts": {
            "application": {
                "mappings": {
                    "dispatcherHandlers": {
                        "webHandler": [
                            {
                                "handler": "example.GreetingHandler",
                                "predicate": predicate,
                                "details": {
                                    "handlerFunction": {
                                        "className": "example.GreetingHandler"
                                    }
                                },
                            }
                        ]
                    }
                }
            }
        }
    }


@pytest.mark.parametrize(
    "predicate",
    [
        "((GET && /example) && produces [application/json])",
        "(GET && /example && Accept: application/json)",
        "((GET && /example) && Accept: application/json)",
        "(((GET && /example)) && (Accept: application/json))",
    ],
)
def test_functional_route_survives_nested_groups_and_media_conditions(
    predicate: str,
) -> None:
    result = asyncio.run(
        call_tool(
            "springboot_verify_mappings",
            {"pathPattern": "/example", "httpMethod": "GET"},
            services_for_bodies({"mappings": mappings(predicate)}),
        )
    )
    assert result["status"] == "ok"
    assert result["totalMatched"] == 1
    row = result["data"]["items"][0]
    assert row["paths"] == ["/example"]
    assert row["httpMethods"] == ["GET"]
    assert row["methodsUnrestricted"] is False
    assert row["handlerKind"] == "function" and row["matchingComplete"] is True
    assert row["conditions"]
    assert _valid_envelope(
        definition("springboot_verify_mappings")["outputSchema"], result
    )


@pytest.mark.parametrize(
    "condition,name,value",
    [
        ("Accept: application/json", "Accept", "application/json"),
        (
            "Accept: [application/json, text/plain]",
            "Accept",
            "application/json,text/plain",
        ),
        ("Content-Type: application/json", "Content-Type", "application/json"),
        (
            "Content-Type: [application/json, application/*+json]",
            "Content-Type",
            "application/json,application/*+json",
        ),
        (
            "Accept: application/json;charset=UTF-8",
            "Accept",
            "application/json;charset=UTF-8",
        ),
    ],
)
def test_media_alternatives_remain_one_header_constraint(
    condition: str, name: str, value: str
) -> None:
    paths, methods, conditions, complete = _parse_predicate(
        "((GET && /example) && " + condition + ")"
    )
    assert complete and paths == ["/example"] and methods == ["GET"]
    assert conditions == [
        {"kind": "header", "name": name, "value": value, "negated": False}
    ]


def test_method_sets_intersect_across_conjunctions() -> None:
    paths, methods, _, complete = _parse_predicate("(([GET, POST] && /example) && GET)")
    assert complete and methods == ["GET"] and paths == ["/example"]


def test_path_regex_comma_is_not_a_clause_separator() -> None:
    path = "/orders/{id:[0-9]{1,3}}"
    paths, methods, _, complete = _parse_predicate("(GET && " + path + ")")
    assert complete and paths == [path] and methods == ["GET"]


@pytest.mark.parametrize(
    "predicate",
    [
        "((GET && /a) || (POST && /b))",
        "(GET /a || POST /b)",
        "!(GET && /a)",
        "(GET && !/a)",
        "((GET && /a) && customPredicate)",
        "(GET && /a) trailing",
        "(GET && /a",
        "GET && /a)",
        "(GET && && /a)",
        "(GET && /a &&)",
        "{GET [/a],}",
        "(GET && /a && Accept: [application/json,])",
        "(GET && /a && Accept: [application/json)",
        '(GET && /a && Accept: application/json;profile="a,b")',
        "(GET && /a && /b)",
        "(GET && POST && /a)",
        "(GET && /a\n)",
        "GET Accept: application/json",
        "GET produces [application/json]",
        "GET",
        "Accept: application/json",
    ],
)
def test_unsupported_or_malformed_predicates_never_form_route_combinations(
    predicate: str,
) -> None:
    result = asyncio.run(
        call_tool(
            "springboot_verify_mappings",
            {"pathPattern": "/a", "httpMethod": "GET"},
            services_for_bodies({"mappings": mappings(predicate)}),
        )
    )
    assert result["status"] == "partial" and result["totalMatched"] is None
    assert result["data"]["items"] == []
    assert "MAPPING_PREDICATE_UNPARSED" in result["coverage"]["gaps"]


def test_predicate_depth_and_clause_budgets() -> None:
    assert _parse_predicate("(" * 16 + "GET /example" + ")" * 16)[3]
    assert not _parse_predicate("(" * 17 + "GET /example" + ")" * 17)[3]
    assert _parse_predicate(" && ".join(["GET"] * 31 + ["/example"]))[3]
    assert not _parse_predicate(" && ".join(["GET"] * 33 + ["/example"]))[3]
    assert not _parse_predicate("GET /" + "a" * 4096)[3]


def test_drift_can_prove_a_missing_route_after_parsing_the_visible_route() -> None:
    result = asyncio.run(
        call_tool(
            "springboot_detect_drift",
            {"expectedRoutes": [{"path": "/absent", "httpMethod": "GET"}]},
            services_for_bodies(
                {
                    "mappings": mappings(
                        "((GET && /example) && Accept: application/json)"
                    )
                }
            ),
        )
    )
    assert result["status"] == "ok" and result["totalMatched"] == 1
    missing = result["data"]["missingInRuntime"]
    assert len(missing) == 1 and missing[0]["actual"] == "absent"
    assert _valid_envelope(
        definition("springboot_detect_drift")["outputSchema"], result
    )
