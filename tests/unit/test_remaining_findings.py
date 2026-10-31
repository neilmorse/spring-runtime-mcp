"""Synthetic regressions for the five unresolved review findings."""

import asyncio
from copy import deepcopy

import pytest

from conformance.assertions import validator
from spring_runtime_mcp.adapters.openapi import _Expander, _path_item
from spring_runtime_mcp.contracts.definitions import validate_arguments
from spring_runtime_mcp.models.common import AnalysisBudget, NormalizationError
from spring_runtime_mcp.replay import services_for
from spring_runtime_mcp.server import _is_rfc3339
from spring_runtime_mcp.tools.registry import call_tool


def invoke(body: dict, arguments: dict) -> dict:
    original = deepcopy(body)
    services = services_for("parent-child")
    services.reader.bodies["openapi"] = body
    result = asyncio.run(call_tool("springboot_search_openapi", arguments, services))
    validator("springboot_search_openapi").validate(result)
    assert body == original
    return result


def document(paths: dict | None = None, schemas: dict | None = None) -> dict:
    return {
        "openapi": "3.1.0",
        "paths": paths or {},
        "components": {"schemas": schemas or {}},
    }


def operation() -> dict:
    return {"responses": {"200": {"description": "omitted"}}}


def test_path_item_keeps_disjoint_operations_across_two_refs() -> None:
    body = document(
        {"/orders": {"$ref": "#/components/pathItems/First", "post": operation()}}
    )
    body["components"]["pathItems"] = {
        "First": {"$ref": "#/components/pathItems/A~1B", "head": operation()},
        "A/B": {"get": operation()},
    }
    result = invoke(body, {"pathPattern": "/orders"})
    assert result["status"] == "ok" and result["totalMatched"] == 3
    assert {r["httpMethod"] for r in result["data"]["items"]} == {"GET", "POST", "HEAD"}


def test_path_item_conflict_is_unknown_without_losing_other_operations() -> None:
    body = document(
        {
            "/orders": {
                "$ref": "#/components/pathItems/Base",
                "get": operation(),
                "post": operation(),
            }
        }
    )
    body["components"]["pathItems"] = {"Base": {"get": operation()}}
    result = invoke(body, {"pathPattern": "/orders"})
    assert result["status"] == "partial" and result["totalMatched"] is None
    assert [r["httpMethod"] for r in result["data"]["items"]] == ["POST"]
    assert "OPENAPI_PATH_FIELD_CONFLICT" in result["coverage"]["gaps"]


@pytest.mark.parametrize(
    "value",
    [
        {"$ref": "#/missing"},
        {"$ref": "https://example.test/schema"},
        None,
        {"get": None},
    ],
)
def test_unreadable_path_cannot_prove_zero_operations(value: object) -> None:
    result = invoke(document({"/orders": value}), {"pathPattern": "/orders"})
    assert result["status"] == "partial" and result["totalMatched"] is None


def test_unmatched_path_is_still_a_complete_zero() -> None:
    result = invoke(
        document({"/orders": {"$ref": "#/missing"}}), {"pathPattern": "/other"}
    )
    assert result["status"] == "ok" and result["totalMatched"] == 0


def test_schema_depth_limit_does_not_destroy_a_known_operation_count() -> None:
    op = operation()
    op["responses"]["200"]["content"] = {
        "application/json": {"schema": {"$ref": "#/components/schemas/Item"}}
    }
    result = invoke(
        document({"/orders": {"get": op}}, {"Item": {"type": "string"}}),
        {"pathPattern": "/orders", "maxRefDepth": 0},
    )
    assert result["status"] == "partial" and result["totalMatched"] == 1


@pytest.mark.parametrize(
    "keyword", ["properties", "items", "additionalProperties", "allOf"]
)
def test_inline_subschemas_inherit_root_dialect(keyword: str) -> None:
    child = {"type": "string"}
    value = (
        {"child": child}
        if keyword == "properties"
        else [child]
        if keyword == "allOf"
        else child
    )
    body = document(
        schemas={
            "Root": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                keyword: value,
            }
        }
    )
    body["jsonSchemaDialect"] = "https://example.test/unknown-dialect"
    result = invoke(body, {"schemaName": "Root"})
    assert result["status"] == "ok" and result["data"]["items"][0]["expansionComplete"]


def test_refs_use_target_lexical_dialect_not_the_callers_dialect() -> None:
    body = document(
        schemas={
            "Root": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$ref": "#/components/schemas/Other",
            },
            "Other": {"type": "string"},
        }
    )
    body["jsonSchemaDialect"] = "https://example.test/unknown-dialect"
    result = invoke(body, {"schemaName": "Root"})
    assert result["status"] == "partial"
    assert "OPENAPI_SCHEMA_DIALECT_UNSUPPORTED" in result["coverage"]["gaps"]


def test_shared_ref_into_defs_inherits_its_resource_dialect() -> None:
    body = document(
        schemas={
            "Root": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$defs": {"A/B~C": {"type": "string"}},
                "properties": {
                    "left": {"$ref": "#/components/schemas/Root/$defs/A~1B~0C"},
                    "right": {"$ref": "#/components/schemas/Root/$defs/A~1B~0C"},
                },
            },
        }
    )
    body["jsonSchemaDialect"] = "https://example.test/unknown-dialect"
    result = invoke(body, {"schemaName": "Root"})
    assert result["status"] == "ok"
    for child in result["data"]["items"][0]["schema"]["properties"].values():
        assert child["type"] == "string" and child["referenceState"] == "resolved"


@pytest.mark.parametrize(
    "value",
    [
        "20261022T010000+00:00",
        "2026-W43-4T01:00:00Z",
        "2026-10-22T01:00:00+00:00:30",
        "2026-10-22 01:00:00Z",
        "2026-02-30T01:00:00Z",
        "2026-10-22T01:00:00+00:99",
        "2026-10-22T01:00:00",
        "2026-10-22T01:00:60Z",
    ],
)
def test_non_rfc3339_is_rejected_at_input_and_output(value: str) -> None:
    with pytest.raises(NormalizationError):
        validate_arguments(
            {"expectedBeans": [{"name": "service"}], "sourceModifiedAt": value},
            "springboot_detect_drift",
        )
    assert not _is_rfc3339(value)


@pytest.mark.parametrize(
    "value",
    [
        "2026-10-22t01:00:00z",
        "2016-12-31T23:59:60Z",
        "2017-01-01T00:59:60+01:00",
        "2026-10-22T01:00:00.123456789Z",
    ],
)
def test_valid_rfc3339_is_supported_consistently(value: str) -> None:
    validate_arguments(
        {"expectedBeans": [{"name": "service"}], "sourceModifiedAt": value},
        "springboot_detect_drift",
    )
    assert _is_rfc3339(value)


@pytest.mark.parametrize(
    "started", [None, 123, "not-a-timestamp", "2026-10-22T00:00:00", "20261022T000000Z"]
)
def test_drift_invalid_start_time_is_partial(started: object) -> None:
    services = services_for("parent-child")
    services.reader.bodies["startup"] = {
        "timeline": {"startTime": started, "events": []}
    }
    result = asyncio.run(
        call_tool(
            "springboot_detect_drift",
            {
                "expectedBeans": [{"name": "orderService"}],
                "sourceModifiedAt": "2026-10-22T01:00:00Z",
            },
            services,
        )
    )
    validator("springboot_detect_drift").validate(result)
    assert result["status"] == "partial" and result["totalMatched"] is None
    assert "STARTUP_TIMING_UNOBSERVED" in result["coverage"]["gaps"]


def test_time_order_keeps_nanoseconds_and_leap_second_order() -> None:
    from spring_runtime_mcp.tools.detect_drift import _later

    assert _later("2026-10-22T00:00:00.000000002Z", "2026-10-22T00:00:00.000000001Z")
    assert _later("2017-01-01T00:00:00Z", "2016-12-31T23:59:60.5Z")
    assert _later("2016-12-31T23:59:60Z", "2016-12-31T23:59:59.9Z")


def test_dialect_cache_does_not_inherit_an_unrelated_caller() -> None:
    body = document(schemas={"Target": {"type": "string"}})
    expander = _Expander(body, 4)
    projected, complete = expander.expand(
        {"$ref": "#/components/schemas/Target"}, 0, frozenset()
    )
    assert complete and projected["type"] == "string"


def test_reference_to_subschema_cannot_escape_an_invalid_resource_dialect() -> None:
    body = document(
        schemas={
            "Root": {"$schema": None, "$defs": {"Child": {"type": "string"}}},
            "Entry": {"$ref": "#/components/schemas/Root/$defs/Child"},
        }
    )
    result = invoke(body, {"schemaName": "Entry"})
    assert result["status"] == "partial"
    assert "OPENAPI_SCHEMA_DIALECT_UNSUPPORTED" in result["coverage"]["gaps"]


def test_ref_into_a_resource_cannot_ignore_its_unsupported_base_uri() -> None:
    body = document(
        schemas={
            "Root": {
                "$id": "https://example.test/other-resource",
                "$defs": {"Child": {"$ref": "#/components/schemas/Other"}},
            },
            "Other": {"type": "string"},
            "Entry": {"$ref": "#/components/schemas/Root/$defs/Child"},
        }
    )
    result = invoke(body, {"schemaName": "Entry"})
    assert result["status"] == "partial"
    assert "OPENAPI_SCHEMA_BASE_UNSUPPORTED" in result["coverage"]["gaps"]


def test_invalid_path_name_does_not_prove_zero_operations() -> None:
    result = invoke(
        document({"missing-slash": {"get": operation()}}), {"pathPattern": "*"}
    )
    assert result["status"] == "partial" and result["totalMatched"] is None


def test_path_item_cycle_is_visible_and_never_a_complete_zero() -> None:
    body = document({"/orders": {"$ref": "#/paths/~1orders"}})
    result = invoke(body, {"pathPattern": "/orders"})
    assert result["status"] == "partial" and result["totalMatched"] is None
    assert "REF_CYCLE" in result["coverage"]["gaps"]


def test_path_item_fields_share_the_query_budget() -> None:
    budget = AnalysisBudget(max_visits=1)
    expander = _Expander({}, 4, budget)
    _path_item({"get": operation(), "post": operation()}, expander)
    assert budget.consumed_visits == 2
    assert {"REF_EXPANSION_LIMIT", "OPENAPI_PATH_UNREADABLE"} <= expander.gaps


def test_wrapper_refs_cannot_trigger_unbounded_pointer_scope_scanning() -> None:
    expander = _Expander({}, 4, AnalysisBudget(max_visits=1))
    assert expander.target("#/" + "/x" * 1000) is None
    assert "REF_INVALID" in expander.gaps
    assert expander.budget.consumed_visits == 0


@pytest.mark.parametrize("start", [123, None, "20261022T000000Z"])
def test_invalid_timeline_start_cannot_be_replaced_by_an_event_time(
    start: object,
) -> None:
    services = services_for("parent-child")
    services.reader.bodies["startup"] = {
        "timeline": {
            "startTime": start,
            "events": [
                {
                    "startTime": "2026-10-22T00:00:00Z",
                    "endTime": "2026-10-22T00:00:01Z",
                    "duration": "PT1S",
                    "startupStep": {
                        "id": 1,
                        "name": "spring.test",
                        "parentId": None,
                        "tags": [],
                    },
                }
            ],
        }
    }
    result = asyncio.run(call_tool("springboot_analyze_startup", {}, services))
    validator("springboot_analyze_startup").validate(result)
    assert result["data"]["totalDurationMs"] is None
    assert "STARTUP_TIMING_UNOBSERVED" in result["coverage"]["gaps"]


@pytest.mark.parametrize(
    "start,end,expected_span",
    [
        ("2026-10-22t00:00:00z", "2026-10-22t00:00:01z", 1000),
        ("2016-12-31T23:59:60Z", "2017-01-01T00:00:00Z", None),
    ],
)
def test_startup_uses_the_same_format_rules_and_keeps_leap_spans_unknown(
    start: str, end: str, expected_span: int | None
) -> None:
    services = services_for("parent-child")
    services.reader.bodies["startup"] = {
        "timeline": {
            "startTime": start,
            "events": [
                {
                    "startTime": start,
                    "endTime": end,
                    "duration": "PT1S",
                    "startupStep": {
                        "id": 1,
                        "name": "spring.test",
                        "parentId": None,
                        "tags": [],
                    },
                }
            ],
        }
    }
    result = asyncio.run(call_tool("springboot_analyze_startup", {}, services))
    validator("springboot_analyze_startup").validate(result)
    assert result["data"]["items"][0]["startedAt"] == start
    assert result["data"]["totalDurationMs"] == expected_span
