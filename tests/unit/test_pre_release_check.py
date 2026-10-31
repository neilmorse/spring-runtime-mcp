"""Release checks must not turn missing evidence into a passing gate."""

from __future__ import annotations

import sys
import subprocess
import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from scripts import pre_release_check as gate


@pytest.fixture
def release_project(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text(
        '[build-system]\nrequires = ["hatchling==1.32.4"]\n'
        '[project]\ndynamic = ["version"]\n'
        '[dependency-groups]\ndev = ["hatchling==1.32.4"]\n'
        '[tool.hatch.version]\npath = "src/spring_runtime_mcp/__init__.py"\n'
    )
    package = tmp_path / "src/spring_runtime_mcp"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text('__version__ = "0.2.0"\n')
    (tmp_path / "uv.lock").write_text("")
    return tmp_path


@pytest.mark.parametrize("audit_code", [1, 124, 127])
def test_failed_or_unavailable_audit_blocks_release(
    release_project: Path, monkeypatch: pytest.MonkeyPatch, audit_code: int
) -> None:
    def run(
        cmd: list[str], cwd: Path | None = None, timeout: int = 300
    ) -> tuple[int, str, str]:
        if cmd[:2] == ["uv", "audit"]:
            return audit_code, "", "audit unavailable or vulnerabilities found"
        return 0, "", ""

    monkeypatch.setattr(gate, "run_cmd", run)
    result = gate.check_dependencies_and_version(release_project, audit=True)
    assert result.status == "FAIL"
    assert f"exit {audit_code}" in result.details


def test_skipped_audit_is_incomplete_and_does_not_call_network(
    release_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[list[str]] = []

    def run(
        cmd: list[str], cwd: Path | None = None, timeout: int = 300
    ) -> tuple[int, str, str]:
        calls.append(cmd)
        return 0, "", ""

    monkeypatch.setattr(gate, "run_cmd", run)
    result = gate.check_dependencies_and_version(release_project)
    assert result.status == "WARN"
    assert "未执行" in result.summary
    assert all(cmd[:2] != ["uv", "audit"] for cmd in calls)


def test_dynamic_version_mismatch_fails(
    release_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (release_project / "src/spring_runtime_mcp/other.py").write_text(
        '__version__ = "0.3.0"\n'
    )
    monkeypatch.setattr(gate, "run_cmd", lambda *args, **kwargs: (0, "", ""))
    result = gate.check_dependencies_and_version(release_project, audit=True)
    assert result.status == "FAIL"
    assert "版本号不一致" in result.details


def test_allowing_skipped_tests_is_reported_as_incomplete(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        gate, "run_cmd", lambda *args, **kwargs: (0, "10 passed, 1 skipped", "")
    )
    assert gate.check_test_suite(tmp_path, False).status == "FAIL"
    assert gate.check_test_suite(tmp_path, True).status == "WARN"


def test_skipping_build_returns_incomplete(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ok = gate.CheckResult("fixture", "PASS", "ok")
    monkeypatch.setattr(gate, "check_git_and_secrets", lambda *args: ok)
    monkeypatch.setattr(gate, "check_code_readiness", lambda *args: ok)
    monkeypatch.setattr(
        gate, "check_dependencies_and_version", lambda *args, **kwargs: ok
    )
    monkeypatch.setattr(gate, "check_static_quality", lambda *args: ok)
    monkeypatch.setattr(gate, "check_test_suite", lambda *args: ok)
    monkeypatch.setattr(
        sys, "argv", ["pre_release_check", "--root", str(tmp_path), "--skip-build"]
    )
    assert gate.main() == 2
    assert "检查不完整" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("wheel_version", "cli_version", "expected"),
    [
        ("0.2.0", "0.2.0", "PASS"),
        ("0.3.0", "0.2.0", "FAIL"),
        ("0.2.0", "0.3.0", "FAIL"),
    ],
)
def test_clean_install_uses_locked_constraints_and_checks_versions(
    release_project: Path,
    monkeypatch: pytest.MonkeyPatch,
    wheel_version: str,
    cli_version: str,
    expected: str,
) -> None:
    package = release_project / "src/spring_runtime_mcp"
    (package / "schemas").mkdir()
    (package / "schemas/tools-contract.json").write_text("{}")
    (package / "py.typed").write_text("")
    (package / "replay_data").mkdir()
    (package / "replay_data/sample.json").write_text("{}")
    calls: list[list[str]] = []

    def run(
        cmd: list[str], cwd: Path | None = None, timeout: int = 300
    ) -> tuple[int, str, str]:
        calls.append(cmd)
        if cmd[:2] == ["uv", "build"]:
            dist = Path(cmd[cmd.index("--out-dir") + 1])
            with zipfile.ZipFile(dist / "example.whl", "w") as archive:
                archive.writestr(
                    "example-0.2.0.dist-info/METADATA", f"Version: {wheel_version}\n"
                )
                for file in [
                    package / "schemas/tools-contract.json",
                    package / "py.typed",
                    package / "replay_data/sample.json",
                ]:
                    archive.write(
                        file,
                        "spring_runtime_mcp/" + file.relative_to(package).as_posix(),
                    )
            with tarfile.open(dist / "example-0.2.0.tar.gz", "w:gz") as archive:
                metadata = b"Version: 0.2.0\n"
                info = tarfile.TarInfo("example-0.2.0/PKG-INFO")
                info.size = len(metadata)
                archive.addfile(info, io.BytesIO(metadata))
                for file in [
                    package / "schemas/tools-contract.json",
                    package / "py.typed",
                    package / "replay_data/sample.json",
                ]:
                    archive.add(
                        file,
                        "example-0.2.0/src/spring_runtime_mcp/"
                        + file.relative_to(package).as_posix(),
                    )
        elif cmd[:2] == ["uv", "export"]:
            Path(cmd[cmd.index("-o") + 1]).write_text("mcp==2.3.0\n")
        elif cmd[-1:] == ["--version"]:
            return 0, f"spring-runtime-mcp {cli_version}", ""
        return 0, "", ""

    monkeypatch.setattr(gate, "run_cmd", run)
    output = release_project / "verified-dist"
    assert (
        gate.check_clean_room_build(release_project, output_dir=output).status
        == expected
    )
    if expected == "PASS":
        assert {p.name for p in output.iterdir()} == {
            "example.whl",
            "example-0.2.0.tar.gz",
        }
    else:
        assert not output.exists()
    if wheel_version != "0.2.0":
        assert not any(cmd[:2] == ["uv", "export"] for cmd in calls)
        return
    export = next(cmd for cmd in calls if cmd[:2] == ["uv", "export"])
    assert "--frozen" in export and "--offline" in export
    installs = [cmd for cmd in calls if cmd[:3] == ["uv", "pip", "install"]]
    if expected == "PASS":
        assert len(installs) == 2
        assert {Path(cmd[-1]).suffix for cmd in installs} == {".whl", ".gz"}
        assert len({cmd[cmd.index("--python") + 1] for cmd in installs}) == 2
        assert sum("check_stdio_install.py" in " ".join(cmd) for cmd in calls) == 2
    for install in installs:
        assert "--offline" in install and "-c" in install
        assert install[install.index("-c") + 1] == export[export.index("-o") + 1]


def test_unreadable_dynamic_version_fails(
    release_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (release_project / "src/spring_runtime_mcp/__init__.py").write_text(
        "__version__ = make_version()\n"
    )
    monkeypatch.setattr(gate, "run_cmd", lambda *args, **kwargs: (0, "", ""))
    assert (
        gate.check_dependencies_and_version(release_project, audit=True).status
        == "FAIL"
    )


@pytest.mark.parametrize("requirement", ["hatchling>=1.27", "hatchling==1.27.0"])
def test_build_dependencies_must_be_pinned_and_in_the_lock_audit(
    release_project: Path, monkeypatch: pytest.MonkeyPatch, requirement: str
) -> None:
    pyproject = release_project / "pyproject.toml"
    content = pyproject.read_text()
    pyproject.write_text(
        content.replace(
            'requires = ["hatchling==1.32.4"]', f'requires = ["{requirement}"]'
        )
    )
    monkeypatch.setattr(gate, "run_cmd", lambda *args, **kwargs: (0, "", ""))
    result = gate.check_dependencies_and_version(release_project, audit=True)
    assert result.status == "FAIL"
    assert "构建依赖" in result.details


@pytest.mark.parametrize("failed_command", ["status", "ls-files"])
def test_unavailable_git_status_or_inventory_blocks_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failed_command: str
) -> None:
    def run(
        cmd: list[str], cwd: Path | None = None, timeout: int = 300
    ) -> tuple[int, str, str]:
        return (127, "", "unavailable") if cmd[1] == failed_command else (0, "", "")

    monkeypatch.setattr(gate, "run_cmd", run)
    monkeypatch.setattr(
        gate.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 127, b"", b""),
    )
    assert gate.check_git_and_secrets(tmp_path, allow_dirty=True).status == "FAIL"


def test_unreadable_tracked_file_blocks_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    unreadable = tmp_path / "directory"
    unreadable.mkdir()
    monkeypatch.setattr(gate, "run_cmd", lambda *args, **kwargs: (0, "", ""))
    monkeypatch.setattr(gate, "get_tracked_files", lambda root: [unreadable])
    result = gate.check_git_and_secrets(tmp_path, allow_dirty=False)
    assert result.status == "FAIL"
    assert "无法读取" in result.details


@pytest.mark.parametrize(
    "fault", ["missing_sdist", "version", "resource", "cache", "unsafe_link", "install"]
)
def test_sdist_failures_block_clean_room(
    release_project: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    package = release_project / "src/spring_runtime_mcp"
    (package / "schemas").mkdir()
    (package / "schemas/tools-contract.json").write_text("{}")
    (package / "py.typed").write_text("")
    (package / "replay_data").mkdir()
    (package / "replay_data/sample.json").write_text("{}")
    calls: list[list[str]] = []

    def run(
        cmd: list[str], cwd: Path | None = None, timeout: int = 300
    ) -> tuple[int, str, str]:
        calls.append(cmd)
        if cmd[:2] == ["uv", "build"]:
            dist = Path(cmd[cmd.index("--out-dir") + 1])
            resources = [
                package / "schemas/tools-contract.json",
                package / "py.typed",
                package / "replay_data/sample.json",
            ]
            with zipfile.ZipFile(dist / "example.whl", "w") as archive:
                archive.writestr("example-0.2.0.dist-info/METADATA", "Version: 0.2.0\n")
                for file in resources:
                    archive.write(
                        file,
                        "spring_runtime_mcp/" + file.relative_to(package).as_posix(),
                    )
            if fault != "missing_sdist":
                with tarfile.open(dist / "example-0.2.0.tar.gz", "w:gz") as archive:
                    metadata = f"Version: {'0.3.0' if fault == 'version' else '0.2.0'}\n".encode()
                    info = tarfile.TarInfo("example-0.2.0/PKG-INFO")
                    info.size = len(metadata)
                    archive.addfile(info, io.BytesIO(metadata))
                    for file in resources:
                        if fault == "resource" and file.name == "sample.json":
                            continue
                        archive.add(
                            file,
                            "example-0.2.0/src/spring_runtime_mcp/"
                            + file.relative_to(package).as_posix(),
                        )
                    if fault in {"cache", "unsafe_link"}:
                        info = tarfile.TarInfo(
                            "example-0.2.0/"
                            + (
                                "__pycache__/leak.pyc"
                                if fault == "cache"
                                else "untrusted-link"
                            )
                        )
                        if fault == "unsafe_link":
                            info.type = tarfile.SYMTYPE
                            info.linkname = "../../outside"
                        archive.addfile(info)
        elif cmd[:2] == ["uv", "export"]:
            Path(cmd[cmd.index("-o") + 1]).write_text("mcp==2.3.0\n")
        elif (
            cmd[:3] == ["uv", "pip", "install"]
            and cmd[-1].endswith(".tar.gz")
            and fault == "install"
        ):
            return 1, "", "sdist install failed"
        elif cmd[-1:] == ["--version"]:
            return 0, "spring-runtime-mcp 0.2.0", ""
        return 0, "", ""

    monkeypatch.setattr(gate, "run_cmd", run)
    result = gate.check_clean_room_build(release_project)
    assert result.status == "FAIL"
    if fault == "install":
        assert "安装" in result.summary and ".tar.gz" in result.summary
        assert any(
            cmd[:3] == ["uv", "pip", "install"] and cmd[-1].endswith(".tar.gz")
            for cmd in calls
        )
    else:
        assert not any(cmd[:3] == ["uv", "pip", "install"] for cmd in calls)


def test_contract_failure_blocks_static_gate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def run(cmd: list[str], **kwargs: object) -> tuple[int, str, str]:
        if "scripts/validate_tool_contract.py" in cmd:
            return 1, "contract mismatch", ""
        return 0, "", ""

    monkeypatch.setattr(gate, "run_cmd", run)
    assert gate.check_static_quality(tmp_path).status == "FAIL"


def test_secret_inventory_includes_untracked_nonignored_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fresh = tmp_path / "fresh.py"
    fresh.write_text("# synthetic inventory fixture")
    calls: list[list[str]] = []

    def run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        calls.append(cmd)
        assert kwargs.get("text") is None
        return subprocess.CompletedProcess(cmd, 0, b"fresh.py\0", b"")

    monkeypatch.setattr(gate.subprocess, "run", run)
    assert gate.get_tracked_files(tmp_path) == [fresh]
    assert calls == [
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"]
    ]


@pytest.mark.parametrize(
    "filename",
    [
        "sample.py",
        "中文.py",
        "with\ttab.py",
        "with\nnewline.py",
        "with\rcarriage.py",
        " leading.py",
        "trailing.py ",
    ],
)
@pytest.mark.parametrize("tracked", [False, True], ids=["untracked", "committed-clean"])
def test_real_git_special_paths_are_scanned(
    tmp_path: Path, filename: str, tracked: bool
) -> None:
    def git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)

    git("init")
    git("config", "core.quotePath", "true")
    path = tmp_path / filename
    path.write_text("credential = '" + "ghp_" + "A" * 36 + "'\n")
    if tracked:
        git("add", "--", filename)
        git(
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "-c",
            "core.hooksPath=/dev/null",
            "commit",
            "-m",
            "Synthetic fixture",
        )
        assert (
            subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=tmp_path,
                capture_output=True,
                check=True,
            ).stdout
            == b""
        )
    assert gate.get_tracked_files(tmp_path) == [path]
    result = gate.check_git_and_secrets(tmp_path, allow_dirty=not tracked)
    assert result.status == "FAIL"
    assert "GitHub Token" in result.details
