# Architecture decisions

These notes summarize implemented constraints, their operational effects, and relevant source. The [tool Schema](../../../src/spring_runtime_mcp/schemas/tools-contract.json) defines public fields; [security architecture](../security-and-sanitization.md) and [implementation conventions](../implementation-conventions.md) define the corresponding boundaries.

| Decision | Implemented constraint |
| --- | --- |
| [001](001-snapshot-ttl-and-budget.md) | Snapshot absolute TTL of 60 seconds and total storage budget of 32 MiB |
| [002](002-max-results-limit.md) | maxResults default and maximum of 50 |
| [003](003-response-size-cap.md) | Complete JSON-RPC tool response capped at 16 KiB |
| [004](004-config-diagnostics-opt-in.md) | Configuration diagnostics disabled by default |
| [005](005-loopback-only-targets.md) | Connections limited to registered loopback targets |

Keep decision notes consistent with the code and current limitations. Record measurements only with a reproducible method and evidence scope; synthetic results do not establish real-instance or client compatibility.
