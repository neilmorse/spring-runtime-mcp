"""Opt-in source overlay for the pinned disposable JHipster acceptance target.

Verify official versioned source hashes, apply the reviewable patch, and compile
with optional compile-only inputs. Never modify Maven's jars or the native POM.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples/project-matrix"
BASE = "https://raw.githubusercontent.com/springdoc/springdoc-openapi/v3.1.1/"
SOURCES = {
    "springdoc-openapi-starter-common/src/main/java/org/springdoc/core/configuration/SpringDocConfiguration.java": "76676b0c2d11a26f286ba7afc4f0eca8c8a04271f62eefa3c95df639284bc776",
    "springdoc-openapi-starter-common/src/main/java/org/springdoc/core/configurer/SpringdocActuatorBeanFactoryConfigurer.java": "0489985111c09b3c8de546673b2308e533981e20b0f779ee9f679361f7a30dfe",
    "springdoc-openapi-starter-webmvc-api/src/main/java/org/springdoc/webmvc/api/MultipleOpenApiActuatorResource.java": "f4ca007ef9d3abbde3046b9b5f749b8b4fa1f788cbca9e8459d573dcbcfb469f",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    project = args.project.resolve()
    revision = subprocess.check_output(
        ["git", "-C", str(project), "rev-parse", "HEAD"], text=True
    ).strip()
    assert (
        revision
        == json.loads((FIXTURE / "projects.json").read_text())["jhipster"]["revision"]
    )
    build = project / "target/springdoc-patch-build"
    source = build / "source"
    cache = build / "original"
    for name, expected in SOURCES.items():
        original = cache / name
        if not original.exists():
            if args.offline:
                raise RuntimeError("PATCH_SOURCE_NOT_CACHED")
            original.parent.mkdir(parents=True, exist_ok=True)
            with urlopen(BASE + name, timeout=30) as response:
                content = response.read(128 * 1024 + 1)
            if hashlib.sha256(content).hexdigest() != expected:
                raise RuntimeError("PATCH_SOURCE_HASH_MISMATCH")
            original.write_bytes(content)
        if digest(original) != expected:
            raise RuntimeError("PATCH_SOURCE_HASH_MISMATCH")
        destination = source / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, destination)
    patch = FIXTURE / "springdoc-3.1.1-diagnostics.patch"
    subprocess.run(
        ["patch", "--batch", "--forward", "-p1", "-i", str(patch)],
        cwd=source,
        check=True,
    )
    shutil.copyfile(FIXTURE / "springdoc-compile-pom.xml", build / "pom.xml")
    subprocess.run(
        [
            "mvn",
            "-B",
            "-q",
            "--no-transfer-progress",
            *(["--offline"] if args.offline else []),
            "-f",
            str(build / "pom.xml"),
            "org.apache.maven.plugins:maven-dependency-plugin:3.8.1:build-classpath",
            "-Dmdep.outputFile=" + str(build / "classpath.txt"),
        ],
        check=True,
    )
    output = project / "target/springdoc-patched-classes"
    if output.exists():
        shutil.rmtree(output)
    output.mkdir()
    runtime = (project / "classpath.txt").read_text().strip()
    compile_only = (build / "classpath.txt").read_text().strip()
    subprocess.run(
        [
            "javac",
            "-proc:none",
            "-parameters",
            "--release",
            "17",
            "-cp",
            runtime + os.pathsep + compile_only,
            "-d",
            str(output),
            *[str(source / name) for name in SOURCES],
        ],
        check=True,
    )
    manifest = {
        "upstreamVersion": "3.1.1",
        "sourceHashes": SOURCES,
        "patchSha256": digest(patch),
        "classes": {
            str(p.relative_to(output)): digest(p)
            for p in sorted(output.rglob("*.class"))
        },
        "compileOnlyDependenciesAddedToRuntime": False,
    }
    (output / "patch-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Prepared verified springdoc overlay:", len(manifest["classes"]), "classes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
