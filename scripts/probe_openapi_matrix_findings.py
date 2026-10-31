"""Offline synthetic reproductions of two project-matrix OpenAPI defects.

Not a default pytest test or a real-target reader. Exit 1 while either expected
tree/schema property is violated; export only boolean facts and fixed codes.
"""

from __future__ import annotations

import json

from spring_runtime_mcp.adapters.openapi import normalize_openapi
from spring_runtime_mcp.models.common import NormalizationError
from spring_runtime_mcp.models.queries import OpenApiQuery
from spring_runtime_mcp.policy.sanitization import SanitizerPipeline
from spring_runtime_mcp.transport.bounded_json import validate_tree


def project(schemas: dict[str, object], name: str) -> dict[str, object]:
    document = {"openapi": "3.1.0", "paths": {}, "components": {"schemas": schemas}}
    _, _, items, _, _ = normalize_openapi(document, OpenApiQuery(schema_name=name))
    return {"data": {"items": items}}


def main() -> int:
    shared = project(
        {
            "Pair": {
                "type": "object",
                "properties": {
                    "left": {"$ref": "#/components/schemas/Entry"},
                    "right": {"$ref": "#/components/schemas/Entry"},
                },
            },
            "Entry": {
                "type": "object",
                "required": ["id"],
                "properties": {"id": {"type": "integer"}},
            },
        },
        "Pair",
    )
    error = None
    try:
        validate_tree(shared)
    except NormalizationError as exc:
        error = exc.code
    collision = project(
        {
            "Details": {
                "type": "object",
                "properties": {"description": {"type": "string"}},
            }
        },
        "Details",
    )
    clean = SanitizerPipeline().sanitize(collision)
    retained = isinstance(
        clean["data"]["items"][0]["schema"]["properties"].get("description"), dict
    )
    print(
        json.dumps(
            {
                "sharedReferenceOutputIsTree": error is None,
                "sharedReferenceErrorCode": error,
                "descriptionPropertySchemaRetained": retained,
            }
        )
    )
    return 1 if error or not retained else 0


if __name__ == "__main__":
    raise SystemExit(main())
