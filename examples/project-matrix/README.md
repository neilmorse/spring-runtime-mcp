# Public-project runtime reproduction

This opt-in harness builds pinned Spring Petclinic, Petclinic REST and JHipster snapshots from [projects.json](projects.json). It is separate from default offline pytest and requires explicit authorization to download/build projects and start disposable loopback applications.

The [launcher](ProjectDiagnosticsLauncher.java) uses original application configurations with buffered startup events, operator-owned properties and fixed diagnostic GET reads. JHipster uses the [namespace patch](jhipster-actuator-namespace.patch) in a disposable checkout to align its management routes with `/actuator`, preserving JWT authorization. A separate-port springdoc variant uses the explicit source overlay below; an unpatched upstream setup is a distinct case.

Every result is checked against its output Schema, independent safety guard and complete 16 KiB response budget. Saved JSON files identify individual source/configuration runs; their success or failure does not describe the current worktree or establish a full compatibility matrix. Raw target responses, tokens, logs and exception stacks are not stored.

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

The offline regression probe checks local-reference projection and business Schema fields; exit **0** means its assertions passed:

```bash
uv run --no-sync python scripts/probe_openapi_matrix_findings.py
```

Run the named configurations against the prepared native builds:

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

## Separate-port springdoc source overlay

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

Saved configuration-specific summaries: [JHipster separate port](jhipster-separate-port-remediation-verification.json) and [Petclinic REST](petclinic-rest-final-remediation-verification.json). Read their source/configuration identity and evidence gaps independently of a new run.

The actual patched post-processors also have four isolated, no-server checks:

```bash
for mode in absent explicit property null-list; do
  java -Xmx192m \
    -Dlogback.configurationFile="$PWD/examples/project-matrix/logback-diagnostics.xml" \
    -cp "$PROJECT_MATRIX_WORK/jhipster/target/springdoc-patched-classes:$(cat "$PROJECT_MATRIX_WORK/jhipster/classpath.txt")" \
    examples/project-matrix/SpringdocPatchedProbe.java "$mode"
done
```

The modes include a group definition whose supplier throws on premature instantiation; the saved [probe summary](springdoc-patched-probe-verification.json) is tied to that run.
No compiled overlay or downloaded dependency jar is checked into this repository.
