"""Approved A1–A16 tool behavior with mocked IO; B1–B5 are not locked here."""

from __future__ import annotations

import asyncio
import json
from copy import deepcopy
from typing import Any
from unittest.mock import AsyncMock

import pytest
from jsonschema import Draft202012Validator

from spring_runtime_mcp.contracts.definitions import definition, validate_arguments
from spring_runtime_mcp.models.common import NormalizationError, ParsedObservation
from spring_runtime_mcp.models.queries import HealthQuery
from spring_runtime_mcp.models.source_catalog import SourceCatalog
from spring_runtime_mcp.policy.sanitization import SanitizerPipeline
from spring_runtime_mcp.services import RuntimeReader, Services
from spring_runtime_mcp.snapshots import SnapshotStore
from spring_runtime_mcp.tools.diagnose_health import diagnose_health
from spring_runtime_mcp.transport.response_gate import (
    EndpointReadError,
    HttpResponse,
    RegisteredTransport,
    ResponseGateReader,
)
from spring_runtime_mcp.transport.responses import serialize_response

TOOL = "springboot_diagnose_health"
_OUTPUT = Draft202012Validator(definition(TOOL)["outputSchema"])


def _services(
    body: Any,
    *,
    target: str = "local",
    store: SnapshotStore | None = None,
) -> tuple[Services, AsyncMock]:
    reader = AsyncMock(spec=RuntimeReader)

    def observation(
        target_id: str, endpoint_id: str, *, snapshot_id: str
    ) -> ParsedObservation:
        return ParsedObservation(
            target_id,
            snapshot_id,
            "health_observation",
            "2026-10-23T00:00:00Z",
            endpoint_id,
            deepcopy(body),
        )

    reader.read.side_effect = observation
    return (
        Services(
            reader,
            SourceCatalog(target, None, {}, (), ()),
            SanitizerPipeline(),
            store if store is not None else SnapshotStore(),
            targets=frozenset({target}),
        ),
        reader,
    )


def _invoke(arguments: dict[str, Any], services: Services) -> dict[str, Any]:
    result = asyncio.run(diagnose_health(arguments, services))
    _OUTPUT.validate(result)
    serialize_response(result, sanitizer=services.sanitizer)
    return result


def _paging_body() -> dict[str, Any]:
    return {
        "status": "DOWN",
        "components": {
            name: {"status": "DOWN", "details": {"database": "H2"}}
            for name in ("c", "a", "b")
        },
    }


def test_a1_defaults_hide_healthy_components_and_details() -> None:
    query = validate_arguments({}, TOOL)
    assert isinstance(query, HealthQuery)
    assert query.target_id == "local"
    assert query.group == "application"
    assert query.max_results == 50
    assert query.max_depth == 4
    assert query.component_path == ()
    assert query.cursor is None
    assert query.include_details is False
    assert query.include_healthy is False

    services, reader = _services(
        {
            "status": "DOWN",
            "components": {
                "db": {"status": "DOWN", "details": {"database": "H2"}},
                "redis": {"status": "UP"},
            },
        }
    )
    result = _invoke({}, services)

    assert result["data"]["activeGroup"] == "application"
    assert [row["componentPath"] for row in result["data"]["items"]] == [["db"]]
    assert result["data"]["items"][0]["details"] == []
    reader.read.assert_awaited_once()
    assert reader.read.call_args.args == ("local", "health")


@pytest.mark.parametrize(
    "arguments",
    [
        {"maxResults": 0},
        {"maxResults": 51},
        {"maxResults": True},
        {"maxResults": 1.5},
        {"maxDepth": -1},
        {"maxDepth": 17},
        {"maxDepth": None},
        {"includeDetails": "true"},
        {"includeHealthy": None},
        {"group": "unknown"},
        {"targetId": ""},
        {"componentPath": ["db"] * 17},
        {"componentPath": ["x" * 129]},
        {"url": "http://127.0.0.1:1"},
    ],
)
def test_a2_invalid_arguments_fail_before_any_read(arguments: dict[str, Any]) -> None:
    services, reader = _services({"status": "UP", "components": {}})

    result = _invoke(arguments, services)

    assert result["status"] == "invalid"
    assert result["coverage"]["state"] == "unavailable"
    assert result["errors"][0]["code"] == "INVALID_ARGUMENT"
    reader.read.assert_not_awaited()


@pytest.mark.parametrize(
    "arguments",
    [
        {"maxResults": 1, "maxDepth": 0},
        {"maxResults": 50, "maxDepth": 16},
        {"componentPath": []},
        {"componentPath": ["x" * 128] * 16},
    ],
)
def test_a2_parameter_endpoints_are_accepted(arguments: dict[str, Any]) -> None:
    services, reader = _services({"status": "UP", "components": {}})

    result = _invoke(arguments, services)

    assert result["status"] == "ok"
    assert result["data"]["overallStatus"] == "UP"
    assert result["data"]["items"] == []
    reader.read.assert_awaited_once()


@pytest.mark.parametrize(
    ("group", "endpoint"),
    [
        ("application", "health"),
        ("liveness", "health-liveness"),
        ("readiness", "health-readiness"),
    ],
)
@pytest.mark.parametrize("http_status", [200, 503])
def test_a3_a13_groups_use_fixed_get_endpoints_and_accept_health_503(
    group: str, endpoint: str, http_status: int
) -> None:
    services, _ = _services({})
    transport = AsyncMock(spec=RegisteredTransport)
    transport.request.return_value = HttpResponse(
        http_status,
        "application/json",
        b'{"status":"DOWN","details":{"database":"H2"}}',
    )
    services.reader = ResponseGateReader(
        transport, frozenset({"local"}), frozenset({endpoint})
    )

    result = _invoke({"group": group}, services)

    assert result["status"] == "ok"
    assert result["data"]["overallStatus"] == "DOWN"
    assert result["data"]["activeGroup"] == group
    assert result["source"]["endpointIds"] == [endpoint]
    assert result["data"]["items"][0]["endpointId"] == endpoint
    transport.request.assert_awaited_once()
    assert transport.request.call_args.args == ("local", endpoint)
    assert transport.request.call_args.kwargs["method"] == "GET"
    assert transport.request.call_args.kwargs["follow_redirects"] is False


@pytest.mark.parametrize(
    ("http_status", "media", "code", "status"),
    [
        (302, "application/json", "REDIRECT_BLOCKED", "unavailable"),
        (401, "application/json", "ENDPOINT_UNAUTHORIZED", "denied"),
        (403, "application/json", "ENDPOINT_UNAUTHORIZED", "denied"),
        (404, "application/json", "ENDPOINT_NOT_EXPOSED", "unavailable"),
        (500, "application/json", "ENDPOINT_UNAVAILABLE", "unavailable"),
        (200, "text/html", "UNEXPECTED_CONTENT_TYPE", "unavailable"),
    ],
)
def test_a13_a15_http_rejections_preserve_safe_endpoint_metadata(
    http_status: int, media: str, code: str, status: str
) -> None:
    services, _ = _services({})
    transport = AsyncMock(spec=RegisteredTransport)
    transport.request.return_value = HttpResponse(
        http_status, media, b"synthetic-untrusted-body"
    )
    services.reader = ResponseGateReader(
        transport, frozenset({"local"}), frozenset({"health"})
    )

    result = _invoke({}, services)

    assert result["status"] == status
    assert result["coverage"]["state"] == "unavailable"
    assert result["data"] is None
    assert result["totalMatched"] is None
    error = result["errors"][0]
    assert (error["code"], error["endpointId"], error["httpStatus"]) == (
        code,
        "health",
        http_status,
    )
    assert result["nextAction"]["reasonCode"] == code
    assert "synthetic-untrusted-body" not in json.dumps(result)
    transport.request.assert_awaited_once()


@pytest.mark.parametrize(
    ("root_status", "component_status", "expected_paths"),
    [("UP", "DOWN", [["db"]]), ("DOWN", "UP", [])],
)
def test_a5_root_status_is_not_recomputed_and_does_not_set_envelope_status(
    root_status: str, component_status: str, expected_paths: list[list[str]]
) -> None:
    services, _ = _services(
        {
            "status": root_status,
            "components": {
                "db": {"status": component_status, "details": {"database": "H2"}}
            },
        }
    )

    result = _invoke({}, services)

    assert result["status"] == "ok"
    assert result["data"]["overallStatus"] == root_status
    assert [row["componentPath"] for row in result["data"]["items"]] == expected_paths


def test_a7_selected_subtree_does_not_restart_depth_counting() -> None:
    services, _ = _services(
        {
            "status": "DOWN",
            "components": {
                "dependencies": {
                    "status": "DOWN",
                    "components": {
                        "db": {"status": "DOWN", "details": {"database": "H2"}}
                    },
                }
            },
        }
    )

    result = _invoke({"componentPath": ["dependencies", "db"], "maxDepth": 1}, services)

    assert result["data"]["items"] == []
    assert result["status"] == "partial"
    assert result["totalMatched"] is None
    assert result["truncated"] is True
    assert "HEALTH_DEPTH_LIMIT" in result["coverage"]["gaps"]
    assert "HEALTH_DEPTH_LIMIT" in result["truncationReasons"]


@pytest.mark.parametrize("include_details", [False, True])
def test_a9_a16_error_class_survives_while_remote_text_and_secrets_do_not(
    include_details: bool,
) -> None:
    secret = "only-synthetic-health-secret"
    services, _ = _services(
        {
            "status": "DOWN",
            "details": {
                "error": "java.sql.SQLException: synthetic_remote_error_message",
                "password": secret,
                "database": "H2",
            },
        }
    )
    services.sanitizer = SanitizerPipeline(known_secrets=(secret,))

    result = _invoke({"includeDetails": include_details}, services)

    row = result["data"]["items"][0]
    assert row["errorType"] == "java.sql.SQLException"
    frame = serialize_response(result, sanitizer=services.sanitizer)
    assert secret.encode() not in frame
    assert b"synthetic_remote_error_message" not in frame
    if include_details:
        assert {"name": "database", "value": "H2"} in row["details"]
        assert result["redactions"]
    else:
        assert row["details"] == []


def test_a10_detail_limit_marks_the_envelope_partial_and_truncated() -> None:
    services, _ = _services(
        {"status": "DOWN", "details": {f"k{index:02d}": index for index in range(11)}}
    )

    result = _invoke({"includeDetails": True}, services)

    assert result["status"] == "partial"
    assert result["coverage"]["state"] == "partial"
    assert result["totalMatched"] is None
    assert result["truncated"] is True
    assert "HEALTH_DETAILS_LIMIT" in result["coverage"]["gaps"]
    assert "HEALTH_DETAILS_LIMIT" in result["truncationReasons"]
    assert len(result["data"]["items"][0]["details"]) == 10


def test_a11_aggregate_up_does_not_prove_an_empty_component_inventory() -> None:
    hidden, _ = _services({"status": "UP"})
    empty, _ = _services({"status": "UP", "components": {}})

    unobserved = _invoke({"componentPath": ["db"]}, hidden)
    reported_empty = _invoke({"componentPath": ["db"]}, empty)

    assert unobserved["data"]["overallStatus"] == "UP"
    assert unobserved["status"] == "partial"
    assert unobserved["totalMatched"] is None
    assert "HEALTH_DETAILS_NOT_VISIBLE" in unobserved["coverage"]["gaps"]
    assert unobserved["nextAction"]["kind"] == "remediate"
    assert unobserved["nextAction"]["reasonCode"] == "HEALTH_DETAILS_NOT_VISIBLE"
    assert reported_empty["status"] == "ok"
    assert reported_empty["totalMatched"] == 0
    assert reported_empty["data"]["items"] == []
    assert reported_empty["coverage"]["gaps"] == []


@pytest.mark.parametrize(
    ("exception_type", "code"),
    [
        (TimeoutError, "TARGET_TIMEOUT"),
        (ValueError, "MALFORMED_EVIDENCE"),
        (TypeError, "MALFORMED_EVIDENCE"),
        (KeyError, "MALFORMED_EVIDENCE"),
        (RecursionError, "MALFORMED_EVIDENCE"),
        (UnicodeError, "MALFORMED_EVIDENCE"),
        (RuntimeError, "INTERNAL_ERROR"),
    ],
)
def test_a14_reader_exceptions_produce_fixed_errors_without_remote_text(
    exception_type: type[Exception], code: str
) -> None:
    services, reader = _services({}, target="registered")
    reader.read.side_effect = exception_type("synthetic_remote_exception_text")

    result = _invoke({"targetId": "registered"}, services)

    assert result["status"] == "unavailable"
    assert result["source"]["targetId"] == "registered"
    assert result["data"] is None
    assert result["coverage"]["state"] == "unavailable"
    assert result["errors"][0]["code"] == code
    assert result["nextAction"]["reasonCode"] == code
    assert "synthetic_remote_exception_text" not in json.dumps(result)
    reader.read.assert_awaited_once()


def test_a14_domain_error_is_not_reclassified_as_its_value_error_base() -> None:
    services, reader = _services({})
    reader.read.side_effect = NormalizationError("NORMALIZATION_LIMIT")

    result = _invoke({}, services)

    assert result["status"] == "unavailable"
    assert result["errors"][0]["code"] == "NORMALIZATION_LIMIT"


def test_a14_endpoint_error_preserves_its_endpoint_and_http_status() -> None:
    services, reader = _services({})
    reader.read.side_effect = EndpointReadError(
        "ENDPOINT_UNAUTHORIZED", "health-readiness", 403
    )

    result = _invoke({"group": "readiness"}, services)

    assert result["status"] == "denied"
    error = result["errors"][0]
    assert (error["code"], error["endpointId"], error["httpStatus"]) == (
        "ENDPOINT_UNAUTHORIZED",
        "health-readiness",
        403,
    )


def test_a15_unregistered_target_is_denied_without_reading() -> None:
    services, reader = _services({})

    result = _invoke({"targetId": "other"}, services)

    assert result["status"] == "denied"
    assert result["coverage"]["state"] == "unavailable"
    assert result["errors"][0]["code"] == "TARGET_NOT_REGISTERED"
    assert result["source"]["targetId"] == "other"
    reader.read.assert_not_awaited()


def test_a16_continuations_preserve_the_original_snapshot_without_reading_again() -> (
    None
):
    body = _paging_body()
    services, reader = _services(body)
    first = _invoke({"maxResults": 1}, services)
    assert first["truncated"] is True
    assert first["totalMatched"] == 3
    assert first["nextAction"]["kind"] == "page"
    cursor = first["nextCursor"]
    assert isinstance(cursor, str) and cursor
    body["components"].clear()
    reader.read.side_effect = AssertionError("Continuation must not read the target")

    second = _invoke({"maxResults": 1, "cursor": cursor}, services)
    third = _invoke({"maxResults": 1, "cursor": second["nextCursor"]}, services)

    assert [
        page["data"]["items"][0]["componentPath"] for page in (first, second, third)
    ] == [
        ["a"],
        ["b"],
        ["c"],
    ]
    assert first["source"] == second["source"] == third["source"]
    assert third["nextCursor"] is None
    reader.read.assert_awaited_once()


@pytest.mark.parametrize(
    "changed_argument",
    [
        {"targetId": "other"},
        {"maxResults": 2},
        {"group": "readiness"},
        {"componentPath": ["a"]},
        {"includeDetails": True},
        {"includeHealthy": True},
        {"maxDepth": 3},
    ],
)
def test_a16_cursor_rejects_changes_to_non_cursor_parameters(
    changed_argument: dict[str, Any],
) -> None:
    services, reader = _services(_paging_body())
    first = _invoke({"maxResults": 1}, services)

    result = _invoke(
        {"maxResults": 1, "cursor": first["nextCursor"], **changed_argument}, services
    )

    assert result["status"] == "unavailable"
    assert result["errors"][0]["code"] == "CURSOR_QUERY_MISMATCH"
    reader.read.assert_awaited_once()


def test_a16_expired_cursor_does_not_refresh_the_target() -> None:
    now = [100.0]
    services, reader = _services(
        _paging_body(), store=SnapshotStore(clock=lambda: now[0])
    )
    first = _invoke({"maxResults": 1}, services)
    now[0] = 161.0

    result = _invoke({"maxResults": 1, "cursor": first["nextCursor"]}, services)

    assert result["errors"][0]["code"] == "CURSOR_EXPIRED"
    assert result["status"] == "unavailable"
    reader.read.assert_awaited_once()


def test_a16_full_frame_budget_pages_before_the_max_results_limit() -> None:
    services, reader = _services(
        {
            "status": "DOWN",
            "components": {
                f"db{index:02d}": {
                    "status": "DOWN",
                    "details": {f"k{key}": "v" * 300 for key in range(6)},
                }
                for index in range(12)
            },
        }
    )
    arguments = {"includeDetails": True, "maxResults": 50}
    page = _invoke(arguments, services)
    assert 0 < len(page["data"]["items"]) < 12
    assert page["nextCursor"]
    paths = []

    for _ in range(12):
        frame = serialize_response(page, 1, sanitizer=services.sanitizer)
        assert len(frame) <= 16_384
        wire = json.loads(frame)["result"]
        assert wire["structuredContent"] == page
        assert json.loads(wire["content"][0]["text"]) == page
        assert page["totalMatched"] == 12
        paths.extend(row["componentPath"] for row in page["data"]["items"])
        if page["nextCursor"] is None:
            break
        page = _invoke({**arguments, "cursor": page["nextCursor"]}, services)

    assert page["nextCursor"] is None
    assert paths == [[f"db{index:02d}"] for index in range(12)]
    reader.read.assert_awaited_once()
