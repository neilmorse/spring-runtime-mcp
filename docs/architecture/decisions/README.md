# 架构决策记录（ADR）

本目录记录影响系统设计的关键决策、上下文和后果。

## ADR 索引

| ADR | 标题 | 状态 | 日期 |
|-----|------|------|------|
| [001](001-snapshot-ttl-and-budget.md) | 快照 60 秒 TTL 和 32 MiB 预算 | 已接受 | 2024-11 |
| [002](002-max-results-limit.md) | maxResults 上限 50 | 已接受 | 2024-11 |
| [003](003-response-size-cap.md) | 响应上限 16 KiB | 已接受 | 2024-11 |
| [004](004-config-diagnostics-opt-in.md) | 配置诊断默认关闭 | 已接受 | 2024-11 |
| [005](005-loopback-only-targets.md) | 仅连接回环地址 | 已接受 | 2024-11 |

## ADR 模板

每条 ADR 包含：

- **Context（上下文）**：为什么需要决策
- **Decision（决策）**：采取了什么决策
- **Consequences（后果）**：决策的正面和负面影响
- **Status（状态）**：已提议/已接受/已弃用/已取代

## 相关文档

- [系统概览](../system-overview.md)
- [安全架构](../security-and-sanitization.md)
- [实现约定](../implementation-conventions.md)
