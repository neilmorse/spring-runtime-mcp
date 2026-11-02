# Documentation index

These pages describe implemented behavior. Select the relevant chapters for your task; there is no need to read everything.

| Task | Entry point |
| --- | --- |
| Product scope and current limits | [Product specification](../SPEC.md) |
| Modules, entry points, and data flow | [System overview](architecture/system-overview.md) |
| Interfaces, error handling, and pagination | [Implementation conventions](architecture/implementation-conventions.md) |
| HTTP, credentials, SSRF, TLS, and sanitization | [Security architecture](architecture/security-and-sanitization.md) |
| Actuator responses, Bean/condition graphs, and OpenAPI references | [Normalization architecture](architecture/cross-version-normalization.md) |
| Tool selection, arguments, results, and errors | [Calling policy](contracts/tool-calling-policy.md); [per-tool reference](contracts/tools-schema/README.md). Fields are defined by the [tool Schema](../src/spring_runtime_mcp/schemas/tools-contract.json). |
| Installation and first read-only query | [First-query guide](first-query.md) |
| Synthetic route demo without a Spring process | [Public-package replay demo](demo.md) |
| Successful or blocked first-query feedback | [Trial guide and invitation templates](trial-feedback.md); [Issue template](../.github/ISSUE_TEMPLATE/first-query-feedback.md) |
| Reporting problems, submitting fixes, and validating PRs | [Contribution guide](../CONTRIBUTING.md); [PR template](../.github/pull_request_template.md) |
| MCP client configuration | [Client templates](client-configuration.md) |
| Troubleshooting by error code | [Troubleshooting](troubleshooting.md) |
| Synthetic performance benchmarks | [Running and interpreting benchmarks](../tests/performance/README.md) |
| Architecture decisions | [Decision index](architecture/decisions/README.md) |
| Target application setup and authorization | [Target setup](target-app-setup.md) |
| Registering Bean source facts | [Source catalog](source-catalog.md) |
| Static expectations and local build evidence | [Java static facts](source-facts-generation.md); [build evidence](build-evidence.md) |
| Offline replay and debugging | [Replay implementation](../src/spring_runtime_mcp/replay.py) |
| Offline checks, builds, and releases | [Release workflow](launch/README.md) |
| Glama source container builds | [Build guide](launch/glama/README.md) |

[AGENTS.md](../AGENTS.md) governs collaboration, security boundaries, and validation. The tool Schema defines public fields and defaults; check the corresponding source and tests for implementation details.

Maintain current documents by updating responsibilities, contracts, and limits directly. Historical processes, design tradeoffs, and uncommitted ideas belong in the human archive; durable documentation must not depend on temporary execution plans.
