"""Offline fixture support: no test may contact a diagnostic target."""

from __future__ import annotations

import json
import socket
import ssl
from collections.abc import Callable, Iterator
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, NoReturn

import pytest

from scripts.runtime_benchmarks.fixture_tls import write_certificates

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "bean_graph"


@pytest.fixture
def loopback_tls() -> Iterator[tuple[ssl.SSLContext, Path]]:
    """Server identity and public CA for a single loopback test."""
    with TemporaryDirectory() as temporary:
        directory = Path(temporary)
        write_certificates(directory)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(directory / "server.pem")
        yield context, directory / "ca.pem"


@pytest.fixture(autouse=True)
def prohibit_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail closed for DNS and both high-level and socket connection APIs."""

    def denied(*args: object, **kwargs: object) -> NoReturn:
        raise AssertionError("Offline tests must not access the network")

    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)
    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket.socket, "connect_ex", denied)


@pytest.fixture
def fixture_json() -> Callable[[str], Any]:
    """Load a fresh JSON object, confined to the synthetic fixture tree."""

    def load(relative_path: str) -> Any:
        root = FIXTURE_ROOT.resolve()
        path = (root / relative_path).resolve()
        if not path.is_relative_to(root) or path.suffix != ".json":
            raise ValueError("Fixture path must be a JSON file below fixture root")
        return json.loads(path.read_text(encoding="utf-8"))

    return load


@pytest.fixture
def beans_payload(fixture_json: Callable[[str], Any]) -> dict[str, Any]:
    return fixture_json("parent-child/beans.json")


@pytest.fixture
def conditions_payload(fixture_json: Callable[[str], Any]) -> dict[str, Any]:
    return fixture_json("stripe-missing/conditions.json")


@pytest.fixture
def source_catalog_payload(fixture_json: Callable[[str], Any]) -> dict[str, Any]:
    return fixture_json("stripe-missing/source-catalog.json")
