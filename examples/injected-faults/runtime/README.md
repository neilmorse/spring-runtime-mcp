# Isolated runtime fault checks

Run from the repository root with the fixed Spring Boot Admin checkout and its prebuilt runtime classpath already cached:

```bash
uv run --no-sync python scripts/check_injected_runtime_faults.py \
  --admin-project /home/neil/.cache/spring-runtime-mcp/large-matrix-20261022/spring-boot-admin \
  --source-catalog examples/injected-faults/generated-source-facts/source-catalog.json \
  --output /tmp/runtime-new-results.json
```

The script builds a temporary copy of the demo offline, injects a conditional route and health indicator, and toggles its existing Stripe condition. It checks fault and recovery using real Actuator responses over MCP STDIO. A separate malformed Flyway V2 migration and a profile-gated constructor cycle each compile successfully and stop startup. Fixed local startup markers are extracted in memory; raw process output is discarded. After each exit, an MCP call against the reserved non-listening loopback port must report unavailable with unknown attribution, followed by a normal restart and Flyway V1/APPLIED baseline with pending visibility unknown. A synthetic Java raw-type example also checks a real javac warning. It also checks an injected health indicator in an operator overlay on the fixed cached Spring Boot Admin sample. Both use newly started loopback-only instances, with process cleanup and a safe summary. The summary's reconstructed frame size is a conservative serialization with a maximal request ID, not a captured wire frame. Health detail visibility and Bean graph gaps remain explicit in the results. The Admin run requires its fixed revision, built classes and complete classpath; missing prerequisites fail the run.
