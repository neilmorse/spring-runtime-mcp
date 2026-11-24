"""Normalize ApplicationStartup timelines without posting to the startup endpoint."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from ..models.common import AnalysisBudget
from ..models.timestamps import parse_rfc3339

from ..contracts.definitions import glob_matches

_DURATION = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?\Z")
_MAX_RANKED_STEPS = 500


def _nanos(text: str) -> int | None:
    matched = _DURATION.fullmatch(text)
    if matched is None or not any(matched.groups()):
        return None
    hours = Decimal(matched.group(1) or 0)
    minutes = Decimal(matched.group(2) or 0)
    seconds = Decimal(matched.group(3) or 0)
    return int((hours * 3600 + minutes * 60 + seconds) * Decimal(1_000_000_000))


def _timestamp(value: Any) -> str | None:
    return (
        value if isinstance(value, str) and parse_rfc3339(value) is not None else None
    )


def _bottleneck(name: str) -> str:
    if "beans.instantiate" in name:
        return "BEAN_INSTANTIATION"
    if "base-packages.scan" in name or "component-scan" in name:
        return "PACKAGE_SCAN"
    if "auto-config" in name or "autoconfigure" in name:
        return "AUTO_CONFIGURATION"
    return "OTHER" if name else "UNKNOWN"


def _lineage(
    parents: dict[str, str | None], budget: AnalysisBudget
) -> dict[str, tuple[int, bool]]:
    """Cache ancestor counts and cycle evidence across overlapping parent chains."""
    known: dict[str, tuple[int, bool]] = {}
    for step_id in parents:
        path: dict[str, int] = {}
        cursor: str | None = step_id
        while (
            cursor is not None
            and cursor in parents
            and cursor not in known
            and cursor not in path
        ):
            budget.consume()
            path[cursor] = len(path)
            cursor = parents[cursor]

        if cursor is not None and cursor in path:
            cycle_start = path[cursor]
            depth, cyclic = len(path) - cycle_start, True
            for member in list(path)[cycle_start:]:
                known[member] = (depth, True)
                del path[member]
        else:
            # A reported but missing parent still occupies one ancestor slot.
            depth, cyclic = (
                (-1, False) if cursor is None else known.get(cursor, (0, False))
            )

        for member in reversed(path):
            depth += 1
            known[member] = (depth, cyclic)
    return known


def _tags(raw_tags: list[Any]) -> list[dict[str, str | None]]:
    tags: list[dict[str, str | None]] = []
    for tag in raw_tags[:10]:
        if not isinstance(tag, dict) or not isinstance(tag.get("key"), str):
            continue
        value = tag.get("value")
        tags.append(
            {
                "key": tag["key"][:128],
                "value": value[:256] if isinstance(value, str) else None,
            }
        )
    return tags


def normalize_startup(
    body: Any,
    *,
    step_name_pattern: str | None,
    bean_name_pattern: str | None,
    min_duration_ms: float,
    max_depth: int,
) -> tuple[str | None, int | float | None, str, bool, list[dict[str, Any]], list[str]]:
    if not isinstance(body, dict) or not isinstance(body.get("timeline"), dict):
        raise ValueError("INVALID_STARTUP_SHAPE")
    events = body["timeline"].get("events")
    if not isinstance(events, list):
        raise ValueError("INVALID_STARTUP_SHAPE")
    version = body.get("springBootVersion")
    version = version if isinstance(version, str) and len(version) <= 64 else None
    gaps: set[str] = set()
    budget = AnalysisBudget()
    indexed: dict[str, dict[str, Any]] = {}
    parents: dict[str, str | None] = {}
    duplicates: set[str] = set()
    for event in events:
        budget.consume()
        if not isinstance(event, dict) or not isinstance(
            event.get("startupStep"), dict
        ):
            gaps.add("STARTUP_EVENT_UNREADABLE")
            continue
        step = event["startupStep"]
        raw_id = step.get("id")
        if type(raw_id) is not int or raw_id < 0:
            gaps.add("STARTUP_EVENT_UNREADABLE")
            continue
        step_id = str(raw_id)
        if step_id in indexed:
            gaps.add("STARTUP_DUPLICATE_STEP")
            duplicates.add(step_id)
            continue
        parent = step.get("parentId")
        parents[step_id] = str(parent) if type(parent) is int and parent >= 0 else None
        indexed[step_id] = event

    lineage = _lineage(parents, budget)
    candidates: list[tuple[bool, int, str]] = []
    for step_id, event in indexed.items():
        budget.consume()
        step = event["startupStep"]
        nanos = (
            _nanos(event["duration"])
            if isinstance(event.get("duration"), str)
            else None
        )
        if nanos is None:
            gaps.add("STARTUP_DURATION_UNPARSED")
        raw_tags = step.get("tags", [])
        raw_tags = raw_tags if isinstance(raw_tags, list) else []
        if len(raw_tags) > 10:
            gaps.add("STARTUP_TAG_LIMIT")
        parent = parents[step_id]
        depth, cyclic = lineage[step_id]
        if parent is not None and parent not in parents:
            gaps.add("STARTUP_ORPHAN_STEP")
        if cyclic:
            gaps.add("STARTUP_CYCLE")
        if depth > max_depth:
            gaps.add("STARTUP_DEPTH_LIMIT")
            continue
        name = step.get("name") if isinstance(step.get("name"), str) else ""
        if step_name_pattern and not glob_matches(step_name_pattern, name[:256]):
            continue
        if bean_name_pattern and not any(
            tag["key"] == "beanName"
            and isinstance(tag["value"], str)
            and glob_matches(bean_name_pattern, tag["value"])
            for tag in _tags(raw_tags)
        ):
            continue
        if nanos is not None and nanos / 1_000_000 < min_duration_ms:
            continue
        candidates.append((nanos is None, -(nanos or 0), step_id))

    if len(candidates) > _MAX_RANKED_STEPS:
        gaps.add("STARTUP_NODE_LIMIT")
    candidates.sort()
    items: list[dict[str, Any]] = []
    for duration_unknown, negative_nanos, step_id in candidates[:_MAX_RANKED_STEPS]:
        event = indexed[step_id]
        step = event["startupStep"]
        name = step.get("name") if isinstance(step.get("name"), str) else ""
        raw_tags = step.get("tags", [])
        depth, cyclic = lineage[step_id]
        parent_id = parents[step_id]
        ancestors: list[str] = []
        cursor = parent_id
        while cursor is not None and len(ancestors) < depth:
            ancestors.append(cursor)
            cursor = parents.get(cursor)
        relation = "duplicate" if step_id in duplicates else "resolved"
        if parent_id is not None and parent_id not in parents:
            relation = "orphan"
        elif cyclic:
            relation = "cycle"
        items.append(
            {
                "stepId": step_id,
                "parentStepId": parent_id,
                "name": name[:256],
                "startedAt": _timestamp(event.get("startTime")),
                "durationNanos": None if duration_unknown else str(-negative_nanos),
                "durationMs": None if duration_unknown else -negative_nanos / 1_000_000,
                "tags": _tags(raw_tags) if isinstance(raw_tags, list) else [],
                "bottleneckCode": _bottleneck(name),
                "relationState": relation,
                "ancestorIds": ancestors,
            }
        )
    total: int | float | None = None
    try:
        starts = [parse_rfc3339(event["startTime"]) for event in events]
        ends = [parse_rfc3339(event["endTime"]) for event in events]
        if not starts or any(date is None for date in [*starts, *ends]):
            raise ValueError("STARTUP_TIMING_UNOBSERVED")
        valid_starts = [date for date in starts if date is not None]
        valid_ends = [date for date in ends if date is not None]
        raw_start = body["timeline"].get("startTime")
        start = (
            parse_rfc3339(raw_start)
            if "startTime" in body["timeline"]
            else min(valid_starts)
        )
        if start is None:
            raise ValueError("STARTUP_TIMING_UNOBSERVED")
        if any(
            end < begin or begin < start
            for begin, end in zip(valid_starts, valid_ends, strict=True)
        ):
            raise ValueError("STARTUP_TIMING_UNOBSERVED")
        if any(date.leap for date in [start, *valid_starts, *valid_ends]):
            raise ValueError("STARTUP_TIMING_UNOBSERVED")
        total = max(valid_ends).milliseconds_since(start)
    except (ValueError, TypeError, KeyError, AttributeError):
        gaps.add("STARTUP_TIMING_UNOBSERVED")
    complete = not gaps
    basis = "timelineSpan" if total is not None else "unknown"
    return version, total, basis, complete, items, sorted(gaps)
