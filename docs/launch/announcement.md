# 0.2.1 Alpha：发布与投稿材料

更新于 2026-10-31。PyPI 0.2.1 已发布，发布与公开安装验证见
[发布记录](release-0.2.1.md)。Registry 已登记为 `io.github.neilmorse/spring-runtime-mcp`，迁移过程见[记录](registry-plan.md)。

## GitHub Release 文案

Title: **Spring Runtime MCP 0.2.1 Alpha**

Spring Runtime MCP gives coding agents bounded, sanitized evidence from a registered
local Spring Boot instance: beans and conditions, routes, health, migrations,
startup, configuration origin, OpenAPI and drift.

Install with Python 3.11+ and uv:

```bash
uvx --default-index https://pypi.org/simple spring-runtime-mcp==0.2.1 --version
uvx --default-index https://pypi.org/simple spring-runtime-mcp==0.2.1 --base-url http://127.0.0.1:18081
```

Prepare a local, read-only Actuator endpoint using the
[target setup guide](https://github.com/neilmorse/spring-runtime-mcp/blob/v0.2.1/docs/target-app-setup.md).
The second command is the persistent STDIO host for your MCP client.

This Alpha supports loopback targets, fixed endpoints and optional Bearer environment
binding. It permits read-only GET requests, rejects redirects and environment proxies,
validates TLS, sanitizes results through two layers and limits complete tool responses
to 16 KiB. Missing evidence remains partial/unknown.

The release passed Python 3.11–3.14 offline tests, the complete audited gate,
independent wheel/sdist installations and a public PyPI clean-environment check.
Windows/macOS, the complete Boot/Java/client matrix and production clusters remain
unverified. Remote targets, Basic/custom headers, custom management paths and OpenAPI
path fallback are outside this release. Configuration diagnostics stay disabled by default.

- [PyPI 0.2.1](https://pypi.org/project/spring-runtime-mcp/0.2.1/)
- [Verified release workflow](https://github.com/neilmorse/spring-runtime-mcp/actions/runs/41176181251)
- [Release source](https://github.com/neilmorse/spring-runtime-mcp/tree/v0.2.1)

## awesome-mcp-servers 投稿

已提交 [PR #18153](https://github.com/punkpeye/awesome-mcp-servers/pull/18153)，现为草稿。维护者要求先通过 Glama 检查；用户选择暂缓 Glama，因此尚未完成目录收录。以下文案供恢复投稿时使用。

目标：[punkpeye/awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers)。
遵循其[贡献指南](https://github.com/punkpeye/awesome-mcp-servers/blob/main/CONTRIBUTING.md)，
添加到 Developer Tools 类别并按仓库所有者排序，不声明 Registry 收录或完整兼容。

```markdown
- [neilmorse/spring-runtime-mcp](https://github.com/neilmorse/spring-runtime-mcp) 🐍 🏠 - Read-only Spring Boot runtime diagnostics: beans and conditions, routes, health, migrations, startup, config origin, OpenAPI and drift. Loopback-only, sanitized, bounded responses.
```

PR title: **Add Spring Runtime MCP**

PR body:

```text
Add spring-runtime-mcp under Developer Tools. It is an Apache-2.0 Python STDIO server
with a public PyPI 0.2.1 Alpha package. Eight read-only tools inspect a registered
loopback Spring Boot instance; results are sanitized and bounded to 16 KiB.

Repository: https://github.com/neilmorse/spring-runtime-mcp
Package: https://pypi.org/project/spring-runtime-mcp/0.2.1/

The entry describes implemented scope only. It does not claim full Boot/client compatibility. Registry ownership is documented
in the release record. Documentation and submission preparation
were assisted by a coding agent.
```

## 其他目录与社区公告

- [Smithery](https://smithery.ai/new) 当前跳转账户登录；需可用账户，且应先确认其安装模型适用于本地 STDIO。
- [Glama](https://glama.ai/mcp/servers) 的 Add Server 已实际核查，要求账号注册/登录；用户已选择暂缓，未创建账号、接受条款或提交。
- PulseMCP、mcp.so 未核实可用的直接提交路径，不能声称已提交或会自动同步。
- Reddit/dev.to 等帖子需选择平台并使用操作者已授权账户；本轮先准备下列短文，不跨平台自动群发。

Title: **Spring Runtime MCP 0.2.1 Alpha: read-only runtime evidence for Spring Boot agents**

```text
Spring Runtime MCP 0.2.1 Alpha is available on PyPI. It gives coding agents eight
read-only tools for Spring Boot beans/conditions, routes, health, migrations,
startup, configuration origin, OpenAPI and drift.

It reads a registered local loopback instance over fixed Actuator endpoints.
Responses are sanitized and bounded to 16 KiB; missing evidence stays partial/unknown.
Configuration diagnostics are off by default. It never invokes business operations.

This is a limited Alpha, with fixture, isolated-install and fixed-project evidence.
It does not claim every Boot/Java/client combination or production-cluster readiness.

Package: https://pypi.org/project/spring-runtime-mcp/0.2.1/
Source: https://github.com/neilmorse/spring-runtime-mcp
```
