"""Regression checks for bounded startup evidence and unavailable MCP semantics."""

import asyncio
import importlib.util
import socket
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[2] / "scripts/check_injected_runtime_faults.py"
)
spec = importlib.util.spec_from_file_location("runtime_fault_checks", SCRIPT)
assert spec is not None and spec.loader is not None
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


def test_startup_markers_require_specific_evidence() -> None:
    unknown = runtime.startup_markers(b"startup failed")
    assert not any(unknown.values())
    flyway = runtime.startup_markers(b"FlywayMigrateException V2__injected_failure.sql")
    assert flyway["flywayMigrationFailure"] and flyway["flywayVersion2"]
    assert not flyway["circularDependency"]
    cycle = runtime.startup_markers(b"BeanCurrentlyInCreationException cycleA cycleB")
    assert all(cycle[key] for key in ("circularDependency", "cycleA", "cycleB"))
    assert not cycle["flywayMigrationFailure"]
    failure_analysis = runtime.startup_markers(
        b"The dependencies of some of the beans in the application context form a cycle"
    )
    assert failure_analysis["circularDependency"]
    assert not failure_analysis["cycleA"]


def test_failed_target_does_not_invent_migration_cause() -> None:
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
        result = asyncio.run(runtime.verify_unavailable(port, "synthetic"))
    assert result["passed"]
    assert result["coverage"] == "unavailable"
    assert result["attribution"] == "unknown"
    assert result["copiesEqual"]
