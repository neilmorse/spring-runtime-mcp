# Larger public-project runtime acceptance — 2026-10-22

The final follow-up closes the five remaining diagnostic findings and passes
the JHipster **separate-management-port** case with a reviewable local springdoc
source patch: 18 calls, including OpenAPI 401/403 checks. Petclinic REST passes
15 calls again. See [final remediation](../../docs/audits/remaining-findings-remediation-2026-10-22.md)
and [reproduction below](#final-separate-port-remediation). Original unpatched
dependency failures and earlier alternative configurations remain historical records.

## Earlier follow-up

Follow-up remediation fixes the two diagnostic OpenAPI defects. Petclinic REST
now passes 15 calls; a JHipster **same-port** configuration retains native API
docs/JWT/Liquibase and passes 18 calls (552 beans). These are separate records:
[REST rerun](petclinic-rest-remediation-verification.json),
[JHipster same-port](jhipster-same-port-verification.json), and the
[repair report](../../docs/audits/openapi-project-matrix-remediation-2026-10-22.md).
The original unpatched separate-management-port JHipster integration remains blocked;
its original failure below is retained. No dependency jar was replaced.
The [follow-up investigation](../../docs/audits/unresolved-findings-investigation-2026-10-22.md)
adds a synthetic lifecycle comparison and a real separate-port experiment:
disabling Actuator-operation documentation permits startup, while the fixed
OpenAPI root still returns 404. This is a causal probe, not passing acceptance.

## Initial matrix (before OpenAPI remediation)

The user explicitly authorized additional public-project testing without the
previous traffic restriction. This is an opt-in real-runtime matrix, separate
from default offline pytest. Existing uncommitted diagnostic changes are kept.

| Project / variant | Pinned source commit | Native Boot | Main Java sources / compiled classes | Reported beans / dependencies | Result |
| --- | --- | --- | --- | --- | --- |
| [Spring Petclinic](https://github.com/spring-projects/spring-petclinic/tree/500158f732419217507c7656904b8e6aa1bcc0d6) | `500158f732419217507c7656904b8e6aa1bcc0d6` | 4.1.0 | 30 / 30 | 416 / 430 | 13 calls; acceptance passed |
| [Petclinic REST](https://github.com/spring-petclinic/spring-petclinic-rest/tree/afc8fc1d3b8ec8de69414482b3bd70a1da78cb95) | `afc8fc1d3b8ec8de69414482b3bd70a1da78cb95` | 4.1.1 | 87 / 126 | 474 / 568 | 15 calls; two OpenAPI checks failed |
| [JHipster Sample](https://github.com/jhipster/jhipster-sample-app/tree/6b000b5d23a36c45e01472471b84a44fa2464044), `api-docs` | `6b000b5d23a36c45e01472471b84a44fa2464044` | 4.1.1 | 81 / 91 | startup blocked | 0 calls; acceptance failed |
| Same JHipster source, `dev,diagnostics` without API docs | same commit | 4.1.1 | 81 / 91 | 486 / 514 | 15 calls; acceptance passed for this reduced scope |

All launched targets used **Java 21**, random loopback business and management
ports, and a distinct process-local H2 database. The selected runs record **43
tool calls** in [verification.json](verification.json). Passing acceptance means
the listed assertions held; Bean/conditions/startup/config evidence still has
explicit `partial` gaps. The original REST attempt is retained separately in
[petclinic-rest-initial-verification.json](petclinic-rest-initial-verification.json).

## Builds and modifications

All three original POMs compiled successfully with their native Boot parents and
dependency sets. No replacement POM, version override, added runtime dependency,
container image or front-end build was used. Petclinic REST's native OpenAPI
generator produced its API/DTO classes. Maven executed **compile** and runtime
classpath generation; upstream business tests were not executed.

The two Petclinic Java source trees are unchanged. JHipster's two-file
[namespace patch](jhipster-actuator-namespace.patch) moves its existing
management authorization patterns and SPA-filter exclusion from `/management`
to `/actuator`, matching the connector's fixed endpoint namespace. It preserves
the existing health exceptions, JWT resource-server validation and administrator
requirements. Anonymous Bean reads returned **401**, a valid non-admin JWT
returned **403**, and the locally signed admin JWT allowed diagnostic reads.
The synthetic signing key and tokens were generated in memory and not saved.

The external [launcher](ProjectDiagnosticsLauncher.java) starts each original
application configuration with buffered startup events and the corresponding
operator-owned properties file. It does not call business URLs or login, and
MCP sends only its registered GET reads. It does not execute the application's
`main` log/banner wrapper. Configuration limits exposure to diagnostic endpoints,
sets endpoint access to read-only, disables Docker Compose, DevTools, H2 console/
TCP and mail health checks, and keeps env/configprops values hidden. Logback
framework output is suppressed; the launcher exports only readiness and bounded
exception class / Bean identifiers on startup failure.

JHipster's reduced variant explicitly replaces the `dev` profile group with
`diagnostics` and disables API docs, avoiding both the failing API-docs integration
and the upstream `secret-samples` group. It keeps the original application and
JWT security chain, uses synchronous Liquibase over H2, and does not replace the
database with a mock. This variant is not proof that the full `api-docs` setup works.

## Observed coverage and failures

- Bean lookup, conditions, two pages from one cached snapshot, disjoint page
  IDs, known GET routes, database health, startup version/steps, config disabled
  by default, exact registered config metadata, profiles and cross-domain drift
  were exercised. Infrastructure references and graph/association limits remain
  visible as gaps. The 500-step startup cap produced explicit truncation.
- JHipster's reduced variant reported **8 APPLIED Liquibase change sets** with
  complete migration-tool coverage for that observed endpoint. This does not
  prove that no pending changes exist or that other databases work.
- Petclinic REST's live `Specialty` OpenAPI Schema query passed. The more complex
  owner operation failed with `NON_TREE_JSON`; `Owner` Schema failed with
  `OUTPUT_CONTRACT_VIOLATION`. Both failures remain failed in the report.
- An independent synthetic probe confirmed two diagnostic implementation defects:
  repeated local refs reuse a mutable `required` list in the projected output,
  and a business property called `description` has its **Schema object** cleared
  by the free-text sanitizer. No raw response was converted into a fixture.
- JHipster's `api-docs` + separate-management-port setup failed before MCP calls:
  `springdocBeanFactoryPostProcessor3` triggered creation of
  `JHipsterSpringDocGroupsConfiguration` and ended in `NoSuchMethodException`.
  The report retains only bounded exception types and Bean/class identifiers.
  This establishes a startup blocker for this integration setup, not a general
  claim that the project or a library is broken in every configuration.
- Petclinic REST returns HTTP **500** for an unexposed migration path. Its
  catch-all application exception advice maps generic exceptions to 500. MCP
  correctly returns `ENDPOINT_UNAVAILABLE` with no migration data. The initial
  harness wrongly required 404; the final expectation records the observed
  500 while still requiring a safe unavailable result. No security assertion
  or production test was weakened.

Every tool result is checked against its output schema, the output safety guard
and a full response measurement reserving a maximum-length request ID, server
metadata and duplicate text content. All processes are stopped in `finally`;
all saved runs confirm `targetProcessStopped=true`. There are no saved raw
endpoint bodies, JWTs, env value trees, target logs or target exception stacks.

The initial testing task did not fix the five previous review findings or its
two new OpenAPI defects. The follow-up above fixes the latter two only.
No release/deployment, non-loopback target, TLS, large
WebFlux application or full framework compatibility matrix is claimed.

## Reproduce

Clone the three source repositories into a disposable directory, check out the
exact commits in `projects.json`, and inspect their sources before execution.
Apply the namespace patch only to the disposable JHipster copy. From the
diagnostic repository root, with `PROJECT_MATRIX_WORK` pointing to that directory:

```bash
git -C "$PROJECT_MATRIX_WORK/jhipster" apply \
  "$PWD/examples/project-matrix/jhipster-actuator-namespace.patch"

for project in petclinic petclinic-rest; do
  MAVEN_OPTS='-Xmx512m -Djava.awt.headless=true' mvn -B -q --no-transfer-progress \
    -f "$PROJECT_MATRIX_WORK/$project/pom.xml" -DskipTests compile \
    org.apache.maven.plugins:maven-dependency-plugin:3.8.1:build-classpath \
    -Dmdep.includeScope=runtime \
    -Dmdep.outputFile="$PROJECT_MATRIX_WORK/$project/classpath.txt"
done

MAVEN_OPTS='-Xmx512m -Djava.awt.headless=true' mvn -B -q --no-transfer-progress \
  -f "$PROJECT_MATRIX_WORK/jhipster/pom.xml" '-Pdev,!webapp,!docker-compose' \
  -DskipTests -Dspotless.skip=true compile \
  org.apache.maven.plugins:maven-dependency-plugin:3.8.1:build-classpath \
  -Dmdep.includeScope=runtime \
  -Dmdep.outputFile="$PROJECT_MATRIX_WORK/jhipster/classpath.txt"
```

Run each case independently; failed acceptance exits 1 **and still saves a safe
summary**, so it must not be treated as a passed check:

```bash
uv run --no-sync python scripts/check_project_runtime.py \
  --name petclinic --project "$PROJECT_MATRIX_WORK/petclinic" \
  --output "$PROJECT_MATRIX_WORK/petclinic-verification.json"
uv run --no-sync python scripts/check_project_runtime.py \
  --name petclinic-rest --project "$PROJECT_MATRIX_WORK/petclinic-rest" \
  --output "$PROJECT_MATRIX_WORK/petclinic-rest-verification.json"
uv run --no-sync python scripts/check_project_runtime.py \
  --name jhipster --project "$PROJECT_MATRIX_WORK/jhipster" \
  --output "$PROJECT_MATRIX_WORK/jhipster-verification.json"
uv run --no-sync python scripts/check_project_runtime.py \
  --name jhipster-core --project "$PROJECT_MATRIX_WORK/jhipster" \
  --output "$PROJECT_MATRIX_WORK/jhipster-core-verification.json"
```

The offline defect probe originally exited **1** for both defects; after the
follow-up remediation it exits **0**:

```bash
uv run --no-sync python scripts/probe_openapi_matrix_findings.py
```

To reproduce the passing follow-up runs, use the same prepared native builds:

```bash
uv run --no-sync python scripts/check_project_runtime.py \
  --name petclinic-rest --project "$PROJECT_MATRIX_WORK/petclinic-rest" \
  --output "$PROJECT_MATRIX_WORK/petclinic-rest-remediation-verification.json"
uv run --no-sync python scripts/check_project_runtime.py \
  --name jhipster-same-port --project "$PROJECT_MATRIX_WORK/jhipster" \
  --output "$PROJECT_MATRIX_WORK/jhipster-same-port-verification.json"
```

The same-port configuration overrides the `dev` group to `api-docs` (avoiding
upstream sample-secret configuration), keeps JWT admin authorization, and sets
`springdoc.use-management-port=false` plus
`springdoc.api-docs.path=/actuator/openapi`. Business and management share one
random loopback port. Bean **and OpenAPI** reads assert anonymous 401/non-admin
403; the connector still uses its fixed registered path. This avoids the failing
dependency-initialization combination; it does not repair that third-party
separate-port integration or add arbitrary URL support.

Run the causal probe independently (it saves only safe facts and stops its JVM):

```bash
uv run --no-sync python scripts/probe_jhipster_separate_port.py \
  --project "$PROJECT_MATRIX_WORK/jhipster" \
  --output "$PROJECT_MATRIX_WORK/jhipster-separate-port-investigation.json"
```

Exit 0 for this probe means the experiment executed, not that OpenAPI acceptance
passed. Check its saved endpoint status. The three synthetic lifecycle modes
use the same native runtime classpath and open no server:

```bash
for mode in normal eager definitions-only; do
  java -Xmx192m \
    -Dlogback.configurationFile="$PWD/examples/project-matrix/logback-diagnostics.xml" \
    -cp "$(cat "$PROJECT_MATRIX_WORK/jhipster/classpath.txt")" \
    examples/project-matrix/EarlyGroupedBeanProbe.java "$mode"
done
```

The eager mode intentionally exits 1. Its output contains only fixed readiness
markers or exception class names; no target response or exception stack is saved.

## Final separate-port remediation

Use the same pinned JHipster checkout, native build/classpath and two-file
namespace patch described above. The fix is a local source overlay for springdoc
3.1.1, not an upgrade or replacement of cached jars. Prepare it with:

```bash
uv run --no-sync python scripts/prepare_springdoc_patch.py \
  --project "$PROJECT_MATRIX_WORK/jhipster"
```

The script verifies three official versioned source hashes before applying
[the patch](springdoc-3.1.1-diagnostics.patch). Maven resolves extra **compile-only**
types with [springdoc-compile-pom.xml](springdoc-compile-pom.xml); javac disables
annotation processors and emits 10 classes with Java 17 bytecode. Those compile
inputs never enter the target runtime classpath. Later preparations can add
`--offline` to reuse verified source and dependency caches. The script leaves
the application's POM, original source tree and Maven jar cache untouched.

```bash
uv run --no-sync python scripts/check_project_runtime.py \
  --name jhipster-fixed --project "$PROJECT_MATRIX_WORK/jhipster" \
  --output "$PROJECT_MATRIX_WORK/jhipster-separate-port-remediation-verification.json"
uv run --no-sync python scripts/check_project_runtime.py \
  --name petclinic-rest --project "$PROJECT_MATRIX_WORK/petclinic-rest" \
  --output "$PROJECT_MATRIX_WORK/petclinic-rest-final-remediation-verification.json"
```

The JHipster case uses [jhipster-fixed.properties](jhipster-fixed.properties),
keeps native API docs and Actuator documentation enabled, and runs distinct
loopback business/management listeners. The launcher compares actual port values
and acceptance requires `portMode=separate`. The harness verifies the patch and
class hashes before prepending only the patched classes to the native classpath.
JWT, native synchronous Liquibase and in-memory H2 remain active.

The patch avoids early grouped-Bean creation and maps the existing default group
to the fixed **GET** `/actuator/openapi`; it does not let MCP choose custom paths
or groups. A target with only custom groups and no `springdocDefault` still needs
a separately designed registered entry. Original JWT administrator rules protect
the added mapping; anonymous/non-admin checks assert 401/403 for OpenAPI itself.

[Final JHipster summary](jhipster-separate-port-remediation-verification.json)
records 18 accepted calls, 544 beans and 8 APPLIED Liquibase records.
[Final REST summary](petclinic-rest-final-remediation-verification.json) records
15 accepted calls. Partial evidence remains explicit; no complete version matrix
or unpatched-upstream fix is claimed. All launched processes are stopped.

The actual patched post-processors also have four isolated, no-server checks:

```bash
for mode in absent explicit property null-list; do
  java -Xmx192m \
    -Dlogback.configurationFile="$PWD/examples/project-matrix/logback-diagnostics.xml" \
    -cp "$PROJECT_MATRIX_WORK/jhipster/target/springdoc-patched-classes:$(cat "$PROJECT_MATRIX_WORK/jhipster/classpath.txt")" \
    examples/project-matrix/SpringdocPatchedProbe.java "$mode"
done
```

All four passed, including a group definition whose supplier throws if it is
prematurely instantiated; see [probe summary](springdoc-patched-probe-verification.json).
No compiled overlay or downloaded dependency jar is checked into this repository.
