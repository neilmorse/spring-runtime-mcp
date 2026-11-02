"""Performance baseline benchmarks for key operations.

Run with: uv run --no-sync python -m pytest tests/performance/ -v
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from functools import partial
from typing import Any

import pytest

from spring_runtime_mcp.models.queries import InspectBeansQuery
from spring_runtime_mcp.policy.sanitization import SanitizerPipeline
from spring_runtime_mcp.replay import services_for
from spring_runtime_mcp.snapshots import SnapshotStore
from spring_runtime_mcp.tools.registry import call_tool
from spring_runtime_mcp.transport.responses import serialize_response


# Performance baselines (subject to adjustment based on CI hardware)
BASELINE_P50_MS = {
    "tool_call_simple": 50,  # Simple tool call (e.g., health without details)
    "tool_call_complex": 200,  # Complex tool call (e.g., beans with dependencies)
    "snapshot_serialize": 10,  # Snapshot serialization
    "snapshot_deserialize": 5,  # Snapshot deserialization
    "bean_graph_depth_3": 100,  # Bean graph traversal depth 3
    "response_serialize": 50,  # Response serialization (16 KiB)
}


def _measure_time(
    func: Callable[..., Any],
    *args: Any,
    check: Callable[[Any], None] | None = None,
    **kwargs: Any,
) -> float:
    """Measure execution time in milliseconds."""
    start = time.perf_counter()
    if asyncio.iscoroutinefunction(func):
        result = asyncio.run(func(*args, **kwargs))
    else:
        result = func(*args, **kwargs)
    elapsed_ms = (time.perf_counter() - start) * 1000
    if check is not None:
        check(result)
    return elapsed_ms


def _percentile(values: list[float], p: int) -> float:
    """Calculate percentile."""
    sorted_values = sorted(values)
    index = int(len(sorted_values) * p / 100)
    return sorted_values[min(index, len(sorted_values) - 1)]


def _check_tool_result(result: dict[str, Any]) -> None:
    assert result["status"] in {"ok", "partial"}, result["errors"]
    assert result["data"] is not None
    assert not result["errors"]


def _check_bean_chain(result: dict[str, Any], *, max_depth: int) -> None:
    _check_tool_result(result)
    items = result["data"]["items"]
    assert len(items) == 1 and items[0]["name"] == "orderController"
    resolved = {
        (edge["targetName"], edge["depth"])
        for edge in items[0]["dependencies"]
        if edge["resolution"] == "resolved"
    }
    chain = ["orderService", "orderRepository", "dataSource", "connectionFactory"]
    for depth, name in enumerate(chain[:max_depth], start=1):
        assert (name, depth) in resolved
    assert all(depth <= max_depth for _, depth in resolved)


class TestToolCallPerformance:
    """Benchmark tool call latency."""

    @pytest.mark.parametrize("iterations", [10])
    def test_simple_tool_call_latency(self, iterations: int) -> None:
        """Measure simple tool call latency (p50/p95/p99)."""
        services = services_for("boot-3.4-servlet")
        arguments = {"group": "application", "includeHealthy": False}

        latencies: list[float] = []
        for _ in range(iterations):
            latency = _measure_time(
                call_tool,
                "springboot_diagnose_health",
                arguments,
                services,
                check=_check_tool_result,
            )
            latencies.append(latency)

        p50 = _percentile(latencies, 50)
        p95 = _percentile(latencies, 95)
        p99 = _percentile(latencies, 99)

        print(
            f"\nSimple tool call latency: p50={p50:.2f}ms, p95={p95:.2f}ms, p99={p99:.2f}ms"
        )

        # Baseline check (warning only, not failing test)
        if p50 > BASELINE_P50_MS["tool_call_simple"] * 2:
            print(
                f"⚠️  p50 latency {p50:.2f}ms exceeds 2x baseline {BASELINE_P50_MS['tool_call_simple']}ms"
            )

    @pytest.mark.parametrize("iterations", [10])
    def test_complex_tool_call_latency(self, iterations: int) -> None:
        """Measure complex tool call latency (beans with dependencies)."""
        services = services_for("parent-child")
        arguments = {
            "packagePrefix": "example",
            "beanNamePattern": "orderController",
            "contextId": "application",
            "direction": "dependencies",
            "maxDepth": 3,
        }

        latencies: list[float] = []
        for _ in range(iterations):
            latency = _measure_time(
                call_tool,
                "springboot_inspect_beans",
                arguments,
                services,
                check=partial(_check_bean_chain, max_depth=3),
            )
            latencies.append(latency)

        p50 = _percentile(latencies, 50)
        p95 = _percentile(latencies, 95)
        p99 = _percentile(latencies, 99)

        print(
            f"\nComplex tool call latency: p50={p50:.2f}ms, p95={p95:.2f}ms, p99={p99:.2f}ms"
        )

        if p50 > BASELINE_P50_MS["tool_call_complex"] * 2:
            print(
                f"⚠️  p50 latency {p50:.2f}ms exceeds 2x baseline {BASELINE_P50_MS['tool_call_complex']}ms"
            )


class TestSnapshotPerformance:
    """Benchmark snapshot serialization/deserialization."""

    def test_snapshot_serialization_latency(self) -> None:
        """Measure snapshot serialization latency."""
        store = SnapshotStore()
        sanitizer = SanitizerPipeline()

        # Create a typical result envelope
        result = {
            "schemaVersion": "2",
            "status": "ok",
            "source": {
                "targetId": "local",
                "snapshotId": "s1",
                "observedAt": "2026-10-16T00:00:00Z",
                "endpointIds": ["beans"],
                "bootVersion": "3.4.0",
                "adapterVersion": "0.2.8",
                "policyVersion": "0.2.8",
            },
            "data": {
                "items": [
                    {
                        "id": f"bean_{i}",
                        "name": f"service{i}",
                        "type": "com.example.Service",
                        "dependencies": [f"dep{j}" for j in range(5)],
                    }
                    for i in range(50)
                ]
            },
            "totalMatched": 50,
            "truncated": False,
            "truncationReasons": [],
            "coverage": {"state": "complete", "scope": "all", "gaps": []},
            "warnings": [],
            "redactions": [],
            "nextCursor": None,
            "nextAction": {
                "kind": "done",
                "reasonCode": "COMPLETE",
                "filterSuggestions": [],
            },
            "errors": [],
        }

        query = InspectBeansQuery(target_id="local")

        iterations = 20
        latencies: list[float] = []
        for _ in range(iterations):
            latency = _measure_time(
                store.put_paged, result, query, offset=0, sanitizer=sanitizer
            )
            latencies.append(latency)

        p50 = _percentile(latencies, 50)
        print(f"\nSnapshot serialization latency: p50={p50:.2f}ms")

        if p50 > BASELINE_P50_MS["snapshot_serialize"] * 2:
            print(
                f"⚠️  p50 latency {p50:.2f}ms exceeds 2x baseline {BASELINE_P50_MS['snapshot_serialize']}ms"
            )

    def test_snapshot_deserialization_latency(self) -> None:
        """Measure snapshot deserialization latency (get_page)."""
        store = SnapshotStore()
        sanitizer = SanitizerPipeline()

        # Create and store a snapshot
        result = {
            "schemaVersion": "2",
            "status": "ok",
            "source": {
                "targetId": "local",
                "snapshotId": "s1",
                "observedAt": "2026-10-16T00:00:00Z",
                "endpointIds": ["beans"],
                "bootVersion": "3.4.0",
                "adapterVersion": "0.2.8",
                "policyVersion": "0.2.8",
            },
            "data": {"items": [{"id": f"bean_{i}"} for i in range(50)]},
            "totalMatched": 50,
            "truncated": False,
            "truncationReasons": [],
            "coverage": {"state": "complete", "scope": "all", "gaps": []},
            "warnings": [],
            "redactions": [],
            "nextCursor": None,
            "nextAction": {
                "kind": "done",
                "reasonCode": "COMPLETE",
                "filterSuggestions": [],
            },
            "errors": [],
        }

        query = InspectBeansQuery(target_id="local", max_results=50)
        cursor = store.put_paged(result, query, offset=0, sanitizer=sanitizer)

        query_with_cursor = InspectBeansQuery(
            target_id="local", cursor=cursor, max_results=50
        )

        iterations = 20
        latencies: list[float] = []
        for _ in range(iterations):
            latency = _measure_time(
                store.get_page, cursor, query_with_cursor, sanitizer=sanitizer
            )
            latencies.append(latency)

        p50 = _percentile(latencies, 50)
        print(f"\nSnapshot deserialization latency: p50={p50:.2f}ms")

        if p50 > BASELINE_P50_MS["snapshot_deserialize"] * 2:
            print(
                f"⚠️  p50 latency {p50:.2f}ms exceeds 2x baseline {BASELINE_P50_MS['snapshot_deserialize']}ms"
            )


class TestBeanGraphPerformance:
    """Benchmark Bean graph traversal."""

    @pytest.mark.parametrize("max_depth", [1, 2, 3, 4])
    def test_bean_graph_traversal_depth(self, max_depth: int) -> None:
        """Measure Bean graph traversal latency at different depths."""
        services = services_for("parent-child")
        arguments = {
            "packagePrefix": "example",
            "beanNamePattern": "orderController",
            "contextId": "application",
            "direction": "dependencies",
            "maxDepth": max_depth,
        }

        iterations = 10
        latencies: list[float] = []
        for _ in range(iterations):
            latency = _measure_time(
                call_tool,
                "springboot_inspect_beans",
                arguments,
                services,
                check=partial(_check_bean_chain, max_depth=max_depth),
            )
            latencies.append(latency)

        p50 = _percentile(latencies, 50)
        print(f"\nBean graph depth {max_depth} latency: p50={p50:.2f}ms")

        if max_depth == 3 and p50 > BASELINE_P50_MS["bean_graph_depth_3"] * 2:
            print(
                f"⚠️  Depth 3 p50 latency {p50:.2f}ms exceeds 2x baseline {BASELINE_P50_MS['bean_graph_depth_3']}ms"
            )


class TestResponseProcessing:
    """Benchmark response processing."""

    def test_response_serialization(self) -> None:
        """Measure response serialization latency (16 KiB typical)."""
        # Create a smaller typical response that fits in 16 KiB
        items = [
            {
                "id": f"bean_{i}",
                "name": f"service{i}",
                "type": "com.example.Service",
                "dependencies": [f"dep{j}" for j in range(3)],
            }
            for i in range(30)  # Reduced from 50 to fit in 16 KiB budget
        ]

        result = {
            "schemaVersion": "2",
            "status": "ok",
            "source": {
                "targetId": "local",
                "snapshotId": "s1",
                "observedAt": "2026-10-16T00:00:00Z",
                "endpointIds": ["beans"],
                "bootVersion": "3.4.0",
                "adapterVersion": "0.2.8",
                "policyVersion": "0.2.8",
            },
            "data": {"items": items},
            "totalMatched": 30,
            "truncated": False,
            "truncationReasons": [],
            "coverage": {"state": "complete", "scope": "all", "gaps": []},
            "warnings": [],
            "redactions": [],
            "nextCursor": None,
            "nextAction": {
                "kind": "done",
                "reasonCode": "COMPLETE",
                "filterSuggestions": [],
            },
            "errors": [],
        }

        sanitizer = SanitizerPipeline()

        iterations = 10
        latencies: list[float] = []
        for _ in range(iterations):
            latency = _measure_time(
                serialize_response, result, "req1", sanitizer=sanitizer
            )
            latencies.append(latency)

        p50 = _percentile(latencies, 50)
        print(f"\nResponse serialization latency: p50={p50:.2f}ms")

        if p50 > BASELINE_P50_MS["response_serialize"] * 2:
            print(
                f"⚠️  p50 latency {p50:.2f}ms exceeds 2x baseline {BASELINE_P50_MS['response_serialize']}ms"
            )


def test_print_baselines() -> None:
    """Print current performance baselines."""
    print("\n" + "=" * 60)
    print("Performance Baselines (p50)")
    print("=" * 60)
    for key, value in BASELINE_P50_MS.items():
        print(f"{key:30s}: {value:6.0f} ms")
    print("=" * 60)
    print("\nNote: Baselines are indicative and subject to hardware variation.")
    print("Warnings (⚠️) appear when p50 exceeds 2x baseline.")
