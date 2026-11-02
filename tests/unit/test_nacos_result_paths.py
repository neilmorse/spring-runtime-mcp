"""Nacos result guards run before constructing any real-target harness."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest


@pytest.fixture
def nacos(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "scripts"))
    module = importlib.import_module("check_nacos_soak")

    def forbidden(*args: Any, **kwargs: Any) -> None:
        pytest.fail("target harness must not be constructed for rejected paths")

    monkeypatch.setattr(module, "NacosSoakAcceptance", forbidden)
    return module


@pytest.mark.parametrize(
    "occupied", ["output", "progress", "directory", "symlink", "symlink-loop"]
)
def test_existing_results_rejected_before_target_initialization(
    nacos: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, occupied: str
) -> None:
    output, progress = tmp_path / "result.json", tmp_path / "result.jsonl"
    sentinel = b"historical evidence\n"
    existing = progress if occupied == "progress" else output
    if occupied == "directory":
        existing.mkdir()
    elif occupied in {"symlink", "symlink-loop"}:
        existing.symlink_to(
            existing if occupied == "symlink-loop" else tmp_path / "missing-target"
        )
    else:
        existing.write_bytes(sentinel)
    monkeypatch.setattr(
        sys, "argv", ["check", "--project", str(tmp_path), "--output", str(output)]
    )
    with pytest.raises(SystemExit) as error:
        nacos.main()
    assert error.value.code == 2
    if occupied == "directory":
        assert existing.is_dir()
    elif occupied in {"symlink", "symlink-loop"}:
        assert existing.is_symlink() and not existing.exists()
    else:
        assert existing.read_bytes() == sentinel
    assert not (output if occupied == "progress" else progress).exists()


def test_same_result_path_rejected_without_creating_files(
    nacos: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output = tmp_path / "result.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "check",
            "--project",
            str(tmp_path),
            "--output",
            str(output),
            "--progress",
            str(output),
        ],
    )
    with pytest.raises(SystemExit) as error:
        nacos.main()
    assert error.value.code == 2 and not output.exists()


def test_progress_creation_failure_rolls_back_only_new_output(
    nacos: ModuleType, tmp_path: Path
) -> None:
    output = tmp_path / "new" / "result.json"
    blocker = tmp_path / "not-a-directory"
    blocker.write_text("keep")
    with pytest.raises(OSError):
        nacos._reserve_result_paths(output, blocker / "progress.jsonl")
    assert not output.exists() and blocker.read_text() == "keep"


@pytest.mark.parametrize("explicit_progress", [False, True])
def test_fresh_paths_reserved_before_harness_runs(
    nacos: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    explicit_progress: bool,
) -> None:
    output = tmp_path / "new" / "result.json"
    progress = (
        tmp_path / "events" / "progress.jsonl"
        if explicit_progress
        else output.with_suffix(".jsonl")
    )

    class FakeAcceptance:
        def __init__(self, args: Any) -> None:
            assert args.progress == progress
            assert output.read_bytes() == progress.read_bytes() == b""

        def run(self) -> int:
            output.write_text('{"accepted": true}\n')
            with progress.open("a") as stream:
                stream.write('{"event": "complete"}\n')
            return 0

    monkeypatch.setattr(nacos, "NacosSoakAcceptance", FakeAcceptance)
    argv = ["check", "--project", str(tmp_path), "--output", str(output)]
    if explicit_progress:
        argv += ["--progress", str(progress)]
    monkeypatch.setattr(sys, "argv", argv)
    assert nacos.main() == 0
    assert '"accepted": true' in output.read_text()
    assert progress.read_text().count("complete") == 1
