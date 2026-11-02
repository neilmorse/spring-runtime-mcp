# ADR 002: maxResults 上限 50

**状态**：已接受

**日期**：2024-11

---

## Context（上下文）

八个诊断工具返回可变数量的记录（Bean、路由、迁移、健康组件等）。需要平衡：

1. **单次查询有效性**：返回足够多的记录便于分析
2. **响应大小控制**：避免超出 16 KiB 响应上限
3. **目标应用负载**：减少对 Actuator 端点的压力
4. **分析预算**：限制 Bean 图遍历、条件链展开等计算开销

关键约束：
- 完整 JSON-RPC 响应上限 16,384 字节
- 单工具调用时限 15 秒
- 编码助手上下文有限，过多结果难以消化
- 依赖图分析有指数级计算风险

## Decision（决策）

设定 `maxResults` 上限为 **50**：

### 1. 默认值和上限均为 50

```json
{
  "maxResults": {
    "type": "integer",
    "minimum": 1,
    "maximum": 50,
    "default": 50
  }
}
```

### 2. 所有八工具统一上限

- 不按工具类型区分上限
- 保持契约一致性

### 3. 超出上限时分页

- 设置 `truncated: true`
- 提供 `nextCursor` 续页
- 返回 `nextAction: {kind: "page"}`

## Consequences（后果）

### 正面影响

1. **响应大小可控**
   - 50 条记录通常在 8-12 KiB 范围内
   - 为信封元数据和双副本留出足够空间

2. **编码助手友好**
   - 50 条记录适合单轮分析
   - 过多结果反而难以理解

3. **分析预算合理**
   - Bean 图遍历最多 50 个起点
   - 条件链展开受控

4. **目标应用负载平衡**
   - 单次读取 50 条记录不会压垮小型应用
   - 避免一次性拉取数百个 Bean

### 负面影响

1. **需要续页**
   - 大型应用（100+ Bean）需要多次查询
   - 增加交互轮次

2. **全量分析受限**
   - 无法一次性获取所有记录
   - 统计类查询需要多次聚合

### 缓解措施

1. **精确筛选优先**
   - 文档强调使用 `packagePrefix`、`beanNamePattern` 等筛选
   - 鼓励精化查询而非依赖大 `maxResults`

2. **续页机制完善**
   - 60 秒 TTL 支持快速续页
   - `nextAction` 提供明确续页指示

3. **工具组合**
   - 先用精确筛选定位目标
   - 再用依赖图查询关联对象

## 替代方案

### 方案 A：上限 100

- **优点**：减少续页频率
- **缺点**：响应超出 16 KiB 风险高，分析预算压力大

### 方案 B：上限 20

- **优点**：响应更小，分析更快
- **缺点**：续页过于频繁，小型应用体验差

### 方案 C：按工具区分上限

- **优点**：针对性优化（如健康组件上限 100，Bean 上限 30）
- **缺点**：契约不一致，用户困惑

### 决策理由

选择 50 是因为：
- **经验数据**：测试中 50 条 Bean 记录约 10 KiB（含依赖图）
- **编码助手上下文**：50 条记录是单轮分析的合理上限
- **分页成本**：60 秒 TTL 使续页开销可接受
- **统一契约**：所有工具保持一致

## 相关决策

- [ADR 001: 快照 60 秒 TTL](001-snapshot-ttl-and-budget.md) - 影响续页体验
- [ADR 003: 响应上限 16 KiB](003-response-size-cap.md) - 决定 maxResults 上限

## 实现细节

- Schema 定义：`src/spring_runtime_mcp/schemas/tools-contract.json`
- 分页实现：`src/spring_runtime_mcp/tools/support.py` (`finalize`)
- 截断逻辑：动态减半 `items` 直到满足 16 KiB 或剩 1 项

## 典型用例

### 用例 1：查询单个 Bean
```json
{
  "beanNamePattern": "userService",
  "maxResults": 1  // 精确查询，不需要 50
}
```

### 用例 2：包扫描
```json
{
  "packagePrefix": "com.example.service",
  "maxResults": 50  // 可能匹配 20-30 个 Bean
}
```

### 用例 3：全量 Bean 审计
```json
// 首次查询
{
  "beanNamePattern": "*",
  "maxResults": 50
}
// 续页查询（如果 totalMatched > 50）
{
  "beanNamePattern": "*",
  "maxResults": 50,
  "cursor": "..."
}
```

## 监控建议

- 统计 `truncated: true` 频率
- 分析续页查询占比
- 监控单工具平均返回记录数
