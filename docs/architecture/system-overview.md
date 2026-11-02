# System overview

Spring Runtime MCP is a standalone Python 3.11+ STDIO service providing coding agents with read-only runtime evidence from registered loopback Spring Boot instances. The executable is `spring-runtime-mcp`; [__init__.py](../../src/spring_runtime_mcp/__init__.py) defines the version. Dependencies and builds are configured in [pyproject.toml](../../pyproject.toml), with the exact development environment pinned by [uv.lock](../../uv.lock).

## Modules and entry points

| Module | Responsibility |
| --- | --- |
| `cli.py` | Parse arguments/environment variables, bind Bearer credentials, load the optional source catalog, assemble services, and start STDIO. |
| `server.py` | Official MCP SDK lowlevel Server; tool discovery, argument/result validation, shared deadlines, and bounded protocol output. |
| `services.py` | Coordinate registered targets, readers, sanitization, source facts, snapshots, and per-target read slots. |
| `transport/` | Fixed-endpoint HTTP, response gates, bounded JSON, frame serialization, and offline resource reads. |
| `policy/` | Configuration read scope, field projection, sanitization, and the independent output gate. |
| `models/` | Facts, queries, observations, graphs, and analysis/call budgets. |
| `adapters/` | Normalize Actuator/OpenAPI structures into domain facts and evidence gaps. |
| `analyzers/` | Deterministic Bean graph traversal, condition-chain analysis, and drift impact. |
| `tools/` | Eight handlers, fixed registration, envelope composition, and pagination. |
| `contracts/`, `schemas/` | Argument normalization and the packaged eight-tool Schema. |
| `snapshots.py` | Bounded sanitized snapshots, query-bound cursors, and continuation pages. |
| `replay.py`, `replay_data/` | One-shot offline scenarios using the same handlers. |

These are module responsibilities, not a mandatory one-way import graph. Shared models underpin the system; tools connect reads, normalization, analysis, and safe output.

The [CLI](../../src/spring_runtime_mcp/cli.py) `main` calls `build_services` and `run_stdio` in the [server](../../src/spring_runtime_mcp/server.py). `build_services` assembles one origin/target; connections are opened only when tools read. `build_server(services)` registers `tools/list` and `tools/call` callbacks and permits Services injection for tests or local integration.

## Online data flow

1. The CLI validates the origin, target, timeout, optional configuration policy, and Bearer variable name; bounded reads and JSON validation load the source catalog.
2. The SDK receives a request; the host validates arguments, establishes a shared 15-second deadline, and dispatches through the fixed registry.
3. An initial query acquires a target read slot through Services. ResponseGateReader checks capability, then the standard-library connector sends GET to the fixed path.
4. Bounded status, media-type, and JSON checks produce a ParsedObservation with target, snapshot, observation time, and endpoint identity.
5. Adapters and analyzers establish all visible facts and associations. Tools fold gaps into coverage/status, filter, count, and stably sort.
6. SanitizerPipeline processes output. Pagination selects a page using record and complete-response byte budgets, saving a sanitized snapshot when continuation is needed.
7. The host validates the output Schema. The independent safety gate and actual SDK serialization recheck the complete JSON-RPC frame, returning structured and equivalent text copies.

## State and resources

Initial queries collect runtime evidence; cursor queries retain the original arguments and snapshot without rereading the target. SnapshotStore defaults to a 60-second absolute TTL and 32 MiB total budget with LRU eviction. Process restarts lose snapshots. A changed policy stamp triggers revalidation of all cached facts; failure removes the snapshot's associated handles.

Services permits at most two concurrent reads per target, with slot waits counted toward the deadline. A Services read waits at most 5 seconds, bounded by the remaining deadline. The CLI reader timeout defaults to 5 seconds and accepts values greater than 0 and no more than 60 seconds. See [security architecture](security-and-sanitization.md) for DNS and worker-thread cleanup limits.

## Tools and evidence

Eight tools are registered in name order. Their selectors and results follow the [Schema](../../src/spring_runtime_mcp/schemas/tools-contract.json) and [calling policy](../contracts/tool-calling-policy.md). Fact distinguishes known, unknown, notReported, and redacted; missing evidence propagates through gaps to tools, yielding partial results and unknown totals when necessary.

See the [product specification](../../SPEC.md) for availability and supported scope. Default validation uses synthetic fixtures and self-hosted loopback services; real targets require separate authorization. See the [release workflow](../launch/README.md) for development checks and distribution verification.
