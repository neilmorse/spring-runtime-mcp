"""Generate partial operator-side catalog and drift inputs from registered Java files."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

from spring_runtime_mcp.adapters.source_catalog import load_source_catalog
from spring_runtime_mcp.contracts.definitions import validate_arguments
from spring_runtime_mcp.models.common import AnalysisBudget
from spring_runtime_mcp.policy.output_guard import ensure_safe_output
from spring_runtime_mcp.policy.sanitization import SanitizerPipeline
from spring_runtime_mcp.transport.bounded_json import loads_bounded

ROOT = Path(__file__).resolve().parents[1]
MAX_FILE_BYTES = 262_144
MAX_TOTAL_BYTES = 2_097_152


def _environment() -> dict[str, str]:
    return {key: os.environ[key] for key in ("PATH",) if key in os.environ}


def _relative(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if (
        not value
        or len(value) > 256
        or path.is_absolute()
        or any(part in ("", ".", "..") for part in value.split("/"))
        or any(ord(char) < 32 or ord(char) == 127 for char in value)
        or "\\" in value
        or ":" in value
    ):
        raise ValueError("invalid registered path")
    return path


def _read_registered(root: Path, relative: PurePosixPath) -> bytes:
    if not hasattr(os, "O_NOFOLLOW"):
        raise ValueError("unsupported safe file access")
    descriptors: list[int] = []
    try:
        directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        descriptors.append(directory)
        for part in relative.parts[:-1]:
            directory = os.open(
                part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory
            )
            descriptors.append(directory)
        descriptor = os.open(
            relative.name,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=directory,
        )
        descriptors.append(descriptor)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_FILE_BYTES:
            raise ValueError("invalid registered file")
        chunks = bytearray()
        while chunk := os.read(
            descriptor, min(65_536, MAX_FILE_BYTES + 1 - len(chunks))
        ):
            chunks.extend(chunk)
            if len(chunks) > MAX_FILE_BYTES:
                raise ValueError("registered file limit")
        after = os.fstat(descriptor)
        if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ):
            raise ValueError("registered file changed")
        return bytes(chunks)
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _parse_registered(snapshots: dict[str, bytes]) -> dict[str, Any]:
    if shutil.which("javac") is None or shutil.which("java") is None:
        raise ValueError("JDK required")
    with tempfile.TemporaryDirectory(prefix="mcp-source-facts-") as temporary:
        work = Path(temporary)
        classes = work / "classes"
        classes.mkdir()
        subprocess.run(
            [
                "javac",
                "-J-Xmx256m",
                "-proc:none",
                "-d",
                str(classes),
                str(ROOT / "scripts/java/SourceFacts.java"),
            ],
            env=_environment(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
            check=True,
        )
        registered: list[str] = []
        for relative, content in snapshots.items():
            destination = work / "sources" / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
            registered.append(str(destination))
        result = subprocess.run(
            ["java", "-Xmx256m", "-cp", str(classes), "SourceFacts", *registered],
            env=_environment(),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=30,
            check=True,
        )
        return loads_bounded(result.stdout, max_bytes=1_048_576)


def generate(
    project: Path,
    sources: list[str],
    *,
    target_id: str,
    context_id: str,
    source_revision: str | None = None,
    condition_sources: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Return validated partial facts; never execute, compile or scan project code."""
    if not 1 <= len(sources) <= 256 or len(set(sources)) != len(sources):
        raise ValueError("invalid registered source set")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", target_id):
        raise ValueError("invalid target")
    if (
        not isinstance(context_id, str)
        or not 1 <= len(context_id) <= 256
        or any(ord(char) < 32 or ord(char) == 127 for char in context_id)
    ):
        raise ValueError("invalid context")
    registered: dict[str, bytes] = {}
    total_bytes = 0
    for value in sorted(sources):
        relative = _relative(value)
        if relative.suffix != ".java":
            raise ValueError("Java sources required")
        content = _read_registered(project, relative)
        total_bytes += len(content)
        if total_bytes > MAX_TOTAL_BYTES:
            raise ValueError("registered source limit")
        registered[value] = content
    extracted = _parse_registered(registered)
    if set(extracted) != {"types", "producers", "routes", "gaps"}:
        raise ValueError("invalid parser output")
    bindings = condition_sources or {}
    producers: list[dict[str, Any]] = []
    used_bindings: set[str] = set()
    source_paths = list(registered)
    for producer in extracted["producers"]:
        row = dict(producer)
        index = row.pop("sourceIndex")
        if type(index) is not int or not 0 <= index < len(source_paths):
            raise ValueError("invalid parser source index")
        identity = row["configurationClass"] + "#" + row["factoryMethod"]
        if identity in bindings:
            used_bindings.add(identity)
        row.update(
            contextId=context_id,
            sourceFile=source_paths[index],
            conditionSources=bindings.get(identity, []),
        )
        producers.append(row)
    if set(bindings) != used_bindings:
        raise ValueError("unmatched condition binding")
    catalog: dict[str, Any] = {
        "targetId": target_id,
        "types": extracted["types"],
        "producers": producers,
    }
    if source_revision is not None:
        catalog["sourceRevision"] = source_revision
    load_source_catalog(catalog, target_id=target_id, budget=AnalysisBudget())
    arguments: dict[str, Any] | None = None
    if producers or extracted["routes"]:
        arguments = {"targetId": target_id, "expectedScopeComplete": False}
        if producers:
            arguments["expectedBeans"] = [
                {
                    "name": row["beanName"],
                    "contextId": context_id,
                }
                for row in producers
            ]
        if extracted["routes"]:
            routes = {(row["path"], row["httpMethod"]) for row in extracted["routes"]}
            arguments["expectedRoutes"] = [
                {"path": path, "httpMethod": method, "contextId": context_id}
                for path, method in sorted(routes)
            ]
        if source_revision is not None:
            arguments["sourceRevision"] = source_revision
        validate_arguments(arguments, "springboot_detect_drift")
    gaps = {
        "SOURCE_SCOPE_PARTIAL",
        "RUNTIME_REGISTRATION_UNVERIFIED",
        *extracted["gaps"],
    }
    if any(not row["conditionSources"] for row in producers):
        gaps.add("CONDITION_SOURCES_UNBOUND")
    bundle = {
        "catalog": catalog,
        "driftArguments": arguments,
        "report": {
            "coverage": "partial",
            "gaps": sorted(gaps),
            "evidenceKind": "registered-source-ast",
            "runtimeIdentity": "notCollected",
            "driftArgumentsState": "generated" if arguments else "notGenerated",
            "registeredSources": [
                {"path": name, "sha256": hashlib.sha256(content).hexdigest()}
                for name, content in registered.items()
            ],
        },
    }
    pipeline = SanitizerPipeline()
    # The pipeline's object whitelist describes tool envelopes, not local
    # artifact keys. Apply its string rules to every projected leaf instead.
    pending: list[Any] = [bundle]
    while pending:
        item = pending.pop()
        if isinstance(item, dict):
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
        elif (
            isinstance(item, str)
            and pipeline.sanitize({"value": item}).get("value") != item
        ):
            raise ValueError("unsafe source facts")
    ensure_safe_output(bundle, sanitizer=pipeline)
    return bundle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--source", action="append", required=True)
    parser.add_argument("--target-id", default="local")
    parser.add_argument("--context-id", required=True)
    parser.add_argument("--source-revision")
    parser.add_argument(
        "--condition-sources", help="Registered JSON path relative to project root"
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.output_dir.exists() or args.output_dir.is_symlink():
            raise ValueError("output exists")
        bindings = None
        if args.condition_sources:
            bindings = loads_bounded(
                _read_registered(args.project_root, _relative(args.condition_sources)),
                max_bytes=MAX_FILE_BYTES,
            )
            if not isinstance(bindings, dict):
                raise ValueError("invalid condition bindings")
        bundle = generate(
            args.project_root,
            args.source,
            target_id=args.target_id,
            context_id=args.context_id,
            source_revision=args.source_revision,
            condition_sources=bindings,
        )
        args.output_dir.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=args.output_dir.parent) as temporary:
            staged = Path(temporary) / "facts"
            staged.mkdir()
            outputs = {
                "source-catalog.json": bundle["catalog"],
                "source-facts-report.json": bundle["report"],
            }
            if bundle["driftArguments"] is not None:
                outputs["drift-arguments.json"] = bundle["driftArguments"]
            for name, value in outputs.items():
                (staged / name).write_text(
                    json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
            staged.rename(args.output_dir)
    except (OSError, ValueError, subprocess.SubprocessError):
        print("SOURCE_FACTS_GENERATION_FAILED", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
