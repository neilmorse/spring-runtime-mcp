#!/usr/bin/env python3
"""Run explicitly authorized, disposable Spring Boot acceptance benchmarks."""

from __future__ import annotations

import argparse
import asyncio
import functools
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, TextIO

from runtime_benchmarks.acceptance import CASES
from runtime_benchmarks.targets import (
    IMAGES,
    MATRIX,
    BenchmarkError,
    build_application,
    build_image,
    launch,
)

from spring_runtime_mcp import __version__


def _run_case(case: str, image_cache: dict[str, str]) -> dict[str, Any]:
    target = MATRIX["targets"]["petclinic" if case == "petclinic-drift" else case]
    java = target["java"]
    report: dict[str, Any] = {
        "case": case,
        "target": target,
        "jdkImage": IMAGES[java],
        "checks": [],
    }
    if case == "trainticket-db":
        report.update(
            {"databaseImage": IMAGES["mysql"], "buildImage": IMAGES["maven8"]}
        )
    try:
        with TemporaryDirectory(prefix="spring-mcp-runtime-") as temporary:
            work = Path(temporary)
            command = build_application(case, target, work)
            if java not in image_cache:
                scratch = work / "image"
                scratch.mkdir()
                image_cache[java] = build_image(java, scratch)
            run = functools.partial(launch, image_cache[java], command, work)
            asyncio.run(CASES[case](run, report))
        report["status"] = "passed"
    except BenchmarkError as error:
        report["status"] = "blocked" if error.blocked else "failed"
        report["reasonCode"] = error.code
    except OSError:
        report["status"] = "blocked"
        report["reasonCode"] = "LOCAL_IO"
    return report


def _save(output: TextIO, report: dict[str, Any]) -> None:
    output.seek(0)
    json.dump(report, output, indent=2)
    output.write("\n")
    output.truncate()
    output.flush()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=(*CASES, "all"), required=True)
    parser.add_argument("--output", type=Path, required=True, help="A new JSON file.")
    args = parser.parse_args()
    selected = list(CASES) if args.case == "all" else [args.case]
    try:
        output = args.output.expanduser().open("x", encoding="utf-8")
    except OSError:
        print(
            "Cannot create a new benchmark report at the requested path.",
            file=sys.stderr,
        )
        return 1

    report: dict[str, Any] = {
        "startedAt": datetime.now(UTC).isoformat(),
        "mcpVersion": __version__,
        "pythonImage": IMAGES["python"],
        "selected": selected,
        "referenceCases": MATRIX["referenceCases"],
        "status": "incomplete",
        "cases": [],
    }
    images: dict[str, str] = {}
    with output:
        _save(output, report)
        for case in selected:
            print(f"{case}: running", file=sys.stderr, flush=True)
            result = _run_case(case, images)
            report["cases"].append(result)
            _save(output, report)
            outcome = result.get("reasonCode", result["status"])
            print(
                f"{case}: {result['status']} ({outcome})", file=sys.stderr, flush=True
            )
        states = {case["status"] for case in report["cases"]}
        if "failed" in states:
            report["status"] = "failed"
        elif "blocked" in states:
            report["status"] = "blocked"
        else:
            report["status"] = "passed"
        report["completedAt"] = datetime.now(UTC).isoformat()
        _save(output, report)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
