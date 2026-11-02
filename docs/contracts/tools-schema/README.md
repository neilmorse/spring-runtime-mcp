# Eight-tool Schema reference

This directory provides human-readable documentation for [tools-contract.json](../../../src/spring_runtime_mcp/schemas/tools-contract.json).

## Tool list

The eight diagnostic tools are published in fixed alphabetical order:

| Tool name | Title | Purpose | Reference |
|---------|------|------|---------|
| `springboot_analyze_startup` | Startup bottlenecks | Investigate slow startup using slowest steps and parent chains | [Reference](springboot_analyze_startup.md) |
| `springboot_check_migrations` | Migration audit | Investigate migration failures or version differences | [Reference](springboot_check_migrations.md) |
| `springboot_detect_drift` | Source/runtime drift | Compare explicit expectations with runtime facts | [Reference](springboot_detect_drift.md) |
| `springboot_diagnose_health` | Application/dependency health | Investigate dependency failures and probe anomalies | [Reference](springboot_diagnose_health.md) |
| `springboot_inspect_beans` | Bean wiring and conditions | Investigate injection and conditional creation | [Reference](springboot_inspect_beans.md) |
| `springboot_inspect_config` | Configuration sources | Inspect property sources with explicit opt-in | [Reference](springboot_inspect_config.md) |
| `springboot_search_openapi` | OpenAPI queries | Inspect operations and Schema definitions | [Reference](springboot_search_openapi.md) |
| `springboot_verify_mappings` | Route registration | Verify MVC/WebFlux mapping registrations | [Reference](springboot_verify_mappings.md) |

## Shared structures

All tools share:

- **Input arguments**: `targetId` (default "local"), `maxResults` (default/maximum 50), and `cursor` for continuation.
- **Output envelopes**: fields including `schemaVersion`, `status`, `source`, `data`, `coverage`, `nextAction`, and `errors`.
- **Errors**: a shared `DiagnosticError` structure with code, endpoint ID, HTTP status, retry guidance, and remediation recipes.

See the [common envelope reference](common-envelope.md).

## Risk annotations

All tools have:

- `readOnlyHint: true` - read-only operations
- `destructiveHint: false` - nondestructive operations
- `idempotentHint: true` - idempotent operations
- `openWorldHint: false` - tool metadata; deterministic guards enforce actual network permissions

## Schema version

- **contractVersion**: 2
- **protocolVersion**: 2026-07-28
- **schemaVersion**: string "2" in all tool responses

## Related documentation

- [Calling policy](../tool-calling-policy.md): tool selection, arguments, results, and errors
- [System overview](../../architecture/system-overview.md): module responsibilities and data flow
- [Security architecture](../../architecture/security-and-sanitization.md): network, credentials, sanitization, and budgets
