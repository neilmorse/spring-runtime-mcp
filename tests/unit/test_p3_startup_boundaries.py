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


def test_large_timeline_ranks_late_steps_and_resolves_late_parents() -> None:
    events = [_event(2, 1)] + [_event(step_id) for step_id in range(3, 503)]
    events += [_event(1), _event(503)]
    events[-1]["duration"] = "PT3S"
    events[-1]["endTime"] = "2026-11-01T00:00:03Z"
    events[0]["duration"] = "PT2S"
    events[0]["endTime"] = "2026-11-01T00:00:02Z"

    result = _invoke(events, maxResults=2)

    assert result["status"] == "partial"
    assert result["totalMatched"] is None
    assert result["data"]["totalDurationMs"] == 3000
    assert [row["stepId"] for row in result["data"]["items"]] == ["503", "2"]
    child = result["data"]["items"][1]
    assert child["ancestorIds"] == ["1"]
    assert child["relationState"] == "resolved"
    assert "STARTUP_NODE_LIMIT" in result["coverage"]["gaps"]
    assert "STARTUP_ORPHAN_STEP" not in result["coverage"]["gaps"]

    filtered = _invoke(events, stepNamePattern="sample.step503")
    assert filtered["status"] == "ok"
    assert filtered["totalMatched"] == 1
    assert filtered["data"]["items"][0]["stepId"] == "503"


def test_depth_limit_applies_at_maximum_supported_depth() -> None:
    events = [_event(1)] + [_event(step_id, step_id - 1) for step_id in range(2, 20)]

    result = _invoke(events, stepNamePattern="sample.step19", maxDepth=16)

    assert result["status"] == "partial"
    assert result["data"]["items"] == []
    assert "STARTUP_DEPTH_LIMIT" in result["coverage"]["gaps"]


def test_cycle_through_late_step_is_retained() -> None:
    events = [_event(1, 2)] + [_event(step_id) for step_id in range(3, 503)]
    events.append(_event(2, 1))

    result = _invoke(events, stepNamePattern="sample.step1")

    assert result["status"] == "partial"
    item = result["data"]["items"][0]
    assert item["relationState"] == "cycle"
    assert item["ancestorIds"] == ["2", "1"]
    assert "STARTUP_CYCLE" in result["coverage"]["gaps"]
    assert "STARTUP_ORPHAN_STEP" not in result["coverage"]["gaps"]


def test_long_shared_ancestry_preserves_shallow_evidence_within_budget() -> None:
    events = [_event(step_id, step_id - 1) for step_id in range(1500, 1, -1)]
    events.append(_event(1))

    result = _invoke(events, stepNamePattern="sample.step3")

    assert result["status"] == "partial"
    assert result["data"]["items"][0]["ancestorIds"] == ["2", "1"]
    assert "STARTUP_DEPTH_LIMIT" in result["coverage"]["gaps"]
    assert "STARTUP_ORPHAN_STEP" not in result["coverage"]["gaps"]
