# Small upstream guide acceptance (opt-in)

This run was explicitly authorized on 2026-10-22. It uses disposable copies of
two small public repositories; default pytest remains synthetic/fixture-only.

| Source repository | Pinned commit | Actual runtime |
| --- | --- | --- |
| [spring-guides/gs-rest-service](https://github.com/spring-guides/gs-rest-service/tree/3f4cef01152596c19bc4d37939409358812b1421/complete) | `3f4cef01152596c19bc4d37939409358812b1421` | Boot 3.5.16 and 4.1.1, MVC, Java 21 |
| [spring-guides/gs-reactive-rest-service](https://github.com/spring-guides/gs-reactive-rest-service/tree/a6f4ff0c651545a14ff5d1f731fde9a8d136e4d5/complete) | `a6f4ff0c651545a14ff5d1f731fde9a8d136e4d5` | Boot 3.2.4, WebFlux, Java 21 |

Both upstream POMs specify Boot 4.0.8. These are **modified-version acceptance
targets**, not evidence that their unmodified Boot 4.0.8 builds passed. The small
diagnostics POM replaces upstream build/test dependencies with the appropriate
web starter and Actuator, and uses a cached compiler plugin. Business Java
sources are unchanged. Upstream business tests were not run.

`GuideDiagnosticsLauncher.java` starts the original application configuration
directly with buffered startup events and an extra `guide.*` configuration bean.
It avoids executing the reactive example's `main`, whose demo client would GET
`localhost:8080`. Both actual listeners bind to random ports on `127.0.0.1`.
There is no database or security dependency. Anonymous management access is
limited by this disposable loopback setup; it does not test authentication.

The launcher exposes only the listed diagnostic endpoints. Configuration value
visibility is enabled for this isolated process with a minimal inherited
environment and a generated synthetic token. The MCP CLI still requires
explicit registration of the `guide` prefix and value permission. Only safe
summaries and fixed boolean probe facts are saved; raw endpoint bodies,
framework logs, synthetic secret values and remote exception stacks are not
saved. Every launched Java process is stopped in `finally`.

## Checks and scope

Each variant calls tools through the official SDK and actual STDIO host. Discovery must list eight tools in sorted order; results are checked against output Schema, the safety guard and the complete response budget including SDK metadata and duplicate text.

Checks cover Bean lookup/conditions, mappings, hidden health details, non-draining startup GETs, source/runtime comparison, configuration registration and negative authorization cases. WebFlux positive nested-AND and Accept predicates use the current parser; unknown predicate syntax remains partial with gaps. Current semantics are described in the [normalization guide](../../docs/architecture/cross-version-normalization.md).

Saved [initial results](verification.json) and [WebFlux rerun](webflux-remediation-verification.json) belong to their recorded source/configuration snapshots. New runs require separate authorization and a fresh result file; neither those records nor this harness establish complete framework/client compatibility.

## Reproduce

Run these commands from the spring-runtime-mcp repository root. Fetch and
dependency resolution require network; runtime acceptance only uses the
disposable loopback processes. Inspect the pinned source before executing it.

```bash
export GUIDE_WORK_DIR="$(mktemp -d)"
fetch_guide() {
  git init -q "$GUIDE_WORK_DIR/$1"
  git -C "$GUIDE_WORK_DIR/$1" remote add origin "https://github.com/spring-guides/$1.git"
  git -C "$GUIDE_WORK_DIR/$1" config remote.origin.promisor true
  git -C "$GUIDE_WORK_DIR/$1" config remote.origin.partialclonefilter blob:none
  git -C "$GUIDE_WORK_DIR/$1" fetch --depth=1 --filter=blob:none origin "$2"
  git -C "$GUIDE_WORK_DIR/$1" sparse-checkout set complete
  git -C "$GUIDE_WORK_DIR/$1" checkout --detach FETCH_HEAD
}
fetch_guide gs-rest-service 3f4cef01152596c19bc4d37939409358812b1421
fetch_guide gs-reactive-rest-service a6f4ff0c651545a14ff5d1f731fde9a8d136e4d5

python3 - <<'PY'
import os
import shutil
from pathlib import Path

work = Path(os.environ["GUIDE_WORK_DIR"])
template = Path("examples/upstream-guides/diagnostics-pom.template.xml").read_text()
cases = [
    ("mvc-3.5.16", "gs-rest-service", "3.5.16", "web"),
    ("mvc-4.1.1", "gs-rest-service", "4.1.1", "webmvc"),
    ("webflux-3.2.4", "gs-reactive-rest-service", "3.2.4", "webflux"),
]
for name, repository, version, starter in cases:
    project = work / name
    shutil.copytree(work / repository / "complete", project)
    pom = template.replace("@CASE@", name).replace("@BOOT_VERSION@", version)
    (project / "pom.xml").write_text(pom.replace("@WEB_STARTER@", starter))
PY

for variant in mvc-3.5.16 mvc-4.1.1 webflux-3.2.4; do
  mvn -o -B -q -f "$GUIDE_WORK_DIR/$variant/pom.xml" compile \
    org.apache.maven.plugins:maven-dependency-plugin:3.8.1:build-classpath \
    -Dmdep.outputFile="$GUIDE_WORK_DIR/$variant/classpath.txt"
done
```

If an offline build reports missing artifacts, resolve only those required
dependencies with a bounded online build before continuing. No Maven package,
Docker or test dependency downloads are needed for these checks.

For either MVC version (change `3.5.16` to `4.1.1` for the second):

```bash
uv run --no-sync python scripts/check_guide_runtime.py \
  --project "$GUIDE_WORK_DIR/mvc-3.5.16" \
  --main-class com.example.restservice.RestServiceApplication \
  --boot-version 3.5.16 --stack mvc --route /greeting \
  --source-revision 3f4cef01152596c19bc4d37939409358812b1421 \
  --source-repository https://github.com/spring-guides/gs-rest-service \
  --output "$GUIDE_WORK_DIR/mvc-3.5.16-verification.json"
```

With the parser fix, the WebFlux run exits **0** and saves a new acceptance
summary. The original failing result remains in `verification.json`:

```bash
uv run --no-sync python scripts/check_guide_runtime.py \
  --project "$GUIDE_WORK_DIR/webflux-3.2.4" \
  --main-class com.example.reactivewebservice.ReactiveWebServiceApplication \
  --boot-version 3.2.4 --stack webflux --route /hello \
  --source-revision a6f4ff0c651545a14ff5d1f731fde9a8d136e4d5 \
  --source-repository https://github.com/spring-guides/gs-reactive-rest-service \
  --output "$GUIDE_WORK_DIR/webflux-3.2.4-remediation-verification.json"
```
