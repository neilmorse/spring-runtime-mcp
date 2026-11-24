#!/usr/bin/env python3
"""Summarize lock waits from a local Actuator JSON thread dump."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from spring_runtime_mcp.adapters.thread_dump import analyze_thread_dump as _analyze
from spring_runtime_mcp.models.common import NormalizationError
from spring_runtime_mcp.transport.bounded_json import loads_bounded
from spring_runtime_mcp.transport.replay_files import read_replay_file

_GAP_LABELS = {
    "THREAD_ROW_UNREADABLE": "unreadableThreadRows",
    "THREAD_ID_AMBIGUOUS": "duplicateThreadIds",
    "THREAD_STATE_UNOBSERVED": "unknownThreadStates",
    "THREAD_LOCK_OWNER_UNOBSERVED": "unobservedLockOwners",
}


def analyze_thread_dump(body: Mapping[str, Any]) -> dict[str, Any]:
    summary = _analyze(body)
    for field in ("waitCycles", "waitChains"):
        if len(summary[field]) > 8:
            summary[field] = summary[field][:8]
            summary["truncated"] = True
    summary["coverage"]["gaps"] = sorted(
        _GAP_LABELS[gap] for gap in summary["coverage"]["gaps"]
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Local Actuator JSON file")
    args = parser.parse_args()
    try:
        body = loads_bounded(read_replay_file(args.input.parent, args.input))
        summary = analyze_thread_dump(body)
    except NormalizationError as exc:
        print(exc.code, file=sys.stderr)
        return 1
    print(json.dumps(summary, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
