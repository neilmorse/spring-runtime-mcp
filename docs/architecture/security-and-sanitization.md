# Security architecture and sanitization boundaries

The project performs read-only diagnostics on registered loopback Spring Boot instances. [actuator_http.py](../../src/spring_runtime_mcp/transport/actuator_http.py) implements the network boundary, [response_gate.py](../../src/spring_runtime_mcp/transport/response_gate.py) gates capabilities, and the [Schema](../../src/spring_runtime_mcp/schemas/tools-contract.json) constrains tool arguments and output.

## Targets, connections, and credentials

The CLI registers one origin/target. Origins allow http/https, host, and port, rejecting credentials, paths, query, fragment, control characters, and unsafe noncanonical addresses. Each connection resolves DNS, verifies the entire address set is loopback, connects by numeric IP, and checks the actual peer. IPv4-mapped and related forms follow existing validation and cannot bypass loopback restrictions.

The connector uses standard-library `http.client`, running blocking I/O in worker threads. It neither reads environment proxies nor follows redirects. HTTPS uses the default verification context, preserving certificate validation and TLS name checks against the original host. There is no entry point for Basic, arbitrary headers, remote addresses, or custom base paths.

`--token-env` registers only a variable name. Production code reads its value only in the CLI, then binds it to the connector and SanitizerPipeline's known-secret set. The Bearer credential is sent only to fixed endpoints on the registered origin. Credentials never enter logs, error messages, tool definitions, or raw-response caches.

## Fixed endpoints and read-only gates

ResponseGateReader checks the registered target and enabled capability before making a fixed GET with `follow_redirects=False`. The connector independently enforces GET and rejects other methods or requests to follow redirects.

| Logical endpoint | Fixed path |
| --- | --- |
| beans、conditions、mappings | `/actuator/beans`、`/actuator/conditions`、`/actuator/mappings` |
| health | `/actuator/health` |
| health-liveness、health-readiness | `/actuator/health/liveness`、`/actuator/health/readiness` |
| flyway、liquibase、startup | `/actuator/flyway`、`/actuator/liquibase`、`/actuator/startup` |
| openapi | `/actuator/openapi` |
| env, configprops | `/actuator/env`, `/actuator/configprops`; disabled by default |

Paths come from the connector's fixed table, never tool-argument concatenation. heapdump, raw logfile, target writes, and business-endpoint requests are prohibited. startup POST drains the buffer and is always forbidden. A 404, authentication failure, or redirect never triggers an alternative path or anonymous retry.

## Responses, deadlines, and cancellation

- Check HTTP status and Content-Type before reading the body. Reject redirects, 401/403, and unsupported media types immediately. Health-family 503 responses may be read as health evidence.
- Accept `application/json` and Actuator v2/v3 JSON media types; the Accept header is fixed to `application/json`. Media types identify representation, not an exact Boot version.
- Headers have a cumulative 32 KiB limit; bodies are capped at 8 MiB. Support no encoding, identity, and a single gzip layer, with limits before and after decompression. Reject other encodings.
- Fail explicitly on incomplete Content-Length, malformed gzip, duplicate JSON keys, nonfinite numbers, or bounded JSON depth/node violations, without echoing the original response.
- Address attempts share a 2-second connection budget. The reader defaults to 5 seconds; Services waits at most 5 seconds within the shared 15-second tool deadline. Waiting for either of the target's two read slots also counts.
- On timeout or cancellation, abort the connection, briefly wait for worker cleanup, then re-raise. System DNS calls cannot be forcibly terminated; not every underlying thread is guaranteed to stop the instant a tool times out.

## Configuration reads and two-layer sanitization

env/configprops require an explicitly registered read policy. The network still reads complete fixed endpoints, with local projection inside upstream budgets. Registration restricts visible fields, not the size of the application's actual response. Intersect queries with registered properties/prefixes; register profile reads separately.

[SanitizerPipeline](../../src/spring_runtime_mcp/policy/sanitization.py) handles field allowlists, sensitive keys/values, descriptor-context propagation, connection strings, origin, known secrets, and encoded/embedded values. Sensitive values become `[REDACTED_BY_MCP]` or are omitted. Configuration values are hidden by default; explicit includeValues can expose only allowed sanitized values within the registered scope. Sensitivity propagates across input values, bound values, and origin associations.

Raw env/configprops trees, health exception text, condition messages, and OpenAPI descriptions never leave the boundary. Health retains only approved structured fields; origin retains only safe source identifiers and positions. Unavailable evidence uses null, Fact states, or gaps. redactions refers to safe output fields/indices, never raw secret keys or secret digests.

The independent [output_guard](../../src/spring_runtime_mcp/policy/output_guard.py) checks serialization and cache output. Snapshots contain sanitized data only; policy stamps contain no plaintext credentials. Revalidate whole snapshots after policy changes and remove associated cursors on failure. This reduces leakage and instruction-forwarding risks for recognized formats; it does not guarantee immunity to arbitrary semantic prompt injection.

## Protocol output and failure handling

STDIO stdout carries JSON-RPC only; safe logs and CLI errors go to stderr. The host validates tool input/output and RFC3339 timestamps; invalid arguments cause no network access. Safety errors become fixed local messages. Exception repr, stacks, remote suggestions, and raw responses never leave the boundary.

Each tool result contains structuredContent and an equivalent text copy. The complete JSON-RPC response is capped at 16,384 UTF-8 bytes. Pagination, host result construction, and the actual SDK send layer independently check this budget. A safety failure never falls back to raw output. Static tools/list is not trimmed by the 16 KiB tool-result limit.

See [tests/security](../../tests/security/README.md) for default tests and synthetic security regressions, and the [release workflow](../launch/README.md) for commands. Self-hosted loopback TLS checks and fixed-project samples do not establish a complete real TLS/SNI, platform, or client matrix.
