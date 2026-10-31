"""Offline synthetic investigation; exit 1 while review defects reproduce."""

from __future__ import annotations

import asyncio
import json

from spring_runtime_mcp.contracts.definitions import validate_arguments
from spring_runtime_mcp.models.common import NormalizationError
from spring_runtime_mcp.replay import services_for
from spring_runtime_mcp.server import _is_rfc3339
from spring_runtime_mcp.tools.registry import call_tool


def document() -> dict:
    return {"openapi": "3.1.0", "paths": {}, "components": {"schemas": {}}}


def query_openapi(body: dict, arguments: dict) -> dict:
    services = services_for("parent-child")
    services.reader.bodies["openapi"] = body
    return asyncio.run(call_tool("springboot_search_openapi", arguments, services))


def main() -> int:
    body = document()
    body["components"]["pathItems"] = {
        "Shared": {"get": {"responses": {"200": {"description": "omitted"}}}}
    }
    body["paths"]["/orders"] = {
        "$ref": "#/components/pathItems/Shared",
        "post": {"responses": {"201": {"description": "omitted"}}},
    }
    siblings = query_openapi(body, {"pathPattern": "/orders"})

    services = services_for("parent-child")
    services.reader.bodies["beans"] = {
        "contexts": {
            "application": {
                "beans": {
                    "service": {
                        "type": "example.Service",
                        "scope": "singleton",
                        "aliases": [],
                        "dependencies": [],
                    }
                }
            }
        }
    }
    services.reader.bodies["startup"] = {
        "timeline": {"startTime": "not-a-timestamp", "events": []}
    }
    drift = asyncio.run(
        call_tool(
            "springboot_detect_drift",
            {
                "sourceModifiedAt": "2026-10-22T01:00:00Z",
                "expectedBeans": [{"name": "service"}],
            },
            services,
        )
    )

    formats = {}
    for name, value in (
        ("basicDate", "20261022T010000+00:00"),
        ("weekDate", "2026-W43-4T01:00:00+00:00"),
        ("offsetSeconds", "2026-10-22T01:00:00+00:00:30"),
        ("validLowercaseZ", "2026-10-22t01:00:00z"),
        ("validLeapSecond", "2016-12-31T23:59:60Z"),
    ):
        try:
            validate_arguments(
                {"sourceModifiedAt": value, "expectedBeans": [{"name": "service"}]},
                "springboot_detect_drift",
            )
            accepted = True
        except NormalizationError:
            accepted = False
        formats[name] = {
            "inputAccepted": accepted,
            "outputFormatAccepted": _is_rfc3339(value),
        }

    body = document()
    # A known root dialect must be inherited by nested schemas. Set the document
    # default unknown to expose the fallback to the wrong lexical scope.
    body["jsonSchemaDialect"] = "https://schemas.example.test/unknown-dialect"
    body["components"]["schemas"]["Root"] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "properties": {"child": {"type": "string"}},
    }
    dialect = query_openapi(body, {"schemaName": "Root"})

    body = document()
    body["paths"]["/orders"] = {"$ref": "#/components/pathItems/Missing"}
    unreadable = query_openapi(body, {"pathPattern": "/orders"})
    findings = {
        "pathItemSiblingOperationLost": {
            "reproduced": siblings["totalMatched"] == 1,
            "methods": [row["httpMethod"] for row in siblings["data"]["items"]],
            "status": siblings["status"],
        },
        "invalidStartupReportedComplete": {
            "reproduced": drift["status"] == "ok",
            "status": drift["status"],
            "coverage": drift["coverage"]["state"],
            "totalMatched": drift["totalMatched"],
            "gaps": drift["coverage"]["gaps"],
        },
        "nonRfc3339Accepted": {
            "reproduced": formats["basicDate"]["inputAccepted"]
            or formats["basicDate"]["outputFormatAccepted"],
            "formats": formats,
        },
        "nestedDialectInheritanceLost": {
            "reproduced": "OPENAPI_SCHEMA_DIALECT_UNSUPPORTED"
            in dialect["coverage"]["gaps"],
            "status": dialect["status"],
            "gaps": dialect["coverage"]["gaps"],
        },
        "unreadablePathReportedAsZero": {
            "reproduced": unreadable["totalMatched"] == 0,
            "status": unreadable["status"],
            "totalMatched": unreadable["totalMatched"],
            "gaps": unreadable["coverage"]["gaps"],
        },
    }
    print(json.dumps(findings, indent=2))
    return int(any(row["reproduced"] for row in findings.values()))


if __name__ == "__main__":
    raise SystemExit(main())
