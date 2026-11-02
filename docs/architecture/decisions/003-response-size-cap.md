# ADR 003: 响应上限 16 KiB

**状态**：已接受

**日期**：2024-11

---

## Context（上下文）

MCP 工具响应通过 JSON-RPC STDIO 传输，需要平衡：

1. **MCP 协议兼容性**：符合 MCP SDK 预期
2. **编码助手上下文**：避免单次工具调用消耗过多上下文
3. **网络与序列化开销**：大响应增加延迟
4. **双副本格式**：structuredContent + text 同时存在

关键约束：
- 完整 JSON-RPC 帧包含：request id、SDK 元数据、structuredContent、text
- 编码助手通常在 8K-32K 上下文窗口内工作
- 大量数据应通过分页而非单次巨大响应传输
- 脱敏后的数据仍可能包含长字符串（如 OpenAPI Schema）

## Decision（决策）

设定完整 JSON-RPC 工具响应上限为 **16,384 UTF-8 字节**（16 KiB）：

### 1. 16 KiB 上限包含完整帧

- JSON-RPC 信封（request id、jsonrpc 版本）
- SDK 元数据
- `structuredContent`（完整信封结构）
- `text`（紧凑 JSON 副本）

### 2. 动态截断策略

当响应超出 16 KiB 时：
1. 减半 `items` 数组
2. 重新序列化并测量大小
3. 重复直到满足上限或只剩 1 项
4. 仍超出时返回 `RESPONSE_TOO_LARGE` 错误

### 3. 所有工具统一上限

- 不按工具类型区分
- 保持一致的错误处理

## Consequences（后果）

### 正面影响

1. **编码助手友好**
   - 16 KiB 约相当于 4K-8K tokens（取决于压缩率）
   - 单次工具结果不会耗尽小上下文窗口

2. **协议兼容性好**
   - 符合 MCP SDK 设计预期
   - JSON-RPC STDIO 传输高效

3. **分页自然触发**
   - 大结果集自动分页
   - 鼓励精化查询

4. **响应时间可控**
   - 16 KiB 序列化和传输快速
   - 避免长时间阻塞

### 负面影响

1. **单条大记录受限**
   - 超大 OpenAPI 文档可能无法完整返回
   - 深层 Bean 依赖图可能截断

2. **需要多轮查询**
   - 复杂场景需要续页或精化筛选
   - 增加交互轮次

3. **截断成本**
   - 需要序列化多次测量大小
   - 最坏情况下 O(log n) 次序列化

### 缓解措施

1. **精确筛选优先**
   - 文档强调使用具体筛选条件
   - 避免一次性查询所有数据

2. **深度控制**
   - 提供 `maxDepth` 参数限制图遍历
   - 默认深度 2-4 适合大部分场景

3. **字段按需包含**
   - 健康查询的 `includeDetails` 等现有参数
   - 减少不必要的字段

4. **OpenAPI 引用深度**
   - `maxRefDepth` 默认 2，上限 8
   - 避免展开整个 Schema 树

## 替代方案

### 方案 A：32 KiB 上限

- **优点**：更少截断，单次返回更多数据
- **缺点**：编码助手上下文压力大，响应延迟增加

### 方案 B：8 KiB 上限

- **优点**：响应更快，上下文友好
- **缺点**：过度分页，小型应用体验差

### 方案 C：不限上限

- **优点**：无需截断逻辑
- **缺点**：大响应可能阻塞 STDIO，编码助手上下文溢出

### 决策理由

选择 16 KiB 是因为：
- **MCP 生态实践**：主流 MCP 服务器响应在 8-32 KiB 范围
- **编码助手兼容**：16 KiB 不会耗尽小上下文窗口
- **分页平衡**：触发分页的阈值合理，既不过严也不过松
- **实现可行**：动态截断策略简单有效

## 相关决策

- [ADR 001: 快照 60 秒 TTL](001-snapshot-ttl-and-budget.md) - 支持快速续页
- [ADR 002: maxResults 上限 50](002-max-results-limit.md) - 影响单次记录数

## 实现细节

- 响应序列化：`src/spring_runtime_mcp/transport/responses.py`
- 截断逻辑：`src/spring_runtime_mcp/tools/support.py` (`finalize`)
- 预算检查：`serialize_response` 返回字节长度

### 截断算法

```python
count = min(len(items), query.max_results)
while True:
    page = page_envelope(result, items[:count])
    try:
        serialize_response(page, request_id, sanitizer)
        break  # 满足上限
    except NormalizationError as exc:
        if exc.code != "RESPONSE_TOO_LARGE":
            raise
        if count <= 1:
            return failed("RESPONSE_TOO_LARGE", query.target_id)
        count //= 2  # 减半重试
```

## 典型场景

### 场景 1：50 个 Bean 的依赖图

- 平均每个 Bean 约 200 字节（含依赖 ID）
- 50 * 200 = 10 KiB
- 加上信封和双副本约 12-14 KiB
- ✅ 不触发截断

### 场景 2：大型 OpenAPI 文档

- 包含 100+ 操作和 Schema
- 单个操作约 500 字节
- 50 * 500 = 25 KiB
- ⚠️ 触发截断，减少到约 30 个操作

### 场景 3：健康组件树

- 包含深层嵌套（数据库 → 连接池 → 各连接）
- 每个组件约 150 字节
- 50 * 150 = 7.5 KiB
- ✅ 通常不触发截断

## 监控建议

- 统计 `RESPONSE_TOO_LARGE` 频率
- 分析触发截断的工具分布
- 监控截断前后记录数差异
- 评估是否需要调整上限
