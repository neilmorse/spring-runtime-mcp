"""Acceptance checks use disposable loopback fixtures, never a Spring instance."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

from spring_runtime_mcp.contracts.definitions import definition
from spring_runtime_mcp.models.common import NormalizationError
from spring_runtime_mcp.policy.output_guard import ensure_safe_output
from spring_runtime_mcp.policy.sanitization import SanitizerPipeline

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts"
spec = importlib.util.spec_from_file_location(
    "protocol_acceptance", SCRIPT_DIR / "check_injected_protocol_faults.py"
)
assert spec is not None and spec.loader is not None
protocol = importlib.util.module_from_spec(spec)
sys.path.insert(0, str(SCRIPT_DIR))
try:
    spec.loader.exec_module(protocol)
finally:
    sys.path.remove(str(SCRIPT_DIR))


def test_synthetic_faults_recover_through_real_stdio() -> None:
    report = protocol.run()
    assert report["trapReads"] == 0 and report["mcpExitCode"] == 0
    assert len(report["cases"]) == 10
    assert report["cases"]["10-health-down"]["status"] == "ok"


def test_independent_gates_reject_corrupt_evidence() -> None:
    validator = Draft202012Validator(definition(protocol.HEALTH)["outputSchema"])
    with pytest.raises(ValidationError):
        validator.validate({"status": "ok", "data": None})
    with pytest.raises(NormalizationError):
        ensure_safe_output(
            {"message": protocol.CANARY}, sanitizer=SanitizerPipeline((protocol.TOKEN,))
        )
    with pytest.raises(NormalizationError):
        ensure_safe_output(
            {"value": protocol.TOKEN}, sanitizer=SanitizerPipeline((protocol.TOKEN,))
        )


def test_failure_report_is_fixed_and_written(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "failure.json"

    def fail() -> dict[str, object]:
        raise AssertionError(protocol.TOKEN)

    monkeypatch.setattr(protocol, "run", fail)
    monkeypatch.setattr(sys, "argv", ["check", "--output", str(output)])
    assert protocol.main() == 1
    report = json.loads(output.read_text())
    assert report["passed"] is False
    assert report["failureCodes"] == ["PROTOCOL_ACCEPTANCE_ASSERTIONERROR"]
    assert protocol.TOKEN not in output.read_text()
    assert protocol.TOKEN not in capsys.readouterr().out


def test_runtime_readiness_never_follows_redirects() -> None:
    paths: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            pass

        def do_GET(self) -> None:
            paths.append(self.path)
            self.send_response(302)
            self.send_header("Location", "/trap")
            self.send_header("Content-Length", "0")
            self.end_headers()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        # Keep the parent test's network prohibition intact. The child receives
        # only this fixture port and the local script, like the STDIO probes.
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                """import importlib.util, sys
from types import SimpleNamespace
spec = importlib.util.spec_from_file_location('runtime_probe', sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
try:
    module.wait_ready(SimpleNamespace(poll=lambda: None), int(sys.argv[2]))
except RuntimeError as error:
    if str(error) == 'READINESS_REDIRECT_BLOCKED':
        print('REDIRECT_BLOCKED')
    else:
        sys.exit(1)
else:
    sys.exit(1)
""",
                str(SCRIPT_DIR / "check_injected_runtime_faults.py"),
                str(server.server_port),
            ],
            env={
                **{key: os.environ[key] for key in ("PATH",) if key in os.environ},
                "PYTHONPATH": str(SCRIPT_DIR.parent / "src"),
            },
            capture_output=True,
            timeout=10,
            check=False,
        )
        assert result.returncode == 0 and result.stdout == b"REDIRECT_BLOCKED\n"
        assert paths == ["/actuator/health"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
