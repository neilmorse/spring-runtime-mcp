"""Local, explicitly registered file evidence; no process identity is inferred."""

from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path
from typing import Any


def _digest(root: Path, relative: Path) -> str | None:
    if (
        relative.is_absolute()
        or not relative.parts
        or any(part in (".", "..") for part in relative.parts)
    ):
        return None
    if not hasattr(os, "O_NOFOLLOW"):
        return None
    descriptors: list[int] = []
    try:
        directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        descriptors.append(directory)
        for part in relative.parts[:-1]:
            directory = os.open(
                part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory
            )
            descriptors.append(directory)
        fd = os.open(
            relative.parts[-1],
            os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=directory,
        )
        descriptors.append(fd)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            return None
        digest = hashlib.sha256()
        while chunk := os.read(fd, 1024 * 1024):
            digest.update(chunk)
        after = os.fstat(fd)
        if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ):
            return None
        return digest.hexdigest()
    except OSError:
        return None
    finally:
        for fd in reversed(descriptors):
            os.close(fd)


def capture_snapshot(
    project: Path,
    source_files: list[Path],
    artifact: Path,
    *,
    build_exit_code: int | None = None,
) -> dict[str, Any]:
    """Hash only registered paths; a caller's exit code never proves provenance."""
    ordered = sorted(source_files, key=lambda path: path.as_posix())
    source_hashes = [(path.as_posix(), _digest(project, path)) for path in ordered]
    source_hash: str | None = None
    if (
        ordered
        and len(set(ordered)) == len(ordered)
        and all(value is not None for _, value in source_hashes)
    ):
        digest = hashlib.sha256()
        for name, value in source_hashes:
            assert value is not None
            digest.update(name.encode("utf-8"))
            digest.update(b"\0")
            digest.update(value.encode("ascii"))
            digest.update(b"\0")
        source_hash = digest.hexdigest()
    artifact_hash = _digest(project, artifact)
    return {
        "source": {"sha256": source_hash, "registeredCount": len(ordered)},
        "localArtifact": {"sha256": artifact_hash},
        "build": {
            "exitCode": build_exit_code,
            "outcome": (
                "unknown"
                if build_exit_code is None
                else "success"
                if build_exit_code == 0
                else "failed"
            ),
            "evidence": "callerReported",
            "artifactProducedByBuild": "unknown",
        },
        "runtimeIdentity": {"state": "notCollected", "sha256": None},
    }


def compare_snapshots(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Compare content only when both explicitly registered snapshots are complete."""

    def changed(section: str) -> bool | None:
        left, right = before[section]["sha256"], after[section]["sha256"]
        return None if left is None or right is None else left != right

    return {
        "sourceChanged": changed("source"),
        "localArtifactChanged": changed("localArtifact"),
        "runtimeIdentityComparison": "unknown",
    }
