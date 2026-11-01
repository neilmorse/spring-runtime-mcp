"""Exercise build faults and stale runtime using disposable demo copies.

Only fixed, aggregated evidence is persisted. Maven runs offline; no business
endpoint is requested. Use --output to select a new result file.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import selectors
import socket
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_evidence import capture_snapshot, compare_snapshots
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from spring_runtime_mcp.models.common import NormalizationError

from spring_runtime_mcp.policy.output_guard import ensure_safe_output

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples/spring-boot-demo"
JAVA = Path("src/main/java/example")
JAR = Path("target/spring-runtime-mcp-demo-0.1.0.jar")


def _env() -> dict[str, str]:
    return {
        key: os.environ[key]
        for key in ("PATH", "HOME", "JAVA_HOME", "LANG", "LC_ALL", "TMPDIR")
        if key in os.environ
    }


def _ports() -> tuple[int, int]:
    sockets = [socket.socket(), socket.socket()]
    try:
        for sock in sockets:
            sock.bind(("127.0.0.1", 0))
        return sockets[0].getsockname()[1], sockets[1].getsockname()[1]
    finally:
        for sock in sockets:
            sock.close()


def _build(project: Path) -> tuple[int, str]:
    env = dict(_env(), MAVEN_OPTS="-Xmx512m")
    result = subprocess.run(
        ["mvn", "-o", "-q", "-DskipTests", "package"],
        cwd=project,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=180,
        check=False,
    )
    return result.returncode, result.stdout


def _mcp(port: int, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "spring_runtime_mcp.cli",
            "--base-url",
            f"http://127.0.0.1:{port}",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=dict(_env(), PYTHONPATH=str(ROOT / "src")),
        bufsize=0,
    )
    try:
        assert proc.stdin is not None and proc.stdout is not None
        selector = selectors.DefaultSelector()
        selector.register(proc.stdout, selectors.EVENT_READ)
        pending = b""

        def send(value: dict[str, Any]) -> None:
            proc.stdin.write(json.dumps(value).encode() + b"\n")
            proc.stdin.flush()

        def request(
            identifier: int, method: str, params: dict[str, Any]
        ) -> tuple[dict[str, Any], int]:
            nonlocal pending
            send(
                {"jsonrpc": "2.0", "id": identifier, "method": method, "params": params}
            )
            deadline = time.monotonic() + 30
            while b"\n" not in pending:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not selector.select(remaining):
                    raise RuntimeError("MCP_FRAME_TIMEOUT")
                part = os.read(proc.stdout.fileno(), 65536)
                if not part:
                    raise RuntimeError("MCP_FRAME_CLOSED")
                pending += part
                if len(pending) > 1024 * 1024:
                    raise RuntimeError("MCP_FRAME_TOO_LARGE")
            line, pending = pending.split(b"\n", 1)
            frame = json.loads(line)
            if frame.get("id") != identifier or "result" not in frame:
                raise RuntimeError("MCP_PROTOCOL_ERROR")
            return frame["result"], len(line)

        request(
            1,
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "injected-build-faults", "version": "1"},
            },
        )
        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        listing, _ = request(2, "tools/list", {})
        schema = next(
            item["outputSchema"] for item in listing["tools"] if item["name"] == tool
        )
        result, frame_bytes = request(
            3, "tools/call", {"name": tool, "arguments": arguments}
        )
        envelope = result["structuredContent"]
        if (
            frame_bytes > 16384
            or len(result["content"]) != 1
            or json.loads(result["content"][0]["text"]) != envelope
        ):
            raise RuntimeError("MCP_WIRE_CHECK_FAILED")
        Draft202012Validator(schema).validate(envelope)
        ensure_safe_output(envelope)
        if result.get("isError", False) != (
            envelope["status"] in ("denied", "unavailable", "invalid", "too_large")
        ):
            raise RuntimeError("MCP_IS_ERROR_MISMATCH")
        proc.stdin.close()
        proc.wait(timeout=10)
    finally:
        _stop(proc)
    data = envelope.get("data") or {}
    return {
        "clientExitCode": proc.returncode,
        "frameBytes": frame_bytes,
        "isError": result.get("isError", False),
        "status": envelope.get("status"),
        "totalMatched": envelope.get("totalMatched"),
        "coverage": envelope.get("coverage"),
        "errorCodes": [item.get("code") for item in envelope.get("errors", [])],
        "inferences": [
            {"code": item.get("code"), "confidence": item.get("confidence")}
            for item in data.get("rootCauseInferences", [])
        ],
        "missingEvidenceLevels": [
            item.get("evidenceLevel") for item in data.get("missingInRuntime", [])
        ],
        "wireSchemaGuardVerified": True,
    }


def _start(
    project: Path,
    app_port: int,
    management_port: int,
    capture: bool,
    jar: Path | None = None,
) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        [
            "java",
            "-Xmx384m",
            "-jar",
            str(jar if jar is not None else project / JAR),
            f"--server.port={app_port}",
            f"--management.server.port={management_port}",
            "--server.address=127.0.0.1",
        ],
        stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
        cwd=project,
        env=_env(),
    )


def _wait_port(process: subprocess.Popen[bytes], port: int) -> bool:
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline and process.poll() is None:
        inodes: set[str] = set()
        for entry in Path(f"/proc/{process.pid}/fd").iterdir():
            try:
                target = os.readlink(entry)
            except FileNotFoundError:
                continue
            if target.startswith("socket:[") and target.endswith("]"):
                inodes.add(target[8:-1])
        for table in (Path("/proc/net/tcp"), Path("/proc/net/tcp6")):
            for line in table.read_text().splitlines()[1:]:
                fields = line.split()
                if (
                    fields[3] == "0A"
                    and int(fields[1].split(":")[1], 16) == port
                    and fields[9] in inodes
                ):
                    return True
        time.sleep(0.2)
    return False


def _stop(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)


def _copy(parent: Path, name: str) -> Path:
    project = parent / name
    shutil.copytree(
        DEMO, project, ignore=shutil.ignore_patterns("target", "transcript.jsonl")
    )
    return project


def _run(output_path: Path, results: dict[str, Any]) -> int:
    with tempfile.TemporaryDirectory(prefix="mcp-build-faults-") as directory:
        parent = Path(directory)
        for name, source, marker in [
            ("syntax", "package example; class Broken { void f( }", "illegal start"),
            (
                "type",
                'package example; class Broken { int value = "text"; }',
                "incompatible types",
            ),
        ]:
            project = _copy(parent, name)
            (project / JAVA / "Broken.java").write_text(source, encoding="utf-8")
            code, output = _build(project)
            results["cases"][name] = {
                "build": {
                    "exitCode": code,
                    "expectedDiagnosticMarker": marker in output,
                },
                "mcp": {
                    "called": False,
                    "reason": "No new executable runtime was produced.",
                },
            }
        for name, source, marker in [
            (
                "missing_bean",
                "package example; import org.springframework.stereotype.Component; @Component class Broken { Broken(Unprovided value) {} } interface Unprovided {}",
                "No qualifying bean of type",
            ),
            (
                "duplicate_bean",
                'package example; import org.springframework.context.annotation.*; @Configuration class Broken { @Bean String conflictOne(){return "a";} @Bean String conflictTwo(){return "b";} @Bean Integer consumer(String value){return 1;} }',
                "expected single matching bean but found 2",
            ),
        ]:
            project = _copy(parent, name)
            (project / JAVA / "Broken.java").write_text(source, encoding="utf-8")
            code, _ = _build(project)
            case: dict[str, Any] = {"build": {"exitCode": code}}
            results["cases"][name] = case
            if code != 0:
                case["launch"] = {"attempted": False}
                continue
            app_port, management_port = _ports()
            process = _start(project, app_port, management_port, True)
            try:
                launch_output, _ = process.communicate(timeout=45)
                case["launch"] = {
                    "exitCode": process.returncode,
                    "expectedDiagnosticMarker": marker.encode() in launch_output,
                }
                # Keep the endpoint unavailable even if another process races for this port.
                with socket.socket() as reservation:
                    reservation.bind(("127.0.0.1", management_port))
                    case["mcp"] = _mcp(
                        management_port, "springboot_diagnose_health", {}
                    )
            finally:
                _stop(process)
                case["cleanup"] = {"processExited": process.poll() is not None}
        project = _copy(parent, "stale_runtime")
        code, _ = _build(project)
        case = {"build": {"exitCode": code}}
        results["cases"]["stale_runtime"] = case
        if code == 0:
            sources = sorted(
                path.relative_to(project) for path in (project / JAVA).glob("*.java")
            ) + [Path("pom.xml")]
            baseline = capture_snapshot(project, sources, JAR, build_exit_code=code)
            launch_jar = parent / "launched-copy.jar"
            shutil.copyfile(project / JAR, launch_jar)
            app_port, management_port = _ports()
            process = _start(project, app_port, management_port, False, jar=launch_jar)
            try:
                ready = _wait_port(process, management_port)
                case["launch"] = {"managementPortOpened": ready}
                if ready:
                    controller = project / JAVA / "OrderController.java"
                    controller.write_text(
                        controller.read_text(encoding="utf-8").replace(
                            "/orders/{id}", "/new-orders/{id}"
                        ),
                        encoding="utf-8",
                    )
                    modified_at = datetime.now(timezone.utc).isoformat()
                    case["source"] = {
                        "sourceModifiedAt": modified_at,
                        "routeChangedAfterLaunch": "/new-orders/{id}"
                        in controller.read_text(encoding="utf-8"),
                    }
                    case["mcpOldRoute"] = _mcp(
                        management_port,
                        "springboot_verify_mappings",
                        {"pathPattern": "/orders/{id}", "httpMethod": "GET"},
                    )
                    case["mcpNewRoute"] = _mcp(
                        management_port,
                        "springboot_verify_mappings",
                        {"pathPattern": "/new-orders/{id}", "httpMethod": "GET"},
                    )
                    unbuilt = capture_snapshot(project, sources, JAR)
                    case["mcpDrift"] = _mcp(
                        management_port,
                        "springboot_detect_drift",
                        {
                            "expectedRoutes": [
                                {"path": "/new-orders/{id}", "httpMethod": "GET"}
                            ],
                            "sourceModifiedAt": modified_at,
                            "sourceRevision": "injected-source-only",
                        },
                    )
                    rebuild_code, _ = _build(project)
                    rebuilt = capture_snapshot(
                        project, sources, JAR, build_exit_code=rebuild_code
                    )
                    case["localEvidence"] = {
                        "baseline": baseline,
                        "sourceChangedWithoutBuild": unbuilt,
                        "afterRebuild": rebuilt,
                        "beforeBuildComparison": compare_snapshots(baseline, unbuilt),
                        "afterBuildComparison": compare_snapshots(baseline, rebuilt),
                    }
                    if rebuild_code == 0 and _wait_port(process, management_port):
                        case["mcpOldRouteAfterRebuild"] = _mcp(
                            management_port,
                            "springboot_verify_mappings",
                            {"pathPattern": "/orders/{id}", "httpMethod": "GET"},
                        )
                        case["mcpNewRouteAfterRebuild"] = _mcp(
                            management_port,
                            "springboot_verify_mappings",
                            {"pathPattern": "/new-orders/{id}", "httpMethod": "GET"},
                        )
            finally:
                _stop(process)
                case["cleanup"] = {"processExited": process.poll() is not None}
    checks = results["cases"]
    ok = all(
        checks[n]["build"]["exitCode"] != 0
        and checks[n]["build"]["expectedDiagnosticMarker"]
        for n in ("syntax", "type")
    )
    ok = ok and all(
        checks[n].get("launch", {}).get("exitCode", 0) != 0
        and checks[n]["launch"].get("expectedDiagnosticMarker")
        and checks[n].get("mcp", {}).get("status") == "unavailable"
        and "TARGET_CONNECTION_REFUSED" in checks[n]["mcp"]["errorCodes"]
        and checks[n].get("cleanup", {}).get("processExited")
        for n in ("missing_bean", "duplicate_bean")
    )
    stale = checks["stale_runtime"]
    drift = stale.get("mcpDrift", {})
    ok = ok and stale.get("launch", {}).get("managementPortOpened", False)
    ok = ok and stale.get("source", {}).get("routeChangedAfterLaunch", False)
    ok = ok and stale.get("mcpOldRoute", {}).get("totalMatched") == 1
    ok = ok and stale.get("mcpNewRoute", {}).get("totalMatched") == 0
    ok = ok and any(
        row.get("code") == "POSSIBLE_NOT_RESTARTED"
        and row.get("confidence") == "candidate"
        for row in drift.get("inferences", [])
    )
    ok = ok and "observed" in drift.get("missingEvidenceLevels", [])
    evidence = stale.get("localEvidence", {})
    ok = ok and evidence.get("beforeBuildComparison", {}).get("sourceChanged") is True
    ok = (
        ok
        and evidence.get("beforeBuildComparison", {}).get("localArtifactChanged")
        is False
    )
    ok = ok and evidence.get("afterBuildComparison", {}).get("sourceChanged") is True
    ok = (
        ok
        and evidence.get("afterBuildComparison", {}).get("localArtifactChanged") is True
    )
    ok = (
        ok
        and evidence.get("afterRebuild", {}).get("build", {}).get("outcome")
        == "success"
    )
    ok = ok and stale.get("mcpOldRouteAfterRebuild", {}).get("totalMatched") == 1
    ok = ok and stale.get("mcpNewRouteAfterRebuild", {}).get("totalMatched") == 0
    ok = ok and stale.get("cleanup", {}).get("processExited", False)
    results["passed"] = bool(ok)
    results["failureCodes"] = [] if ok else ["EXPECTED_OBSERVATIONS_MISMATCH"]
    results["verifiedAt"] = datetime.now(timezone.utc).isoformat()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8") as stream:
        json.dump(results, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(f"Wrote {output_path}; passed: {results['passed']}")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "examples/injected-faults/build-results.json",
    )
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Output already exists; choose a new --output path.")
    results: dict[str, Any] = {
        "cases": {},
        "limitations": [
            "Build and launch observations come from local Maven and launcher, not MCP.",
            "MCP cannot inspect uncompiled source or compiler diagnostics.",
            "The loopback listener is checked against the launched process using Linux /proc; port allocation has a race.",
            "sourceRevision is caller-supplied, not an observed runtime build identity.",
        ],
    }
    try:
        return _run(args.output, results)
    except (
        OSError,
        subprocess.TimeoutExpired,
        RuntimeError,
        ValidationError,
        NormalizationError,
        json.JSONDecodeError,
        KeyError,
        StopIteration,
    ) as exc:
        # Persist only a fixed classification, never exception text or remote output.
        results.update(
            passed=False,
            failureCodes=["EXECUTION_OR_VALIDATION_FAILED"],
            verifiedAt=datetime.now(timezone.utc).isoformat(),
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(results, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        print(f"Wrote {args.output}; passed: False ({type(exc).__name__})")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
