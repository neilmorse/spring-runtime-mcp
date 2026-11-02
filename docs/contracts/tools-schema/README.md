# 八工具 Schema 说明

本目录为 [tools-contract.json](../../../src/spring_runtime_mcp/schemas/tools-contract.json) 提供人类可读的文档版本。

## 工具列表

按字母序固定发布的八个诊断工具：

| 工具名称 | 标题 | 用途 | 详细说明 |
|---------|------|------|---------|
| `springboot_analyze_startup` | 启动瓶颈诊断 | 排查慢启动，返回最慢步骤及父子链 | [详细说明](springboot_analyze_startup.md) |
| `springboot_check_migrations` | 数据库迁移审计 | 排查迁移失败或版本差异 | [详细说明](springboot_check_migrations.md) |
| `springboot_detect_drift` | 源码与运行态漂移诊断 | 比较预期与实际运行状态 | [详细说明](springboot_detect_drift.md) |
| `springboot_diagnose_health` | 应用与依赖健康诊断 | 排查依赖故障或探针异常 | [详细说明](springboot_diagnose_health.md) |
| `springboot_inspect_beans` | Bean 装配与条件诊断 | 排查注入或条件装配问题 | [详细说明](springboot_inspect_beans.md) |
| `springboot_inspect_config` | 配置来源检查 | 查询配置属性来源（需显式启用） | [详细说明](springboot_inspect_config.md) |
| `springboot_search_openapi` | OpenAPI 查询 | 查询操作或 Schema 定义 | [详细说明](springboot_search_openapi.md) |
| `springboot_verify_mappings` | 路由注册验证 | 验证 MVC/WebFlux 路由注册 | [详细说明](springboot_verify_mappings.md) |

## 公共结构

所有工具共享以下结构：

- **输入参数**：包含 `targetId`（默认 "local"）、`maxResults`（默认 50，上限 50）、`cursor`（续页游标）
- **输出信封**：包含 `schemaVersion`、`status`、`source`、`data`、`coverage`、`nextAction`、`errors` 等字段
- **错误结构**：统一的 `DiagnosticError` 结构，包含错误码、端点 ID、HTTP 状态、重试建议和修复配方

详细说明见 [公共信封结构](common-envelope.md)。

## 风险注解

所有工具的风险注解均为：

- `readOnlyHint: true` - 只读操作
- `destructiveHint: false` - 非破坏性
- `idempotentHint: true` - 幂等操作
- `openWorldHint: false` - 工具元数据提示，实际网络权限由守卫执行

## Schema 版本

- **contractVersion**: 2
- **protocolVersion**: 2026-07-28
- **schemaVersion**: 字符串 "2"（所有工具响应）

## 相关文档

- [工具调用策略](../tool-calling-policy.md) - 工具选择、参数、结果与错误处理
- [系统概览](../../architecture/system-overview.md) - 模块职责与数据流
- [安全架构](../../architecture/security-and-sanitization.md) - 网络、凭据、脱敏与预算
