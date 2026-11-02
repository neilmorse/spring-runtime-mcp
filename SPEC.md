# Spring Boot Runtime Diagnostics MCP: current product specification

This specification describes the implemented product scope. [tools-contract.json](src/spring_runtime_mcp/schemas/tools-contract.json) is authoritative for public inputs, outputs, defaults, and constraints; [AGENTS.md](AGENTS.md) governs collaboration permissions. Start with the [documentation index](docs/README.md).

## Product and connection

The product is a standalone Python 3.11+ CLI exposing eight tools through a STDIO host using the official MCP Python SDK. At startup, the CLI registers one loopback origin and target, with optional Bearer environment-variable binding, a local Source catalog, and explicitly enabled configuration diagnostics. See the [first-query guide](docs/first-query.md) for installation and the first query.

Target addresses must resolve to 127.0.0.0/8 or ::1. An origin contains only an http(s) scheme, host, and port. Connections use numeric addresses with peer checks; HTTPS uses default TLS validation. Requests are fixed GETs with redirects and environment proxies disabled. Tool arguments are local query selectors, never forwarded URLs, paths, or headers.

The endpoint table is fixed under `/actuator/`; OpenAPI is read from `/actuator/openapi`. Basic authentication, custom management base paths, automatic capability discovery, endpoint fallback, and remote targets are unsupported.

## Eight tools

| Tool | Implemented capability and evidence boundary |
| --- | --- |
| springboot_analyze_startup | Read startup events, durations, and parent chains; filter and sort them. Preserve gaps for missing units, parents, or depth evidence; do not sum overlapping steps into total startup time. |
| springboot_check_migrations | Normalize Flyway/Liquibase inventory, states, versions/identities, and checksums; compare explicit expectations. Keep unreported pending status, versions, or duration unknown. |
| springboot_detect_drift | Compare caller-supplied Bean, route, migration-version, and profile expectations; use dependency graphs and available startup evidence to assess impact and evidence strength. |
| springboot_diagnose_health | Read overall health, visible components, and fixed liveness/readiness endpoints; return partial/unknown when details or status are missing. |
| springboot_inspect_beans | Inspect Contexts, aliases, forward/reverse and multi-hop dependencies; combine conditions and registered source facts into evidence-backed blocking chains. |
| springboot_inspect_config | Disabled by default. When enabled, project sources, bindings, and effective values within registered properties/prefixes; values are hidden by default and always sanitized. |
| springboot_search_openapi | Query operations or Schemas; handle in-document, shared, cyclic, and depth-limited references without fetching remote references. |
| springboot_verify_mappings | Inspect reported MVC/WebFlux route paths, methods, handlers, and Contexts; retain incomplete status for unreadable data or possible non-DispatcherServlet coverage. |

The fixed tool list is published alphabetically by name with all four explicit risk annotations. Tool discovery does not read the target. See [calling policy](docs/contracts/tool-calling-policy.md) for tool selection, filter combinations, and next actions.

## Result and security invariants

- Establish all visible facts and associations before filtering, stable sorting, and pagination. maxResults defaults to and is capped at 50.
- Domain envelopes contain Schema fields including source, data, totalMatched, truncated, coverage, nextAction, and errors. Unknown totals use null; insufficient evidence uses partial/unknown.
- Each tool result includes structuredContent and an equivalent compact JSON text copy. The complete JSON-RPC tool response is capped at 16,384 UTF-8 bytes.
- Each tool call has a shared 15-second deadline and two shared read slots per target; queueing counts toward the deadline. Upstream bodies are capped at 8 MiB and headers at 32 KiB.
- Cache sanitized snapshots only: default absolute TTL 60 seconds, total budget 32 MiB. Continuation pages retain the original query and snapshot; restarting the process loses snapshots.
- All external evidence passes through SanitizerPipeline and an independent output gate. Never emit raw credentials, exception stacks, OpenAPI free-text descriptions, complete env/configprops value trees, or remote instructions.
- Prohibit target writes, heapdump, raw logfile, arbitrary business requests, and bypasses of authentication, TLS, sanitization, or budgets. startup always uses GET.

Implementation details are in the [system overview](docs/architecture/system-overview.md), [security architecture](docs/architecture/security-and-sanitization.md), and [normalization architecture](docs/architecture/cross-version-normalization.md).

## Configuration and source facts

The CLI reads `SPRING_RUNTIME_BASE_URL`, `SPRING_RUNTIME_TARGET_ID`, `SPRING_RUNTIME_TIMEOUT`, and `SPRING_RUNTIME_SOURCE_CATALOG` as defaults for their corresponding arguments. Bearer values are read only from the variable named by `--token-env`; token values do not belong in tool arguments or configuration files.

Register configuration diagnostics explicitly using `--config-prefix`, `--config-property`, and `--config-profiles`. `--config-allow-values` permits sanitized values within the registered scope. Network reads still use fixed `/actuator/env` and `/actuator/configprops`; local filtering does not reduce the upstream response scope.

A Source catalog contains operator-registered JSON facts, capped at 256 KiB and 1,000 combined types/producers. The CLI does not scan or execute source. See the [catalog guide](docs/source-catalog.md) for correlation rules and coverage gaps.

## Validation and compatibility scope

Default tests use synthetic multi-version fixtures, self-hosted loopback HTTP/TLS services, and official SDK protocol checks. Offline replay reuses the handlers as a one-shot command, not a persistent MCP service.

Normalization handles Boot 2.7/3.x/4.x-related structures and MVC/WebFlux reports. Shape recognition, synthetic tests, and isolated fixed-project samples each provide limited evidence. The full Boot/Java/client matrix, Windows/macOS, and production-cluster compatibility remain unverified. Complete visibility is not guaranteed for JAX-RS business routes, arbitrary condition messages, or every runtime-proxy/source-type combination.

Real-instance integration requires separate authorization and remains separate from default offline checks. See the [release workflow](docs/launch/README.md) for checks, builds, and gates. The wheel distributes the tool Schema, py.typed, and replay resources; historical human records remain in Git and are excluded from wheel/sdist.
