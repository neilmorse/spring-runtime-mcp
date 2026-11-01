# Spring Boot Runtime Diagnostics MCP

[中文说明](README.zh-CN.md)

Give your coding assistant access to what is actually running in a Spring Boot application. This MCP server reads authorized Actuator and OpenAPI data to help investigate Beans, routes, health, database migrations and startup problems.

## What can it check?

| Your question | What it provides |
| --- | --- |
| Why was a Bean not created? | Beans, dependencies and condition reports, with blocking chains when evidence is sufficient |
| Is this route registered? | Actual paths, HTTP methods, Controllers and MVC/WebFlux mappings |
| What is unhealthy? | Visible components and liveness/readiness status |
| Did a migration fail? | Reported Flyway/Liquibase records, states and checksums |
| What made startup slow? | Slow steps and their parent chains |
| Where did a configuration value come from? | Sources for registered properties; configuration diagnostics require opt-in |
| Is this API in OpenAPI? | Operations, schemas and references within the document |
| Does the process match my expectations? | Compare the Bean, route, migration version and profile expectations you supply |

For example, ask: “Check whether GET /orders/{id} is registered and tell me which Controller handles it.” The server reads mapping metadata without calling the business endpoint.

## Get started

You need Python 3.11+, [uv](https://docs.astral.sh/uv/) and an authorized local Spring Boot application. Confirm its management endpoints and permissions using the [target setup guide](docs/target-app-setup.md), then check and start **0.2.8 Alpha**:

```bash
uvx --default-index https://pypi.org/simple spring-runtime-mcp==0.2.8 --version
uvx --default-index https://pypi.org/simple spring-runtime-mcp==0.2.8 --base-url http://127.0.0.1:18081
```

Use the second command as your MCP client's STDIO server command. In a terminal it waits for client requests. Follow the [first-query guide](docs/first-query.md) or use the [client configuration templates](docs/client-configuration.md) (both in Chinese).

## Boundaries

The server connects only to loopback addresses, uses fixed endpoints and supports optional Bearer authentication from a named environment variable. OpenAPI uses `/actuator/openapi`. Configuration values are hidden by default, output is sanitized, and each tool response is capped at 16 KiB. Missing evidence is reported as `partial`/`unknown`.

Tools do not write to the target, restart applications, or read heap dumps or raw logs. The complete Boot/Java/client matrix, Windows/macOS and production-cluster compatibility remain unverified.

[Documentation](docs/README.md) · [Tool contract](src/spring_runtime_mcp/schemas/tools-contract.json) · [Source facts](docs/source-catalog.md) · [Development and checks](docs/launch/README.md) · [Runnable demo](examples/spring-boot-demo/README.md)

[Apache-2.0](LICENSE) · [Report a security issue](SECURITY.md)

<!-- mcp-name: io.github.neilmorse/spring-runtime-mcp -->
