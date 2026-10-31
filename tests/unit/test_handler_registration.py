"""An incomplete advertised registry must fail before accepting MCP requests."""

import asyncio

import pytest

from spring_runtime_mcp.replay import services_for
from spring_runtime_mcp.server import build_server
from spring_runtime_mcp.tools.registry import HANDLERS, call_tool


@pytest.mark.parametrize("change", ["missing", "extra"])
def test_host_rejects_incomplete_or_extra_handlers(
    monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    if change == "missing":
        monkeypatch.delitem(HANDLERS, "springboot_diagnose_health")
    else:
        monkeypatch.setitem(
            HANDLERS, "unexpected_tool", HANDLERS["springboot_diagnose_health"]
        )
    with pytest.raises(RuntimeError, match="^INVALID_TOOL_HANDLER_REGISTRATION$"):
        build_server(services_for("parent-child"))


def test_advertised_tool_cannot_degrade_to_a_placeholder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delitem(HANDLERS, "springboot_diagnose_health")
    with pytest.raises(RuntimeError, match="^INVALID_TOOL_HANDLER_REGISTRATION$"):
        asyncio.run(
            call_tool("springboot_diagnose_health", {}, services_for("parent-child"))
        )
