"""Synthetic P3 boundary evidence; no real targets or retained response bodies."""

from __future__ import annotations

import asyncio
from typing import Any

from spring_runtime_mcp.tools.registry import call_tool
from unit.test_rw06_architecture_regressions import services_for_bodies


def _event(step_id: int, parent: int | None = None) -> dict[str, Any]:
    return {
        "startupStep": {
            "id": step_id,
            "parentId": parent,
            "name": f"sample.step{step_id}",
            "tags": [
                {"key": "beanName", "value": "sampleOne"},
                {"key": "beanName", "value": "sampleTwo"},
            ],
        },
        "startTime": "2026-11-01T00:00:00Z",
        "endTime": "2026-11-01T00:00:01Z",
        "duration": "PT1S",
    }


def _invoke(events: list[dict[str, Any]], **arguments: Any) -> dict[str, Any]:
    return asyncio.run(
        call_tool(
            "springboot_analyze_startup",
            arguments,
            services_for_bodies(
                {
                    "startup": {
                        "timeline": {
                            "startTime": "2026-11-01T00:00:00Z",
                            "events": events,
                        }
                    }
                }
            ),
        )
    )


def test_empty_timeline_retains_unknown_duration_and_incomplete_evidence() -> None:
    result = _invoke([])
    assert result["status"] == "partial"
    assert result["data"]["items"] == []
    assert result["data"]["totalDurationMs"] is None
    assert result["data"]["durationBasis"] == "unknown"
    assert result["data"]["timelineComplete"] is False
    assert "STARTUP_TIMING_UNOBSERVED" in result["coverage"]["gaps"]


def test_nested_duration_is_a_span_and_repeated_tags_survive_filtering() -> None:
    result = _invoke([_event(1), _event(2, 1)], beanNamePattern="sampleTwo")
    assert result["status"] == "ok"
    assert result["data"]["totalDurationMs"] == 1000
    rows = result["data"]["items"]
    assert len(rows) == 2
    assert sum(row["durationMs"] for row in rows) == 2000
    assert rows[1]["ancestorIds"] == ["1"]
    assert rows[1]["tags"] == [
        {"key": "beanName", "value": "sampleOne"},
        {"key": "beanName", "value": "sampleTwo"},
    ]


def test_missing_parent_is_partial_even_when_duration_filter_hides_the_step() -> None:
    result = _invoke([_event(2, 99)], minDurationMs=2000)
    assert result["status"] == "partial"
    assert result["data"]["items"] == []
    assert result["data"]["timelineComplete"] is False
    assert "STARTUP_ORPHAN_STEP" in result["coverage"]["gaps"]
