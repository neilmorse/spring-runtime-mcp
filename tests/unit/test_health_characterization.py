"""Approved A4–A12 Health adapter behavior; B1–B5 remain outside the baseline."""

from __future__ import annotations

from typing import Any

import pytest

from spring_runtime_mcp.adapters.health import normalize_health


def _normalize(body: Any, **options: Any) -> Any:
    arguments = {
        "component_path": (),
        "include_details": False,
        "include_healthy": False,
        "max_depth": 4,
        **options,
    }
    return normalize_health(body, **arguments)


@pytest.mark.parametrize("children_field", ["components", "details"])
def test_a4_component_and_legacy_details_trees_report_the_down_database(
    children_field: str,
) -> None:
    overall, items, gaps = _normalize(
        {
            "status": "DOWN",
            children_field: {
                "redis": {"status": "UP"},
                "db": {"status": "DOWN", "details": {"database": "H2"}},
            },
        },
        include_details=True,
    )

    assert overall == "DOWN"
    assert gaps == []
    assert items == [
        {
            "id": "health_000001",
            "componentPath": ["db"],
            "parentId": None,
            "status": "DOWN",
            "details": [{"name": "database", "value": "H2"}],
            "errorType": None,
            "remediationCodes": ["REVIEW_DATABASE_CONNECTIVITY"],
            "childrenComplete": True,
        }
    ]


def test_a4_reported_components_take_precedence_over_legacy_details() -> None:
    _, items, gaps = _normalize(
        {
            "status": "UP",
            "components": {"db": {"status": "UP"}},
            "details": {"legacy": {"status": "DOWN"}},
        },
        include_healthy=True,
    )

    assert [row["componentPath"] for row in items] == [["db"]]
    assert [row["status"] for row in items] == ["UP"]
    assert gaps == []


@pytest.mark.parametrize(
    ("include_healthy", "expected_paths"),
    [(False, [["db"]]), (True, [["db"], ["redis"]])],
)
def test_a6_healthy_components_are_opt_in(
    include_healthy: bool, expected_paths: list[list[str]]
) -> None:
    _, items, gaps = _normalize(
        {
            "status": "DOWN",
            "components": {
                "redis": {"status": "UP"},
                "db": {"status": "DOWN", "details": {"database": "H2"}},
            },
        },
        include_healthy=include_healthy,
    )

    assert [row["componentPath"] for row in items] == expected_paths
    assert gaps == []


def test_a6_missing_component_status_becomes_unknown_with_an_explicit_gap() -> None:
    _, items, gaps = _normalize(
        {"status": "UP", "components": {"db": {"details": {"database": "H2"}}}}
    )

    assert len(items) == 1
    assert items[0]["componentPath"] == ["db"]
    assert items[0]["status"] == "UNKNOWN"
    assert gaps == ["HEALTH_STATUS_UNOBSERVED"]


def test_a7_component_path_selects_the_component_and_its_descendants() -> None:
    _, items, gaps = _normalize(
        {
            "status": "DOWN",
            "components": {
                "other": {"status": "DOWN", "details": {"version": 1}},
                "db": {
                    "status": "DOWN",
                    "components": {
                        "pool": {"status": "DOWN", "details": {"active": 2}}
                    },
                },
            },
        },
        component_path=("db",),
    )

    assert [row["componentPath"] for row in items] == [["db"], ["db", "pool"]]
    assert items[1]["parentId"] == items[0]["id"]
    assert gaps == []


def test_a8_root_is_omitted_and_children_are_numbered_in_sorted_preorder() -> None:
    _, items, gaps = _normalize(
        {
            "status": "DOWN",
            "components": {
                "z": {"status": "DOWN", "details": {"value": 1}},
                "a": {
                    "status": "DOWN",
                    "components": {
                        "z": {"status": "DOWN", "details": {"value": 2}},
                        "a": {"status": "DOWN", "details": {"value": 3}},
                    },
                },
            },
        }
    )

    assert [row["componentPath"] for row in items] == [
        ["a"],
        ["a", "a"],
        ["a", "z"],
        ["z"],
    ]
    assert [row["id"] for row in items] == [
        "health_000001",
        "health_000002",
        "health_000003",
        "health_000004",
    ]
    assert [row["parentId"] for row in items] == [
        None,
        "health_000001",
        "health_000001",
        None,
    ]
    assert gaps == []


def test_a8_filtered_healthy_parent_does_not_get_an_output_identifier() -> None:
    _, items, gaps = _normalize(
        {
            "status": "DOWN",
            "components": {
                "dependencies": {
                    "status": "UP",
                    "components": {
                        "db": {"status": "DOWN", "details": {"database": "H2"}}
                    },
                }
            },
        }
    )

    assert len(items) == 1
    assert items[0]["componentPath"] == ["dependencies", "db"]
    assert items[0]["parentId"] is None
    assert gaps == []


@pytest.mark.parametrize("include_details", [False, True])
def test_a10_scalar_details_are_sorted_and_limited_only_when_requested(
    include_details: bool,
) -> None:
    _, items, gaps = _normalize(
        {
            "status": "DOWN",
            "components": {},
            "details": {f"k{index:02d}": index for index in reversed(range(11))},
        },
        include_details=include_details,
    )

    assert len(items) == 1
    if include_details:
        assert items[0]["details"] == [
            {"name": f"k{index:02d}", "value": index} for index in range(10)
        ]
        assert gaps == ["HEALTH_DETAILS_LIMIT"]
    else:
        assert items[0]["details"] == []
        assert gaps == []


def test_a12_depth_limit_stops_before_children_and_reports_the_gap() -> None:
    _, items, gaps = _normalize(
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
        },
        max_depth=1,
    )

    assert [row["componentPath"] for row in items] == [["dependencies"]]
    assert items[0]["childrenComplete"] is False
    assert gaps == ["HEALTH_DEPTH_LIMIT"]


@pytest.mark.parametrize("body", [None, [], "invalid", 7])
def test_a14_non_object_health_body_raises_the_existing_shape_error(body: Any) -> None:
    with pytest.raises(ValueError, match="^INVALID_HEALTH_SHAPE$"):
        _normalize(body)
