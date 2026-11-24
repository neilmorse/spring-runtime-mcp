from __future__ import annotations

import asyncio
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from spring_runtime_mcp.cli import main
from spring_runtime_mcp.contracts.definitions import definition, validate_arguments
from spring_runtime_mcp.models.common import NormalizationError
from spring_runtime_mcp.models.source_catalog import SourceCatalog
from spring_runtime_mcp.policy.configuration import ConfigReadPolicy
from spring_runtime_mcp.policy.sanitization import SanitizerPipeline
from spring_runtime_mcp.replay import FixtureReader
from spring_runtime_mcp.services import Services
from spring_runtime_mcp.snapshots import SnapshotStore
from spring_runtime_mcp.tools.inspect_config import inspect_config
from spring_runtime_mcp.transport.actuator_http import ActuatorHttpTransport


def test_authenticated_registration_requires_https() -> None:
    targets = frozenset({"local"})
    with pytest.raises(ValueError, match="^CREDENTIAL_REQUIRES_TLS$"):
        ActuatorHttpTransport(
            "http://127.0.0.1", targets=targets, bearer_token="fixture"
        )
    ActuatorHttpTransport("http://127.0.0.1", targets=targets)
    ActuatorHttpTransport("https://127.0.0.1", targets=targets, bearer_token="fixture")


def test_invalid_cli_option_has_a_fixed_hint(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--unrecognized-option", "fixture-example"])
    captured = capsys.readouterr()
    assert exc.value.code == 2 and not captured.out
    assert "--help" in captured.err and "fixture-example" not in captured.err


def test_http_bearer_configuration_exits_before_stdio(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    token = "synthetic-tls-registration"
    monkeypatch.setenv("REGISTRATION_TOKEN", token)
    with pytest.raises(SystemExit) as exc:
        main(
            [
                "--base-url",
                "http://127.0.0.1:18081",
                "--token-env",
                "REGISTRATION_TOKEN",
            ]
        )
    captured = capsys.readouterr()
    assert exc.value.code == 2 and captured.out == ""
    assert "HTTPS" in captured.err and token not in captured.err


@pytest.mark.parametrize(
    "arguments",
    [
        {"routeSource": "application", "httpMethod": "GET"},
        {"routeSource": "application", "controllerClassPattern": "Order*"},
        {"routeSource": "application"},
        {"routeSource": "gateway", "pathPattern": "/orders/*"},
        {"routeSource": "gateway", "contextId": "fixture"},
    ],
)
def test_route_source_contract_matches_runtime(arguments: dict[str, str]) -> None:
    name = "springboot_verify_mappings"
    expected = Draft202012Validator(definition(name)["inputSchema"]).is_valid(arguments)
    try:
        validate_arguments(arguments, name)
    except NormalizationError:
        accepted = False
    else:
        accepted = True
    assert accepted == expected


@pytest.mark.parametrize("complete", [False, True])
def test_config_inventory_total_tracks_evidence(complete: bool) -> None:
    bodies: dict[str, dict[str, Any]] = {"env": {"propertySources": []}}
    if complete:
        bodies["configprops"] = {"contexts": {}}
    services = Services(
        FixtureReader(bodies),
        SourceCatalog("local", None, {}, (), ()),
        SanitizerPipeline(),
        SnapshotStore(),
        config_policy=ConfigReadPolicy(prefixes=frozenset({"app"})),
    )
    result = asyncio.run(inspect_config({"prefix": "app"}, services))
    assert result["status"] == ("ok" if complete else "partial")
    assert result["totalMatched"] == (0 if complete else None)


def test_benchmark_keeps_generated_name(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from scripts.runtime_benchmarks import targets

    recorded_names: list[str] = []

    @contextmanager
    def capture(
        args: list[str], name: str, *, env: dict[str, str] | None = None
    ) -> Iterator[None]:
        recorded_names.append(name)
        yield

    monkeypatch.setattr(targets, "_container", capture)
    monkeypatch.setattr(targets, "_docker", lambda args: None)
    monkeypatch.setattr(targets.Application, "_wait_ready", lambda self: None)
    with targets.launch(
        "fixture",
        [],
        tmp_path,
        "health",
        {},
        private_environment={"SYNTHETIC_SETTING": "example"},
    ) as app:
        assert app.container.startswith("spring-mcp-bench-")
        assert recorded_names == [app.container]


def test_benchmark_management_tls_registers_server_and_client(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from cryptography import x509
    from cryptography.hazmat.primitives.serialization import pkcs12

    from scripts.runtime_benchmarks import targets

    directory = tmp_path / "tls"
    directory.mkdir(mode=0o700)
    creates: list[str] = []

    def docker(args: list[str], *, env: dict[str, str] | None = None) -> bytes:
        if args[0] == "create":
            creates.append(args[2])
            assert f"{directory}:/work/tls:ro" in args
            assert "SSL_CERT_FILE=/work/tls/ca.pem" in args
            assert "--management.server.ssl.enabled=true" in args
            assert "--management.server.ssl.key-store=file:/work/tls/server.p12" in args
            assert (
                "--management.server.ssl.key-store-password=${BENCHMARK_TLS_STORE_PASSWORD}"
                in args
            )
            assert env is not None
            password = env["BENCHMARK_TLS_STORE_PASSWORD"]
            assert all(password not in arg for arg in args)
            key, cert, chain = pkcs12.load_key_and_certificates(
                (directory / "server.p12").read_bytes(), password.encode("ascii")
            )
            ca = x509.load_pem_x509_certificate((directory / "ca.pem").read_bytes())
            assert key is not None and cert is not None and chain == [ca]
            cert.verify_directly_issued_by(ca)
        return b""

    monkeypatch.setattr(targets, "_docker", docker)
    monkeypatch.setattr(targets.Application, "_wait_ready", lambda self: None)
    with targets.launch(
        "fixture", [], tmp_path, "health", {}, management_tls=directory
    ) as app:
        assert creates == [app.container]
        assert app.origin == f"https://127.0.0.1:{targets.PORT}"
