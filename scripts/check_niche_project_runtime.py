"""Opt-in acceptance for a disposable HertzBeat v1.7.3 checkout.

HertzBeat is a smaller but production-used observability platform. The manager
runs with its native embedded H2 database on loopback. A temporary operator
launcher adds a bounded startup buffer and a plain management Bearer filter;
no Spring Security or target source is replaced.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
import time
from pathlib import Path

from check_large_project_runtime import Acceptance, environment
from check_project_runtime import ready

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples/niche-project-matrix"
LAUNCHER = ROOT / "examples/large-project-matrix/LargeProjectLauncher.java"
JAVA17 = Path("/usr/lib/jvm/java-17-openjdk/bin/java")
JAVAC17 = JAVA17.with_name("javac")


class NicheAcceptance(Acceptance):
    def __init__(self, args: argparse.Namespace) -> None:
        super().__init__(args, fixture=FIXTURE)
        self.work = self.project / ".niche-diagnostics"
        self.work.mkdir(exist_ok=True)
        (self.work / "data").mkdir(exist_ok=True)
        (self.work / "config").mkdir(exist_ok=True)
        self.report["database"] = "embedded-H2-file"
        self.report["startupBufferEvents"] = 2048

    def prepare(self) -> None:
        revision = subprocess.check_output(
            ["git", "-C", str(self.project), "rev-parse", "HEAD"], text=True
        ).strip()
        if revision != self.config["revision"]:
            raise ValueError("UNEXPECTED_REVISION")
        module = self.project / self.config["module"]
        classpath_file = module / "classpath-runtime.txt"
        if not classpath_file.exists():
            raise ValueError("RUNTIME_CLASSPATH_MISSING")
        runtime = [
            entry
            for entry in classpath_file.read_text().strip().split(os.pathsep)
            if entry
        ]
        module_classes = [
            str(path)
            for path in sorted(self.project.glob("hertzbeat-*/target/classes"))
            if path.is_dir()
        ]
        manager_classes = str(module / "target/classes")
        if manager_classes in module_classes:
            module_classes.remove(manager_classes)
        sureness_source = (module / "src/main/resources/sureness.yml").read_text()
        marker = "# account info config"
        if marker not in sureness_source:
            raise ValueError("SURENESS_CONFIG_SHAPE_MISMATCH")
        sureness_source = sureness_source.replace(
            marker,
            "  - /actuator/**===*\n\n" + marker,
            1,
        )
        (self.work / "config/sureness.yml").write_text(sureness_source)
        self.report["surenessActuatorPermit"] = True
        self.classpath = os.pathsep.join(
            [str(self.work / "config"), manager_classes, *module_classes, *runtime]
        )
        artifacts = [Path(entry).name for entry in runtime]
        self.report["runtimeArtifacts"] = artifacts
        self.report["runtimeArtifactsSha256"] = hashlib.sha256(
            "\n".join(sorted(artifacts)).encode()
        ).hexdigest()
        self.report["classpathEntryCount"] = len(module_classes) + len(runtime) + 1
        compiled = subprocess.run(
            [
                str(JAVAC17),
                "-cp",
                self.classpath,
                "-d",
                str(self.work),
                str(self.fixture / "DiagnosticSecurity.java"),
                str(LAUNCHER),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.report["operatorLauncherCompileExit"] = compiled.returncode
        if compiled.returncode:
            print(compiled.stderr.decode(errors="replace")[:5000], file=sys.stderr)
            raise ValueError("OPERATOR_LAUNCHER_COMPILE_FAILED")
        properties = (self.fixture / "common.properties").read_text()
        properties += "\n" + (self.fixture / "hertzbeat.properties").read_text()
        properties += (
            f"\nserver.port={self.port}\n"
            f"management.server.port={self.management_port}\n"
            f"spring.datasource.url=jdbc:h2:file:{self.work}/data/hertzbeat;"
            "MODE=MYSQL;DB_CLOSE_ON_EXIT=FALSE\n"
        )
        (self.work / "application.properties").unlink(missing_ok=True)
        (self.work / "niche.properties").write_text(properties)

    def start(self) -> None:
        env = environment()
        env["JAVA_HOME"] = str(JAVA17.parent.parent)
        env.update(
            NICHE_DIAGNOSTICS_ADMIN=self.admin,
            NICHE_DIAGNOSTICS_USER=self.user,
        )
        self.process = subprocess.Popen(
            [
                str(JAVA17),
                "-Xmx1280m",
                "-Djava.awt.headless=true",
                "-Dspring.devtools.restart.enabled=false",
                "-cp",
                str(self.work) + os.pathsep + self.classpath,
                "LargeProjectLauncher",
                self.config["mainClass"],
                str(self.work / "niche.properties"),
                str(ROOT / "examples/project-matrix/logback-diagnostics.xml"),
            ],
            cwd=self.project,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        started = time.monotonic()
        port, java = ready(self.process, self.report, timeout=240)
        self.expect(port == self.management_port, "MANAGEMENT_PORT_MISMATCH")
        self.report["javaMajor"] = java
        self.report.setdefault("startupSeconds", []).append(
            round(time.monotonic() - started, 3)
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default="hertzbeat", choices=("hertzbeat",))
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--soak-seconds", type=int, default=180)
    args = parser.parse_args()
    if not 65 <= args.soak_seconds <= 600:
        parser.error("--soak-seconds must be between 65 and 600")
    return NicheAcceptance(args).run()


if __name__ == "__main__":
    raise SystemExit(main())
