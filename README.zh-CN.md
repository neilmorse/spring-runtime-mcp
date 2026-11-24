# Spring Boot Runtime Diagnostics MCP

[English](README.md)

让编码助手读取本地 Spring Boot 应用的实际运行状态。默认提供 8 个只读 MCP 工具，使用已授权的 Actuator 和 OpenAPI 数据，帮你排查 Bean 未创建、路由未注册、启动缓慢等问题。

已收录于 [Awesome MCP Servers（Developer Tools）](https://github.com/punkpeye/awesome-mcp-servers/pull/18153/files) · [在 Glama 查看工具](https://glama.ai/mcp/servers/neilmorse/spring-runtime-mcp)

## 能帮你查什么

| 你想知道的事 | 它能提供的信息 |
| --- | --- |
| Bean 为什么没创建？ | 查 Bean、依赖和条件报告；有足够证据时追踪阻塞链 |
| 接口到底注册了吗？ | 查实际路径、HTTP 方法、Controller 和 MVC/WebFlux 映射 |
| 应用哪里不健康？ | 查可见组件及 liveness/readiness 状态 |
| 数据库迁移是否异常？ | 查 Flyway/Liquibase 已报告的迁移记录、状态和校验和 |
| 启动慢在哪里？ | 找出慢步骤及其父子关系 |
| 配置被谁覆盖了？ | 查登记属性的来源；配置诊断需单独启用 |
| OpenAPI 里有没有这个接口？ | 查接口、Schema 和文档内引用 |
| 运行实例与源码预期是否一致？ | 比较你提供的 Bean、路由、迁移版本和 Profile 预期 |

例如，你可以问助手：“检查 GET /orders/{id} 是否已注册，告诉我实际处理它的 Controller。”它只读取映射信息，不调用业务接口。

## 开始使用

### 无需 Spring Boot 应用，先试演示

[合成路由演示（英文）](docs/demo.md)使用公开包和内置数据，展示如何查到处理路由的 Controller。运行演示无需 Spring 进程或 MCP 客户端。

### 用 MCP 客户端连接你的应用

需要 Python 3.11+、[uv](https://docs.astral.sh/uv/) 和读取本地 Spring Boot 应用管理端点的权限。先按[目标配置指南](docs/target-app-setup.md)确认端点与权限。以下命令使用 **0.2.14 Alpha**。

```bash
uvx --default-index https://pypi.org/simple spring-runtime-mcp==0.2.14 --version
uvx --default-index https://pypi.org/simple spring-runtime-mcp==0.2.14 --base-url http://127.0.0.1:18081
```

把第二条命令配置为 MCP 客户端的 STDIO 启动命令。直接在终端运行时，它会等待客户端请求。完整步骤见[首次查询（英文）](docs/first-query.md)，各客户端模板见[配置指南](docs/client-configuration.md)。

[分享首次查询反馈](docs/trial-feedback.md)

## 使用边界

当前只连接本地回环地址，使用固定端点。可选 Bearer 鉴权从指定环境变量读取令牌，要求使用经过证书验证的 HTTPS。OpenAPI 固定读取 `/actuator/openapi`。配置诊断默认关闭，需通过 CLI 参数显式启用（`--config-prefix`、`--config-property`、`--config-profiles`）；启用后配置值仍默认隐藏，输出值还需要 `--config-allow-values` 和工具参数 `includeValues=true`。输出始终脱敏，每次工具结果最多 16 KiB。证据不足会明确返回 `partial/unknown`。

工具不写目标、不重启应用，也不读取 heapdump 或原始日志。完整 Boot/Java/客户端矩阵、Windows/macOS 和生产集群兼容性尚未验证。

[全部文档](docs/README.md) · [工具契约](src/spring_runtime_mcp/schemas/tools-contract.json) · [源码事实接入](docs/source-catalog.md) · [开发与验证](docs/launch/README.md)

[Apache-2.0](LICENSE) · [参与贡献](CONTRIBUTING.md) · [安全问题反馈](SECURITY.md)
