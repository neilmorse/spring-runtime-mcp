"""Synthetic regressions for the larger-project OpenAPI findings."""

import asyncio
from copy import deepcopy
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from spring_runtime_mcp.adapters.openapi import _Expander, normalize_openapi
from spring_runtime_mcp.contracts.definitions import definition
from spring_runtime_mcp.models.common import AnalysisBudget, NormalizationError
from spring_runtime_mcp.models.queries import OpenApiQuery
from spring_runtime_mcp.policy.output_guard import ensure_safe_output
from spring_runtime_mcp.policy.sanitization import SanitizerPipeline
from spring_runtime_mcp.replay import services_for
from spring_runtime_mcp.tools.registry import call_tool
from spring_runtime_mcp.transport.bounded_json import validate_tree
from spring_runtime_mcp.transport.responses import serialize_response


def project(entry: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    document = {
        "openapi": "3.1.0",
        "paths": {},
        "components": {
            "schemas": {
                "Pair": {
                    "properties": {
                        "left": {"$ref": "#/components/schemas/A~1B~0C"},
                        "right": {"$ref": "#/components/schemas/A~1B~0C"},
                    }
                },
                "A/B~C": entry,
            }
        },
    }
    before = deepcopy(document)
    _, _, items, gaps, _ = normalize_openapi(
        document, OpenApiQuery(schema_name="Pair", max_ref_depth=4)
    )
    assert gaps == [] and items[0]["expansionComplete"]
    assert document == before
    return items[0]["schema"], document


@pytest.mark.parametrize(
    "metadata",
    [
        {"required": ["id"], "properties": {"id": {"type": "integer"}}},
        {"type": ["string", "null"], "enum": ["ready", None]},
    ],
)
def test_repeated_refs_copy_metadata_and_do_not_mutate_source(metadata: dict) -> None:
    schema, document = project(metadata)
    validate_tree(schema)
    children = schema["properties"]
    left, right = children["left"], children["right"]
    for key in metadata.keys() & {"required", "type", "enum"}:
        if isinstance(metadata[key], list):
            assert left[key] == right[key] == metadata[key]
            left[key].clear()
            assert right[key] == document["components"]["schemas"]["A/B~C"][key]


@pytest.mark.parametrize(
    "name", ["description", "comments", "stackTrace", "message", "properties", "name"]
)
def test_business_field_names_preserve_schema_without_exporting_annotations(
    name: str,
) -> None:
    schema, _ = project(
        {"properties": {name: {"type": "string", "description": "untrusted prose"}}}
    )
    value = {"schema": schema}
    pipeline = SanitizerPipeline()
    clean = pipeline.sanitize(value)
    assert clean["schema"]["properties"]["left"]["properties"][name] == {
        "type": "string"
    }
    assert pipeline.sanitize(clean) == clean
    ensure_safe_output(clean)
    contract = definition("springboot_search_openapi")["outputSchema"]
    Draft202012Validator(
        {"$ref": "#/$defs/Schema", "$defs": contract["$defs"]}
    ).validate(clean["schema"])


@pytest.mark.parametrize("name", ["description", "comments", "stackTrace"])
def test_property_maps_cannot_smuggle_prose_or_credentials(name: str) -> None:
    pipeline = SanitizerPipeline()
    raw = {"properties": {name: {"description": "untrusted prose"}}}
    with pytest.raises(NormalizationError):
        ensure_safe_output(raw)
    clean = pipeline.sanitize(raw)
    ensure_safe_output(clean)
    assert "untrusted prose" not in str(clean)
    for child in ("untrusted prose", "Bearer synthetic-credential"):
        unsafe = {"properties": {name: child}}
        with pytest.raises(NormalizationError):
            ensure_safe_output(unsafe)
        assert name not in pipeline.sanitize(unsafe)["properties"]
    assert pipeline.sanitize({"properties": {"password": {"type": "string"}}}) == {
        "properties": {}
    }


def test_metadata_copy_uses_the_shared_analysis_budget() -> None:
    budget = AnalysisBudget(max_visits=2)
    expander = _Expander({}, 4, budget)
    schema, complete = expander.expand({"required": ["a", "b", "c"]}, 0, frozenset())
    assert not complete and "REF_EXPANSION_LIMIT" in expander.gaps
    assert budget.consumed_visits == 3
    validate_tree(schema)


def test_repeated_description_schemas_reach_the_full_tool_response() -> None:
    _, document = project(
        {
            "required": ["description"],
            "properties": {
                "description": {"type": ["string", "null"], "enum": ["ready", None]}
            },
        }
    )
    services = services_for("parent-child")
    services.reader.bodies["openapi"] = document
    result = asyncio.run(
        call_tool("springboot_search_openapi", {"schemaName": "Pair"}, services)
    )
    Draft202012Validator(
        definition("springboot_search_openapi")["outputSchema"]
    ).validate(result)
    assert result["status"] == "ok" and result["totalMatched"] == 1
    properties = result["data"]["items"][0]["schema"]["properties"]
    for name in ("left", "right"):
        assert properties[name]["properties"]["description"]["enum"] == ["ready", None]
    assert len(serialize_response(result, chr(0) * 128)) <= 16_384


@pytest.mark.parametrize("depth", [1, 2, 4])
def test_shared_second_order_refs_keep_cycle_and_depth_evidence(depth: int) -> None:
    document = {
        "components": {
            "schemas": {
                "Entry": {"$ref": "#/components/schemas/Node"},
                "Node": {
                    "required": ["child"],
                    "properties": {"child": {"$ref": "#/components/schemas/Entry"}},
                },
            }
        }
    }
    expander = _Expander(document, depth)
    projected, complete = expander.expand(
        {
            "properties": {
                "left": {"$ref": "#/components/schemas/Entry"},
                "right": {"$ref": "#/components/schemas/Entry"},
            }
        },
        0,
        frozenset(),
    )
    assert not complete
    assert ("REF_DEPTH_LIMIT" if depth == 1 else "REF_CYCLE") in expander.gaps
    validate_tree(projected)


@pytest.mark.parametrize(
    "entry",
    [
        {"required": [["id"]]},
        {"enum": [{"description": "untrusted prose"}]},
        {"type": ["string"] * 8},
        {"required": ["x"] * 51},
        {"enum": list(range(17))},
    ],
)
def test_invalid_or_oversized_metadata_is_omitted_as_partial(entry: dict) -> None:
    expander = _Expander({}, 4)
    schema, complete = expander.expand(entry, 0, frozenset())
    assert not complete and "OPENAPI_SCHEMA_PARTIAL" in expander.gaps
    assert not (schema.keys() & entry.keys())
    validate_tree(schema)
