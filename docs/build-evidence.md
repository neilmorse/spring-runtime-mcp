# Local build evidence

`scripts/build_evidence.py` is a local Python interface, not a new MCP tool or collection endpoint. Operators explicitly register project directories, source files, and local artifact paths. It does not scan projects, execute builds, access the network, or collect running-process information. Register only authorized files suitable for hashing, not credentials or logs.

```python
from pathlib import Path
from scripts.build_evidence import capture_snapshot, compare_snapshots

project = Path('/path/to/project')
sources = [Path('pom.xml'), Path('src/main/java/example/App.java')]
artifact = Path('target/app.jar')
before = capture_snapshot(project, sources, artifact, build_exit_code=0)
# After editing source or building, read the same scope; the caller supplies the exit code.
after = capture_snapshot(project, sources, artifact, build_exit_code=0)
comparison = compare_snapshots(before, after)
```

The interface returns aggregate SHA-256 for registered source files, artifact SHA-256, caller-reported build exit code, and comparison results. Callers may save the returned object locally. Source aggregation includes relative paths and content digests, so compare the same path set. Results exclude file contents and absolute paths. Empty source lists, duplicate registration, missing/unreadable files, metadata changes during reads, nonregular files, symlinks, and paths escaping the project yield unknown digests. If either comparison side is unknown, the corresponding changed value is null. This implementation requires platform support for `O_NOFOLLOW` and rejects symlinks in the project root and registered paths. Files are read individually, not as an atomic project snapshot; collect while files are stable.

Build `outcome` reflects only the caller-supplied exit code; `artifactProducedByBuild` is always `unknown`. Neither a zero exit code nor changed artifact digests prove an artifact was built from the stated source. A failed build may leave an old artifact. Different local artifact digests establish only that the bytes read differ.

`runtimeIdentity.state` is always `notCollected`; runtime comparison is `unknown`. A local jar digest, declared source revision, or launch command does not prove the running process loaded that jar. MCP route/drift observations are separate runtime facts alongside local digests, not observed runtime build identity.

The isolated `scripts/check_injected_build_faults.py` demo records two cases in temporary copies: source edited without rebuilding, and successful rebuild while an old process remains alive. Each is checked using read-only MCP route queries. It copies the launch jar to a separate path to avoid overwriting a live JVM's file. This acceptance requires Maven's offline cache, Java, Linux `/proc`, and newly created loopback instances; the output path must not exist:

```bash
uv run --no-sync python scripts/check_injected_build_faults.py --output /tmp/build-evidence-check.json
```
