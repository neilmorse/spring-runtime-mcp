from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.analyze_thread_dump import analyze_thread_dump, main


def _row(thread: int, state: str, owner: int = -1) -> dict[str, object]:
    return {"threadId": thread, "threadState": state, "lockOwnerId": owner}


def test_blocked_thread_with_observed_owner() -> None:
    result = analyze_thread_dump(
        {
            "threads": [
                _row(11, "BLOCKED", 12),
                _row(12, "RUNNABLE"),
                _row(13, "WAITING"),
            ],
        }
    )

    assert result["stateCounts"]["BLOCKED"] == result["stateCounts"]["WAITING"] == 1
    assert result["waitCycleStatus"] == "noneObserved"
    assert result["waitChains"] == [
        {"threadIds": ["11", "12"], "end": "endOfObservedChain"}
    ]
    assert result["coverage"] == {"state": "complete", "gaps": []}


def test_cycle_is_reported_once_with_a_separate_feeder_chain() -> None:
    rows = [_row(19, "BLOCKED", 21), _row(21, "WAITING", 20), _row(20, "BLOCKED", 21)]
    result = analyze_thread_dump({"threads": rows})

    assert result == analyze_thread_dump({"threads": rows[::-1]})
    assert result["waitCycleStatus"] == "observed"
    assert result["waitCycleCount"] == 1
    assert result["waitCycles"] == [
        {"threadIds": ["20", "21"], "length": 2, "containsTimedWait": False}
    ]
    assert result["waitChains"] == [{"threadIds": ["19", "21"], "end": "observedCycle"}]


@pytest.mark.parametrize(
    ("rows", "gaps", "chain"),
    [
        ([_row(11, "BLOCKED", 12)], ["unobservedLockOwners"], ["11", "12"]),
        ([_row(11, "BLOCKED")], ["unobservedLockOwners"], ["11"]),
        (
            [_row(11, "BLOCKED", 12), _row(12, "BLOCKED", 11), _row(12, "RUNNABLE")],
            ["duplicateThreadIds", "unobservedLockOwners"],
            ["11", "12"],
        ),
        (
            [
                _row(11, "BLOCKED", 12),
                _row(12, "PRIVATE_UNRECOGNIZED"),
                {"threadId": True},
            ],
            ["unknownThreadStates", "unobservedLockOwners", "unreadableThreadRows"],
            ["11", "12"],
        ),
    ],
)
def test_incomplete_owner_evidence_keeps_cycle_status_unknown(
    rows: list[dict[str, object]], gaps: list[str], chain: list[str]
) -> None:
    result = analyze_thread_dump({"threads": rows})
    assert result["waitCycleStatus"] == "unknown"
    assert result["waitCycles"] == []
    assert result["coverage"] == {"state": "partial", "gaps": gaps}
    assert result["waitChains"] == [{"threadIds": chain, "end": "ownerUnobserved"}]


def test_cycle_detection_precedes_output_depth_limit() -> None:
    rows = [_row(thread, "BLOCKED", thread % 20 + 1) for thread in range(1, 21)]
    result = analyze_thread_dump({"threads": rows})

    assert result["waitCycleStatus"] == "observed"
    assert result["waitCycles"] == [
        {
            "threadIds": [str(i) for i in range(1, 17)],
            "length": 20,
            "containsTimedWait": False,
        }
    ]
    assert result["truncated"] is True


def test_output_limits_many_long_chains() -> None:
    rows = [
        _row(thread, "BLOCKED", thread + 1)
        for start in range(1, 1000, 100)
        for thread in range(start, start + 20)
    ] + [_row(start + 20, "RUNNABLE") for start in range(1, 1000, 100)]
    result = analyze_thread_dump({"threads": rows})

    assert result["waitChainCount"] == 10
    assert len(result["waitChains"]) == 8
    assert all(len(chain["threadIds"]) == 16 for chain in result["waitChains"])
    assert all(chain["end"] == "depthLimit" for chain in result["waitChains"])
    assert result["truncated"] is True


def test_cli_projects_only_safe_thread_facts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "threads.json"
    row = _row(11, "RUNNABLE") | {
        "threadName": "PRIVATE_NAME",
        "lockName": "PRIVATE_LOCK",
        "stackTrace": [{"fileName": "PRIVATE_PATH"}],
    }
    path.write_text(json.dumps({"threads": [row]}), encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["analyze_thread_dump.py", str(path)])

    assert main() == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out)["stateCounts"]["RUNNABLE"] == 1
    assert "PRIVATE_" not in captured.out
    assert captured.err == ""

    path.write_text('{"private":"PRIVATE_BODY"}', encoding="utf-8")
    assert main() == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "UNSUPPORTED_SHAPE\n"
