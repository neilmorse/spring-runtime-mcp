# Glama source container build guide

The [Dockerfile](Dockerfile) builds `spring-runtime-mcp` from repository source using a digest-pinned Python 3.12 slim image and official PyPI, then starts the real STDIO host as nonroot UID 10001.

Run at the repository root:

```bash
docker build -t spring-runtime-mcp-glama:local -f docs/launch/glama/Dockerfile .
docker run --rm --network none spring-runtime-mcp-glama:local --version
```

Builds download the base image and dependencies; the run command above checks the executable version only. The Dockerfile copies pyproject.toml, README, LICENSE, and src, excluding human archives, fixture substitutes, target credentials, and port-exposure configuration. Tool discovery itself does not read targets.

Actual protocol validation requires a client to perform initialize, tools/list, and tools/call through container stdin/stdout. State the network namespace when using self-hosted loopback fixtures; container 127.0.0.1 is not the developer host. Real application access requires separate authorization and retains fixed paths, loopback, authentication, TLS, sanitization, and budget guards.

A remote directory sandbox cannot directly diagnose a loopback application on a developer's machine. For daily diagnostics, run the local CLI in the authorized application's environment using the [first-query guide](../../first-query.md).

After Dockerfile, dependency, or tool metadata changes, check local builds, actual remote builds, and tool discovery separately. Glama configuration, listing, and ratings depend on remote state; this guide asserts no current score or compatibility result. See [Glama submission guidance](https://glama.ai/mcp/faq#how-do-i-submit-an-mcp-server).
