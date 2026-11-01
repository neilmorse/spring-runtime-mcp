# Spring Boot Runtime Diagnostics MCP

[English](README.md)

让编码助手看见 Spring Boot 应用的实际运行状态。它读取应用已授权的 Actuator 和 OpenAPI 数据，帮你排查 Bean、接口、健康、数据库迁移和启动问题。

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

需要 Python 3.11+、[uv](https://docs.astral.sh/uv/) 和已获权读取的本地 Spring Boot 应用。先按[目标配置指南](docs/target-app-setup.md)确认管理端点与权限，再检查并启动 **0.2.7 Alpha**：

```bash
uvx --default-index https://pypi.org/simple spring-runtime-mcp==0.2.7 --version
uvx --default-index https://pypi.org/simple spring-runtime-mcp==0.2.7 --base-url http://127.0.0.1:18081
```

把第二条命令配置为 MCP 客户端的 STDIO 启动命令；直接在终端运行会等待客户端请求。完整步骤见[首次查询](docs/first-query.md)，各客户端模板见[配置指南](docs/client-configuration.md)。

## 使用边界

当前只连接本地回环地址，使用固定端点和可选 Bearer 环境变量鉴权；OpenAPI 固定读取 `/actuator/openapi`。配置值默认隐藏，输出始终脱敏，每次工具结果最多 16 KiB。证据不足会明确返回 `partial/unknown`。

工具不写目标、不重启应用，也不读取 heapdump 或原始日志。完整 Boot/Java/客户端矩阵、Windows/macOS 和生产集群兼容性尚未验证。

[全部文档](docs/README.md) · [工具契约](src/spring_runtime_mcp/schemas/tools-contract.json) · [源码事实接入](docs/source-catalog.md) · [开发与验证](docs/launch/README.md) · [可运行演示](examples/spring-boot-demo/README.md)

[Apache-2.0](LICENSE) · [安全问题反馈](SECURITY.md)
