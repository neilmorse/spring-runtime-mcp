"""Validate the published schemas and synthetic contracts without a live target."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_NAMES = [
    "springboot_analyze_startup",
    "springboot_check_migrations",
    "springboot_detect_drift",
    "springboot_diagnose_health",
    "springboot_inspect_beans",
    "springboot_inspect_config",
    "springboot_search_openapi",
    "springboot_verify_mappings",
]
VALID_INPUTS = [
    {},
    {"engine": "auto"},
    {"expectedBeans": [{"name": "orderService"}]},
    {"componentPath": ["db"]},
    {"beanNamePattern": "order*"},
    {"prefix": "spring.datasource"},
    {"pathPattern": "/orders/*"},
    {"httpMethod": "POST", "pathPattern": "/orders"},
]


def walk(value: object):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def resolve(schema: dict, pointer: str) -> dict:
    assert pointer.startswith("#/$defs/"), pointer
    value = schema
    for part in pointer[2:].split("/"):
        value = value[part.replace("~1", "/").replace("~0", "~")]
    return value


def minimal(schema: dict, root: dict):
    """Produce synthetic, minimal typed records; never claim these are Boot fixtures."""
    if "$ref" in schema:
        return minimal(resolve(root, schema["$ref"]), root)
    if "const" in schema:
        return schema["const"]
    if "enum" in schema:
        return schema["enum"][0]
    if "anyOf" in schema:
        return minimal(schema["anyOf"][0], root)
    kind = schema.get("type")
    if isinstance(kind, list):
        kind = kind[0]
    if kind == "null":
        return None
    if kind == "object":
        return {
            key: minimal(schema["properties"][key], root)
            for key in schema.get("required", [])
        }
    if kind == "array":
        return [
            minimal(schema["items"], root) for _ in range(schema.get("minItems", 0))
        ]
    if kind == "boolean":
        return False
    if kind in ("integer", "number"):
        return schema.get("minimum", 0)
    if kind == "string":
        if schema.get("format") == "date-time":
            return "2026-10-16T00:00:00Z"
        if schema.get("pattern", "").startswith("^[0-9]"):
            return "0"
        if schema.get("pattern", "").startswith("^/"):
            return "/orders"
        return "S"
    raise AssertionError(f"Unsupported synthetic sample schema: {schema}")


def rejects(validator: Draft202012Validator, value: object) -> None:
    assert not validator.is_valid(value), "Unexpectedly accepted invalid fixture"


def _validate_description_length(description: str, max_length: int = 256) -> None:
    """Validate description length for Chinese/English compatibility."""
    # Chinese characters typically take 2-3 bytes in UTF-8
    byte_length = len(description.encode("utf-8"))
    assert byte_length <= max_length, (
        f"Description too long: {byte_length} bytes (max {max_length})"
    )
    # Check for reasonable character length (heuristic)
    assert len(description) <= max_length // 2, (
        f"Description too many characters: {len(description)}"
    )


def _validate_default_in_range(schema: dict[str, Any], root: dict[str, Any]) -> None:
    """Validate defaults while retaining the containing schema's local refs."""
    if "default" not in schema:
        return
    # descend keeps the root resolver when checking this particular subschema.
    validator = Draft202012Validator(root)
    errors = list(validator.descend(schema["default"], schema))
    if errors:
        error_msgs = [f"{e.message} at {'.'.join(map(str, e.path))}" for e in errors]
        raise AssertionError(
            f"Default value {schema['default']!r} violates schema constraints: "
            + "; ".join(error_msgs)
        )


def _validate_ref_in_defs(schema: dict[str, Any], root: dict[str, Any]) -> None:
    """Validate that all $ref references are defined in $defs."""
    for node in walk(schema):
        if isinstance(node.get("$ref"), str):
            ref = node["$ref"]
            # Complete the offline reference preflight before validating defaults.
            try:
                resolve(root, ref)
            except (KeyError, AssertionError):
                raise AssertionError(
                    f"$ref {ref} must resolve within local $defs"
                ) from None


def main() -> None:
    bundle = json.loads(
        (ROOT / "src/spring_runtime_mcp/schemas/tools-contract.json").read_text()
    )
    assert bundle["contractVersion"] == "2"
    assert bundle["protocolVersion"] == "2026-07-28"
    tools = bundle["tools"]
    assert [tool["name"] for tool in tools] == sorted(EXPECTED_NAMES)
    checks = 0

    # New checks
    description_checks = 0
    default_checks = 0
    ref_checks = 0
    for tool, arguments in zip(tools, VALID_INPUTS, strict=True):
        hints = tool["annotations"]
        assert hints["title"]
        assert hints["readOnlyHint"] is True
        assert hints["idempotentHint"] is True
        assert hints["destructiveHint"] is False
        assert hints["openWorldHint"] is False

        # Validate description length
        _validate_description_length(tool["description"])
        description_checks += 1
        for key in ("inputSchema", "outputSchema"):
            schema = tool[key]
            Draft202012Validator.check_schema(schema)
            assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
            assert schema["type"] == "object"
            assert schema["additionalProperties"] is False

            # Validate all $ref references
            _validate_ref_in_defs(schema, schema)
            ref_checks += 1

            for node in walk(schema):
                if isinstance(node.get("$ref"), str):
                    resolve(schema, node["$ref"])
                if isinstance(node.get("pattern"), str):
                    re.compile(node["pattern"])

                # Validate default values in range
                if isinstance(node, dict) and "default" in node:
                    _validate_default_in_range(node, schema)
                    default_checks += 1
        iv = Draft202012Validator(tool["inputSchema"], format_checker=FormatChecker())
        ov = Draft202012Validator(tool["outputSchema"], format_checker=FormatChecker())
        iv.validate(arguments)
        for extra in (
            {"url": "http://169.254.169.254/"},
            {"headers": {}},
            {"maxResults": 51},
            {"maxResults": 0},
            {"maxResults": True},
            {"targetId": "local\n"},
        ):
            rejects(iv, {**arguments, **extra})
        checks += 7
        result = minimal(tool["outputSchema"], tool["outputSchema"])
        result["totalMatched"] = 0
        result["nextCursor"] = None
        result["source"]["snapshotId"] = "s1"
        result["source"]["endpointIds"] = []
        result["nextAction"] = {
            "kind": "done",
            "reasonCode": "COMPLETE",
            "filterSuggestions": [],
        }
        ov.validate(result)
        partial = copy.deepcopy(result)
        partial["status"] = "partial"
        partial["coverage"]["state"] = "partial"
        partial["coverage"]["gaps"] = ["ENDPOINT_NOT_VISIBLE"]
        ov.validate(partial)
        # Exercise each typed record, not just empty result arrays.
        if "items" in result["data"]:
            data_schema = tool["outputSchema"]["properties"]["data"]["anyOf"][0]
            item_schema = data_schema["properties"]["items"]["items"]
            item = minimal(item_schema, tool["outputSchema"])
            result["data"]["items"] = [item]
            result["totalMatched"] = 1
            ov.validate(result)
            if tool["name"] == "springboot_inspect_config":
                item.update(valueState="redacted", effectiveValue="[REDACTED_BY_MCP]")
                ov.validate(result)
                item["effectiveValue"] = "synthetic-secret"
                rejects(ov, result)
                item["effectiveValue"] = "[REDACTED_BY_MCP]"
            if tool["name"] == "springboot_search_openapi":
                item["schema"] = {
                    "type": "object",
                    "properties": {
                        "order": {
                            "type": "object",
                            "properties": {"customer": {"type": "string"}},
                        }
                    },
                }
                ov.validate(result)
                item["schema"] = {"$ref": "https://unregistered.invalid/schema"}
                rejects(ov, result)
                item["schema"] = {
                    "$ref": "#/components/schemas/Order",
                    "referenceState": "cycle",
                }
                ov.validate(result)
        for status in ("denied", "unavailable", "invalid", "too_large"):
            failure = copy.deepcopy(result)
            failure.update(status=status, data=None, totalMatched=None, nextCursor=None)
            failure["coverage"]["state"] = "unavailable"
            failure["errors"] = [
                minimal(
                    tool["outputSchema"]["$defs"]["DiagnosticError"],
                    tool["outputSchema"],
                )
            ]
            ov.validate(failure)
            failure["errors"] = []
            rejects(ov, failure)
            checks += 2
        invalid = copy.deepcopy(result)
        invalid["data"] = {"rawDump": "not allowed"}
        rejects(ov, invalid)
        checks += 3
    by_name = {tool["name"]: tool for tool in tools}

    def input_validator(name: str):
        return Draft202012Validator(by_name[name]["inputSchema"])

    for name in EXPECTED_NAMES[2:]:
        if name != "springboot_diagnose_health":
            rejects(input_validator(name), {})
    openapi = input_validator("springboot_search_openapi")
    rejects(openapi, {"httpMethod": "GET"})
    rejects(openapi, {"schemaName": "Order", "operationId": "findOrder"})
    rejects(openapi, {"schemaName": "Order", "maxRefDepth": 9})
    openapi.validate({"schemaName": "Order", "maxRefDepth": 2})
    drift = input_validator("springboot_detect_drift")
    rejects(drift, {"expectedBeans": [{}]})
    drift.validate({"expectedProfiles": []})
    config = input_validator("springboot_inspect_config")
    rejects(config, {"prefix": "../../env"})
    print(
        f"Validated 8 isolated input/output schemas; {checks}+ synthetic contract assertions passed."
    )
    print(
        f"Enhanced validations: {description_checks} descriptions, {default_checks} defaults, {ref_checks} $ref references."
    )


if __name__ == "__main__":
    main()
