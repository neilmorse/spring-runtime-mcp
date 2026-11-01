# 文档导航

本目录说明代码当前实现的行为。按任务选择相关章节；无需全量阅读。

| 任务 | 入口 |
| --- | --- |
| 产品范围与当前限制 | [产品规格](../SPEC.md) |
| 模块、入口与数据流 | [系统概览](architecture/system-overview.md) |
| 接口惯例、错误处理与分页实现 | [实现约定](architecture/implementation-conventions.md) |
| HTTP、凭据、SSRF、TLS 与脱敏 | [安全架构](architecture/security-and-sanitization.md) |
| Actuator 响应、Bean/条件图与 OpenAPI 引用 | [归一化架构](architecture/cross-version-normalization.md) |
| 工具选择、参数、结果与错误配方 | [调用策略](contracts/tool-calling-policy.md)；字段以 [工具 Schema](../src/spring_runtime_mcp/schemas/tools-contract.json) 为准 |
| 安装与首次只读查询 | [首次接入](first-query.md) |
| MCP 客户端配置 | [参考模板](client-configuration.md) |
| 目标应用配置与授权 | [目标配置](target-app-setup.md) |
| Bean 源码事实登记 | [Source catalog](source-catalog.md) |
| 静态预期生成与本地构建证据 | [Java 静态事实](source-facts-generation.md)；[构建证据](build-evidence.md) |
| 离线检查、构建与发布 | [发布流程](launch/README.md) |
| Glama 源码容器构建 | [构建指南](launch/glama/README.md) |
| 可复现 Spring Boot 演示 | [演示说明](../examples/spring-boot-demo/README.md) |
| 隔离编译、运行态与协议故障验收 | [故障注入说明](../examples/injected-faults/README.md) |

仓库协作、安全边界和验证要求由 [AGENTS.md](../AGENTS.md) 维护。公开字段与默认值以工具 Schema 为准；模块实现细节由对应源码和测试核对。

维护现行文档时直接更新职责、契约和限制。历史过程、设计取舍及未立项想法进入人类资料库；持久文档不依赖临时执行计划。
