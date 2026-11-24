# Real Spring Boot acceptance benchmarks

Run this opt-in matrix from the repository root on Linux with a local Docker
Engine, Git, curl, Maven, a JDK 21 compiler, and uv. The VulnerableApp Gradle
build also needs a local JDK 17 toolchain. The first run needs access to the
pinned source repositories, dependency repositories, and image registry.
The default pytest and release workflows run separately offline.

```bash
uv sync --dev --locked
uv run --no-sync python scripts/run_runtime_benchmarks.py \
  --case all --output /tmp/spring-runtime-benchmarks.json
```

Use a fresh report path on each run. Select a single case with `--case`. The
runner prepares each target in a disposable directory and registers one
loopback Actuator origin with the MCP process. The
[target manifest](../scripts/runtime_benchmarks/matrix.json) pins upstream
commits, fixture versions, and images. It also records the SHA-256 of the upstream WebGoat jar.

| Case | Expected evidence |
| --- | --- |
| `jvm-threads` | Isolated Boot 3.4.8 fixture for an ordinary blocked thread, a monitor deadlock checked against the JVM, and a timed lock cycle that disappears after its workers finish. Verifies cursor reuse and counts thread-dump GETs. |
| `petclinic` | Owner controller and route, database health, Bean cursor continuation, buffered startup, and a single registered configuration key with hidden values. |
| `petclinic-drift` | The same Bean and route expectations across baseline, fault, and recovery, with a known slow startup Bean. |
| `petclinic-chaos` | A file-controlled Chaos Monkey toggle changes a test health indicator in the same JVM. The report checks HTTP 503 recovery, the declared component-to-Bean association and its dependency, and unknown Bean evidence when components are hidden. |
| `petclinic-rest` | The owner route in mappings and management OpenAPI, plus the projected `Owner` Schema. |
| `trainticket-db` | TrainTicket station-service mappings, Bean pagination, and health as its private database stops and restarts. This is a local dependency outage on Boot 2.3.12. The [original F3 experiment](https://fudanselab.github.io/research/MSFaultEmpiricalStudy/) uses Boot 1.5.3 and is indexed for reference. |
| `webgoat` | Native mappings and Flyway applied migrations. The management port is configured only for the WebGoat application in the upstream WebGoat/WebWolf launcher. |
| `vulnerableapp` | Health, Bean identity, and mappings with a same-BOM Actuator dependency in the temporary source copy. The mail health indicator is disabled for the isolated run. |

To run the JVM acceptance by itself, choose a fresh report path.

```bash
uv run --no-sync python scripts/run_runtime_benchmarks.py \
  --case jvm-threads --output /tmp/spring-runtime-jvm-threads.json
```

The JVM case builds the repository fixture and launches a separate disposable
JDK 21 container for each scenario. The initial diagnosis and its continuation
pages must use one thread-dump GET. Timed-wait recovery takes one additional GET
and must yield a fresh snapshot with zero observed cycles. The JSON report
contains scenario verdicts, request counts, and wire sizes.

Application containers publish no ports. Each MCP session runs in the same
container as its target. The TrainTicket containers share a private internal
network for database traffic. Management reads are fixed GETs. Target security
configuration remains active. TrainTicket's temporary checkout reads a
disposable signing key from the environment. Its management listener uses a
per-run PKCS12 identity for `127.0.0.1`. The MCP process and readiness probe
trust the run’s test CA for HTTPS. The certificate files are mounted read-only
and removed when the case exits. The case verifies anonymous
denial and authenticates through the original JWT filter. Queries to the
security teaching applications are limited to diagnostic metadata.

The report records each case as `passed`, `failed`, or `blocked`. A build,
download, startup, or local infrastructure failure is recorded with a fixed
reason code. A completed case must satisfy its diagnostic assertions, each
tool's public output Schema, text and structured result equality, and the
actual 16,384-byte tool-response limit. Sizes exclude the STDIO line delimiter.
The runner saves summary fields such as coverage, gaps, error codes, and frame
sizes. It discards raw Actuator data and logs. A selected case that fails or
is blocked makes the command exit nonzero. Other selected cases still run.
