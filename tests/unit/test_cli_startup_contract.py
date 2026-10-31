"""Operator startup must fail closed with a readable, value-free reason."""

from __future__ import annotations

from importlib.metadata import version as distribution_version

import pytest

from spring_runtime_mcp import __version__
from spring_runtime_mcp.cli import main

SOURCE_CATALOG_MAX_BYTES = 262144


def test_version_matches_the_package_single_source(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == f"spring-runtime-mcp {__version__}"


def test_distribution_metadata_matches_runtime_version() -> None:
    assert distribution_version("spring-runtime-mcp") == __version__


def test_missing_token_variable_is_named_carefully(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("SPRING_RUNTIME_TEST_TOKEN", raising=False)
    with pytest.raises(SystemExit) as exc:
        main(["--token-env", "SPRING_RUNTIME_TEST_TOKEN"])
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "SPRING_RUNTIME_TEST_TOKEN" in captured.err
    assert "missing or empty" in captured.err
    assert "Traceback" not in captured.err


def test_invalid_timeout_names_the_flag(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--timeout", "0"])
    assert exc.value.code == 2
    assert "--timeout" in capsys.readouterr().err


def test_non_loopback_origin_is_rejected_without_connecting(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--base-url", "http://10.0.0.1:8080"])
    assert exc.value.code == 2
    assert "loopback" in capsys.readouterr().err


def test_oversized_source_catalog_is_rejected_before_parsing(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "catalog.json"
    path.write_bytes(b"{" + b" " * SOURCE_CATALOG_MAX_BYTES + b"}")
    with pytest.raises(SystemExit) as exc:
        main(["--source-catalog", str(path)])
    assert exc.value.code == 2
    assert "exceeds" in capsys.readouterr().err


def test_source_catalog_must_be_a_regular_file(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--source-catalog", str(tmp_path)])
    assert exc.value.code == 2
    assert "--source-catalog" in capsys.readouterr().err


def test_source_catalog_target_mismatch_is_reported(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "catalog.json"
    path.write_text('{"targetId":"other","types":[],"producers":[]}', encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        main(["--source-catalog", str(path), "--target-id", "local"])
    assert exc.value.code == 2
    assert "SOURCE_TARGET_MISMATCH" in capsys.readouterr().err


def test_startup_errors_do_not_echo_a_registered_token(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    token = "sk-proj-" + "a" * 40
    monkeypatch.setenv("SPRING_RUNTIME_TEST_TOKEN", token)
    with pytest.raises(SystemExit) as exc:
        main(
            [
                "--token-env",
                "SPRING_RUNTIME_TEST_TOKEN",
                "--base-url",
                "http://10.0.0.1:8080",
            ]
        )
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert token not in captured.err
    assert token not in captured.out
