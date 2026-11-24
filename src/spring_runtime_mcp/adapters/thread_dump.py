"""Normalize visible lock-owner relationships from an Actuator thread dump."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..models.common import AnalysisBudget, NormalizationError

_STATES = ("NEW", "RUNNABLE", "BLOCKED", "WAITING", "TIMED_WAITING", "TERMINATED")
_WAITING = frozenset(("BLOCKED", "WAITING", "TIMED_WAITING"))
_MAX_THREAD_ID = 2**63 - 1
_MAX_PATH_LENGTH = 16


def _cycles(owners: dict[int, int | None], budget: AnalysisBudget) -> list[list[int]]:
    """Find closed cycles in the reported owner graph before limiting output."""
    visited: set[int] = set()
    cycles = []
    for thread_id in sorted(owners):
        path: list[int] = []
        positions: dict[int, int] = {}
        current: int | None = thread_id
        while current is not None and current in owners and current not in visited:
            budget.consume()
            visited.add(current)
            positions[current] = len(path)
            path.append(current)
            current = owners[current]
        if current is not None and current in positions:
            cycle = path[positions[current] :]
            first = cycle.index(min(cycle))
            cycles.append(cycle[first:] + cycle[:first])
    return sorted(cycles)


def _chain(
    start: int,
    owners: dict[int, int | None],
    states: dict[int, str | None],
    cycle_members: set[int],
    budget: AnalysisBudget,
) -> tuple[list[int], str]:
    path = [start]
    current = start
    while True:
        budget.consume()
        if current in cycle_members:
            return path, "observedCycle"
        if current not in states or states[current] is None:
            return path, "ownerUnobserved"
        if current not in owners:
            return path, "endOfObservedChain"
        owner = owners[current]
        if owner is None:
            return path, "ownerUnobserved"
        if len(path) >= _MAX_PATH_LENGTH:
            return path, "depthLimit"
        path.append(owner)
        current = owner


def analyze_thread_dump(body: Mapping[str, Any]) -> dict[str, Any]:
    rows = body.get("threads")
    budget = AnalysisBudget()
    if not isinstance(rows, list):
        raise NormalizationError("UNSUPPORTED_SHAPE")

    records: dict[int, dict[str, Any]] = {}
    duplicates: set[int] = set()
    gaps: set[str] = set()
    for row in rows:
        budget.consume()
        thread_id = row.get("threadId") if isinstance(row, dict) else None
        if type(thread_id) is not int or not 1 <= thread_id <= _MAX_THREAD_ID:
            gaps.add("THREAD_ROW_UNREADABLE")
            continue
        if thread_id in records:
            duplicates.add(thread_id)
        records[thread_id] = row
    if duplicates:
        gaps.add("THREAD_ID_AMBIGUOUS")
        for thread_id in duplicates:
            del records[thread_id]

    counts = dict.fromkeys(_STATES, 0)
    states: dict[int, str | None] = {}
    owners: dict[int, int | None] = {}
    for thread_id, row in records.items():
        budget.consume()
        state = row.get("threadState")
        if state not in _STATES:
            states[thread_id] = None
            gaps.add("THREAD_STATE_UNOBSERVED")
            continue
        states[thread_id] = state
        counts[state] += 1
        if state in _WAITING:
            owner = row.get("lockOwnerId")
            if type(owner) is int and 1 <= owner <= _MAX_THREAD_ID:
                owners[thread_id] = owner
            elif state == "BLOCKED" or type(owner) is not int or owner != -1:
                owners[thread_id] = None
    if any(owner is None or states.get(owner) is None for owner in owners.values()):
        gaps.add("THREAD_LOCK_OWNER_UNOBSERVED")

    cycles = _cycles(owners, budget)
    cycle_members = {member for cycle in cycles for member in cycle}
    downstream = {owner for owner in owners.values() if owner is not None}
    starts = sorted(set(owners) - cycle_members - downstream)
    chains = [_chain(start, owners, states, cycle_members, budget) for start in starts]
    return {
        "observedThreads": len(records),
        "stateCounts": counts,
        "waitCycleStatus": "observed"
        if cycles
        else "unknown"
        if gaps
        else "noneObserved",
        "waitCycleCount": len(cycles),
        "waitCycles": [
            {
                "threadIds": [str(member) for member in cycle[:_MAX_PATH_LENGTH]],
                "length": len(cycle),
                "containsTimedWait": any(
                    states[member] == "TIMED_WAITING" for member in cycle
                ),
            }
            for cycle in cycles
        ],
        "waitChainCount": len(starts),
        "waitChains": [
            {"threadIds": [str(member) for member in path], "end": end}
            for path, end in chains
        ],
        "truncated": (
            any(len(cycle) > _MAX_PATH_LENGTH for cycle in cycles)
            or any(end == "depthLimit" for _, end in chains)
        ),
        "coverage": {"state": "partial" if gaps else "complete", "gaps": sorted(gaps)},
    }
