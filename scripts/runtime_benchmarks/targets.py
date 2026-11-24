"""Provision pinned applications in disposable directories and Docker networks."""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from zipfile import BadZipFile, ZipFile

from .fixture_tls import write_certificates

ASSETS = Path(__file__).resolve().parent
ROOT = ASSETS.parents[1]
MATRIX = json.loads((ASSETS / "matrix.json").read_text())
PORT = 18081
IMAGES = MATRIX["images"]
STATION_TOKEN_ENV = "BENCHMARK_STATION_TOKEN"

_HEALTH_HTTP = (
    "import os, sys\n"
    "from http.client import HTTPConnection, HTTPSConnection\n"
    "port, scheme = sys.argv[1:]\n"
    f"token = os.environ.get({STATION_TOKEN_ENV!r})\n"
    "if scheme not in ('http', 'https') or (token and scheme != 'https'): sys.exit(2)\n"
    "connection_type = HTTPSConnection if scheme == 'https' else HTTPConnection\n"
    "connection = connection_type('127.0.0.1', int(port), timeout=5)\n"
    "try:\n"
    "    headers = {'Authorization': 'Bearer ' + token} if token else {}\n"
    "    connection.request('GET', '/actuator/health', headers=headers)\n"
    "    print(connection.getresponse().status)\n"
    "finally:\n"
    "    connection.close()\n"
)


class BenchmarkError(Exception):
    def __init__(self, code: str, *, blocked: bool = False) -> None:
        super().__init__(code)
        self.code = code
        self.blocked = blocked


def _run(
    argv: list[str],
    failure: str,
    *,
    cwd: Path = ROOT,
    timeout: int = 120,
    env: dict[str, str] | None = None,
) -> bytes:
    try:
        return subprocess.run(
            argv,
            check=True,
            cwd=cwd,
            env=env,
            timeout=timeout,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        raise BenchmarkError(failure, blocked=True) from None


def _git_checkout(target: dict[str, str], source: Path) -> None:
    source.mkdir()
    _run(["git", "init", "-q"], "GIT_INIT", cwd=source)
    _run(
        ["git", "fetch", "-q", "--depth=1", target["repository"], target["revision"]],
        "SOURCE_FETCH",
        cwd=source,
    )
    _run(
        ["git", "checkout", "-q", "--detach", "FETCH_HEAD"],
        "SOURCE_CHECKOUT",
        cwd=source,
    )
    revision = _run(["git", "rev-parse", "HEAD"], "SOURCE_REVISION", cwd=source)
    if revision.strip().decode("ascii") != target["revision"]:
        raise BenchmarkError("SOURCE_REVISION")


def _replace(path: Path, needle: str, replacement: str) -> None:
    original = path.read_text()
    if original.count(needle) != 1:
        raise BenchmarkError("SOURCE_OVERLAY_MISMATCH")
    path.write_text(original.replace(needle, replacement))


_MAVEN = ["mvn", "-B", "-q", "--no-transfer-progress", "-DskipTests"]
_PETCLINIC_MAIN = "org.springframework.samples.petclinic.PetClinicApplication"


def _petclinic_command(case: str, target: dict[str, str], work: Path) -> list[str]:
    source = work / "source"
    _git_checkout(target, source)
    overlays = {
        "petclinic-drift": "DriftConfiguration",
        "petclinic-chaos": "ChaosConfiguration",
    }
    overlay = overlays.get(case)
    if case == "petclinic-chaos":
        _replace(
            source / "pom.xml",
            "\n  <dependencies>\n",
            "\n  <dependencies>\n"
            "    <dependency>\n"
            "      <groupId>de.codecentric</groupId>\n"
            "      <artifactId>chaos-monkey-spring-boot</artifactId>\n"
            f"      <version>{target['chaosMonkey']}</version>\n"
            "    </dependency>\n",
        )
    output = work / "runtime"
    _run(
        [
            *_MAVEN,
            "compile",
            "org.apache.maven.plugins:maven-dependency-plugin:3.8.1:copy-dependencies",
            "-DincludeScope=runtime",
            f"-DoutputDirectory={output / 'lib'}",
        ],
        "PETCLINIC_BUILD",
        cwd=source,
        timeout=600,
    )
    classes = output / "classes"
    shutil.copytree(source / "target/classes", classes)
    java_files = [ASSETS / "BenchmarkLauncher.java"]
    if overlay:
        java_files.append(ASSETS / f"{overlay}.java")
    _run(
        [
            "javac",
            "--release",
            "17",
            "-classpath",
            f"{classes}:{output / 'lib'}/*",
            "-d",
            str(classes),
            *map(str, java_files),
        ],
        "BENCHMARK_LAUNCHER_BUILD",
    )
    return [
        "-cp",
        "/work/runtime/classes:/work/runtime/lib/*",
        "benchmark.BenchmarkLauncher",
        _PETCLINIC_MAIN,
        f"benchmark.{overlay}" if overlay else "-",
    ]


def _train_command(target: dict[str, str], work: Path) -> list[str]:
    source = work / "source"
    _git_checkout(target, source)
    jwt_source = (
        source / "ts-common/src/main/java/edu/fudan/common/security/jwt/JWTUtil.java"
    )
    signing_key = re.findall(
        r"(?m)^    private static String secretKey = [^\r\n]+;$", jwt_source.read_text()
    )
    if len(signing_key) != 1:
        raise BenchmarkError("SOURCE_OVERLAY_MISMATCH")
    _replace(
        jwt_source,
        signing_key[0],
        '    private static String secretKey = System.getenv("BENCHMARK_STATION_JWT_KEY");',
    )
    cache = Path.home() / ".m2/repository"
    cache.mkdir(parents=True, exist_ok=True)
    name = f"spring-mcp-build-{secrets.token_hex(8)}"
    args = [
        "--user",
        f"{os.getuid()}:{os.getgid()}",
        "--log-driver",
        "none",
        "-v",
        f"{source}:/source",
        "-v",
        f"{cache}:/maven-repository",
        "-w",
        "/source",
        IMAGES["maven8"],
        *_MAVEN,
        "-Dmaven.repo.local=/maven-repository",
        "-Duser.home=/tmp",
        "-pl",
        "ts-station-service",
        "-am",
        "package",
    ]
    with _container(args, name):
        _run(
            ["docker", "--context", "default", "start", "--attach", name],
            "TRAINTICKET_BUILD",
            timeout=900,
        )
    jar = source / "ts-station-service/target/ts-station-service-1.0.jar"
    if not jar.is_file():
        raise BenchmarkError("TRAINTICKET_JAR_MISSING", blocked=True)
    shutil.copyfile(jar, work / "runtime/application.jar")
    return ["-jar", "/work/runtime/application.jar"]


def build_application(case: str, target: dict[str, str], work: Path) -> list[str]:
    output = work / "runtime"
    output.mkdir()
    if case.startswith("petclinic"):
        return _petclinic_command(case, target, work)
    if case == "trainticket-db":
        return _train_command(target, work)
    jar = output / "application.jar"
    if case == "jvm-threads":
        source = work / "source"
        shutil.copytree(
            ASSETS / "thread-fixture", source, ignore=shutil.ignore_patterns("target")
        )
        _run([*_MAVEN, "package"], "THREAD_FIXTURE_BUILD", cwd=source, timeout=600)
        shutil.copyfile(source / "target/thread-acceptance-1.jar", jar)
        return ["-jar", "/work/runtime/application.jar"]
    if case == "webgoat":
        _run(
            ["curl", "-fsSL", "--max-time", "180", target["asset"], "-o", str(jar)],
            "WEBGOAT_DOWNLOAD",
            timeout=190,
        )
        with jar.open("rb") as handle:
            digest = hashlib.file_digest(handle, "sha256").hexdigest()
        if digest != target["sha256"]:
            raise BenchmarkError("WEBGOAT_DIGEST_MISMATCH")
        expanded = output / "webgoat"
        try:
            with ZipFile(jar) as archive:
                members = [
                    name for name in archive.namelist() if name.startswith("BOOT-INF/")
                ]
                archive.extractall(expanded, members)
        except BadZipFile:
            raise BenchmarkError("WEBGOAT_ARCHIVE") from None
        return [
            "-cp",
            "/work/runtime/webgoat/BOOT-INF/classes:/work/runtime/webgoat/BOOT-INF/lib/*",
            "org.owasp.webgoat.server.StartWebGoat",
        ]
    else:
        source = work / "source"
        _git_checkout(target, source)
        dependency = "    implementation group: 'org.springframework.boot', name: "
        web = f"{dependency}'spring-boot-starter-web'"
        _replace(
            source / "build.gradle",
            web,
            f"{web}\n{dependency}'spring-boot-starter-actuator'",
        )
        _run(
            ["sh", "./gradlew", "--no-daemon", "bootJar"],
            "VULNERABLEAPP_BUILD",
            cwd=source,
            timeout=900,
        )
        shutil.copyfile(source / "build/libs/VulnerableApp-1.0.0.jar", jar)
    return ["-jar", "/work/runtime/application.jar"]


def build_image(java: str, scratch: Path) -> str:
    requirements = _run(
        ["uv", "export", "--locked", "--no-dev", "--no-emit-project", "--no-header"],
        "PYTHON_LOCK_EXPORT",
    )
    (scratch / "requirements.txt").write_bytes(requirements)
    shutil.copyfile(ASSETS / "Dockerfile", scratch / "Dockerfile")
    image = (
        _run(
            [
                "docker",
                "--context",
                "default",
                "build",
                "--quiet",
                "--build-arg",
                f"JDK={IMAGES[java]}",
                "--build-arg",
                f"PYTHON={IMAGES['python']}",
                str(scratch),
            ],
            "RUNTIME_IMAGE_BUILD",
            timeout=600,
        )
        .strip()
        .decode("ascii")
    )
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", image):
        raise BenchmarkError("RUNTIME_IMAGE_ID", blocked=True)
    return image


@dataclass(frozen=True)
class Application:
    container: str
    mount: Path
    scheme: Literal["http", "https"] = "http"

    @property
    def origin(self) -> str:
        return f"{self.scheme}://127.0.0.1:{PORT}"

    def exec(self, *args: str) -> list[str]:
        return ["docker", "--context", "default", "exec", "-i", self.container, *args]

    def health_http(self) -> int:
        status = _run(
            self.exec("python", "-c", _HEALTH_HTTP, str(PORT), self.scheme),
            "HEALTH_HTTP",
            timeout=12,
        )
        if not re.fullmatch(rb"[1-5][0-9]{2}\n", status):
            raise BenchmarkError("HEALTH_HTTP_STATUS")
        return int(status)

    def _wait_ready(self) -> None:
        deadline = time.monotonic() + 100
        while time.monotonic() < deadline:
            state = _docker(
                ["inspect", "--format", "{{.State.Running}}", self.container]
            )
            if state.strip() != b"true":
                raise BenchmarkError("APPLICATION_EXITED", blocked=True)
            try:
                status = self.health_http()
            except BenchmarkError as error:
                if error.code != "HEALTH_HTTP":
                    raise
                time.sleep(0.5)
            else:
                if 300 <= status < 400:
                    raise BenchmarkError("READINESS_REDIRECT_BLOCKED", blocked=True)
                return
        raise BenchmarkError("APPLICATION_READY_TIMEOUT", blocked=True)


def _docker(args: list[str], *, env: dict[str, str] | None = None) -> bytes:
    return _run(["docker", "--context", "default", *args], "DOCKER_COMMAND", env=env)


@contextmanager
def _container(
    args: list[str], name: str, *, env: dict[str, str] | None = None
) -> Iterator[None]:
    _docker(["create", "--name", name, *args], env=env)
    try:
        yield
    finally:
        _docker(["rm", "--force", "--volumes", name])


@contextmanager
def launch(
    image: str,
    launch_args: list[str],
    work: Path,
    exposure: str,
    properties: dict[str, str],
    *,
    network: str = "none",
    private_environment: dict[str, str] | None = None,
    management_tls: Path | None = None,
    webgoat: bool = False,
    shared_management: bool = False,
) -> Iterator[Application]:
    name = f"spring-mcp-bench-{secrets.token_hex(8)}"
    private = work / "runtime"
    variables = dict(private_environment or {})
    docker_env = ["--env", "PYTHONPATH=/repo/src"]
    settings = {
        "server.address": "127.0.0.1",
        "server.port": "0",
        "management.server.address": "127.0.0.1",
        "management.server.port": str(PORT),
        "management.endpoints.web.base-path": "/actuator",
        "management.endpoints.web.exposure.include": exposure,
        "management.endpoints.access.max-permitted": "read-only",
        "management.endpoints.jmx.exposure.exclude": "*",
        "management.endpoint.env.show-values": "never",
        "management.endpoint.configprops.show-values": "never",
        "management.endpoint.health.show-details": "never",
        "spring.jmx.enabled": "false",
        "spring.main.banner-mode": "off",
        "logging.level.root": "ERROR",
        **properties,
    }
    scheme: Literal["http", "https"] = "http"
    if management_tls is not None:
        scheme = "https"
        password = secrets.token_urlsafe(32)
        write_certificates(management_tls, store_password=password.encode("ascii"))
        variables["BENCHMARK_TLS_STORE_PASSWORD"] = password
        docker_env.extend(
            [
                "--volume",
                f"{management_tls}:/work/tls:ro",
                "--env",
                "SSL_CERT_FILE=/work/tls/ca.pem",
            ]
        )
        settings.update(
            {
                "management.server.ssl.enabled": "true",
                "management.server.ssl.key-store": "file:/work/tls/server.p12",
                "management.server.ssl.key-store-type": "PKCS12",
                "management.server.ssl.key-store-password": "${BENCHMARK_TLS_STORE_PASSWORD}",
            }
        )
    for variable in variables:
        docker_env.extend(["--env", variable])
    environment = {**os.environ, **variables} if variables else None
    if shared_management:
        # The fixture counts management requests using the primary Tomcat access log.
        settings["server.port"] = settings.pop("management.server.port")
        del settings["management.server.address"]
    if webgoat:
        # The original launcher starts two applications with the same argv.
        # Attach management settings to WebGoat's own property source only.
        classes = private / "webgoat/BOOT-INF/classes"
        with (classes / "application-webgoat.properties").open("a") as profile:
            profile.write(
                "\n" + "".join(f"{key}={value}\n" for key, value in settings.items())
            )
        with (classes / "application-webwolf.properties").open("a") as profile:
            profile.write("\nserver.address=127.0.0.1\nserver.port=0\n")
        settings = {}
    args = [
        "--network",
        network,
        "--user",
        f"{os.getuid()}:{os.getgid()}",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--read-only",
        "--tmpfs",
        "/tmp:rw,nosuid,nodev",
        "--log-driver",
        "none",
        "--workdir",
        "/work/runtime",
        "--volume",
        f"{private}:/work/runtime",
        "--volume",
        f"{ROOT / 'src'}:/repo/src:ro",
        *docker_env,
        image,
        "java",
        "-Xmx512m",
        "-Djava.awt.headless=true",
        "-Duser.home=/work/runtime",
        "-Dspring.devtools.restart.enabled=false",
        *launch_args,
        *(f"--{key}={value}" for key, value in settings.items()),
    ]
    with _container(args, name, env=environment):
        _docker(["start", name])
        application = Application(name, private, scheme)
        application._wait_ready()
        yield application


@dataclass(frozen=True)
class Database:
    name: str
    network: str
    password: str

    def stop(self) -> None:
        _docker(["stop", "--time", "10", self.name])

    def start(self) -> None:
        _docker(["start", self.name])
        self.wait_ready()

    def wait_ready(self) -> None:
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            command = [
                "exec",
                self.name,
                "mysqladmin",
                "--connect-timeout=3",
                "--protocol=tcp",
                "-h",
                "127.0.0.1",
                "ping",
            ]
            try:
                _docker(command)
            except BenchmarkError:
                time.sleep(0.5)
            else:
                return
        raise BenchmarkError("MYSQL_READY_TIMEOUT", blocked=True)


@contextmanager
def database() -> Iterator[Database]:
    suffix = secrets.token_hex(8)
    instance = Database(
        f"station-db-{suffix}", f"spring-mcp-bench-{suffix}", secrets.token_hex(24)
    )
    environment = {
        **os.environ,
        "MYSQL_ROOT_PASSWORD": secrets.token_hex(24),
        "MYSQL_PASSWORD": instance.password,
    }
    _docker(["network", "create", "--internal", instance.network])
    try:
        args = [
            "--network",
            instance.network,
            "--network-alias",
            "station-db",
            "--log-driver",
            "none",
            "--env",
            "MYSQL_DATABASE=station",
            "--env",
            "MYSQL_USER=station",
            "--env",
            "MYSQL_PASSWORD",
            "--env",
            "MYSQL_ROOT_PASSWORD",
            IMAGES["mysql"],
        ]
        with _container(args, instance.name, env=environment):
            _docker(["start", instance.name])
            instance.wait_ready()
            yield instance
    finally:
        _docker(["network", "rm", instance.network])
