"""A connection attempt has its own bound inside the overall read deadline."""

from __future__ import annotations

import asyncio
import socket
import threading
from types import SimpleNamespace
from typing import Any

import pytest

from spring_runtime_mcp.transport.actuator_http import (
    ActuatorHttpTransport,
    _ExchangeState,
)
from spring_runtime_mcp.transport import actuator_http
from spring_runtime_mcp.transport.response_gate import HttpResponse


@pytest.mark.parametrize("deadline", [0.2, 5.0])
def test_connect_deadline_is_bounded_and_read_timeout_is_restored(
    monkeypatch: pytest.MonkeyPatch, deadline: float
) -> None:
    class FakeSocket:
        def __init__(self, *args: Any) -> None:
            self.timeouts: list[float] = []
            self.target: Any = None

        def settimeout(self, value: float) -> None:
            self.timeouts.append(value)

        def connect(self, address: Any) -> None:
            self.target = address

        def getpeername(self) -> Any:
            return self.target

        def close(self) -> None:
            return None

    monkeypatch.setattr(socket, "socket", FakeSocket)
    transport = ActuatorHttpTransport(
        "http://127.0.0.1:18081", targets=frozenset({"local"})
    )
    state = _ExchangeState(deadline)
    connection = transport._open(deadline, state)
    sock = connection._create_connection(("127.0.0.1", 18081))
    assert isinstance(sock, FakeSocket)
    assert len(sock.timeouts) == 2
    assert 0 < sock.timeouts[0] <= min(2.0, deadline)
    assert 0 < sock.timeouts[1] <= deadline
    if deadline > 2:
        assert sock.timeouts[1] > sock.timeouts[0]


def test_multiple_addresses_share_one_connect_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = SimpleNamespace(now=100.0)
    monkeypatch.setattr(
        actuator_http, "time", SimpleNamespace(monotonic=lambda: clock.now)
    )
    records = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 18081))] * 3
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: records)
    attempts: list[float] = []

    class RefusedSocket:
        def __init__(self, *args: Any) -> None:
            self.timeout = 0.0

        def settimeout(self, value: float) -> None:
            self.timeout = value

        def connect(self, address: Any) -> None:
            attempts.append(self.timeout)
            clock.now += min(1.5, self.timeout)
            raise OSError("synthetic refusal")

        def close(self) -> None:
            return None

    monkeypatch.setattr(socket, "socket", RefusedSocket)
    transport = ActuatorHttpTransport(
        "http://localhost:18081", targets=frozenset({"local"})
    )
    state = _ExchangeState(5.0)
    connection = transport._open(5.0, state)
    with pytest.raises(TimeoutError):
        connection._create_connection(("localhost", 18081))
    assert attempts == [2.0, 0.5]


def test_cancelled_call_keeps_worker_slot_until_exchange_returns(monkeypatch):
    transport = ActuatorHttpTransport(
        "http://localhost:18081", targets=frozenset({"local"})
    )

    async def run():
        started: asyncio.Queue[None] = asyncio.Queue()
        finish = threading.Event()
        loop = asyncio.get_running_loop()

        def exchange(*args):
            loop.call_soon_threadsafe(started.put_nowait, None)
            assert finish.wait(5)
            return HttpResponse(200, "application/json", b"{}")

        async def request(timeout):
            return await transport.request(
                "local",
                "health",
                method="GET",
                follow_redirects=False,
                timeout=timeout,
                max_bytes=1024,
            )

        monkeypatch.setattr(transport, "_exchange", exchange)
        first = [asyncio.create_task(request(4)) for _ in range(2)]
        try:
            for _ in first:
                await asyncio.wait_for(started.get(), 2)
            for task in first:
                task.cancel()
            assert all(
                isinstance(result, asyncio.CancelledError)
                for result in await asyncio.gather(*first, return_exceptions=True)
            )
            with pytest.raises(TimeoutError):
                await request(0.03)
            assert started.empty()
        finally:
            finish.set()
        assert (await request(2)).status == 200

    asyncio.run(run())
