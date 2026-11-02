# springboot_diagnose_health - 应用与依赖健康诊断

返回整体健康状态、异常组件树及已脱敏的结构化错误和修复代码；依赖故障或探针异常时调用，组件下钻在本地完成，不获取日志、堆转储或原始异常栈。

字段依据 [工具 Schema](../../../src/spring_runtime_mcp/schemas/tools-contract.json)，公共结果见[信封说明](common-envelope.md)。

## 调用规则

默认不包含健康的子节点（includeHealthy=false）及详情（includeDetails=false），异常组件仍可返回。componentPath 是本地树路径数组。固定 liveness/readiness 的 503 可作为有效健康证据；详情隐藏或组件不可读时保留 partial/unknown。

pattern 为区分大小写的有界 glob，仅 `*`、`?` 是通配符；多条件按 AND。参数不接受额外字段，约束失败不读取目标。

## 输入字段

### `arguments`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `targetId` | string | 否 | "local" | 最短 `1`；最长 `64`；正则 `^[A-Za-z0-9_-]+$(?![\s\S])` |
| `maxResults` | integer | 否 | 50 | 最小值 `1`；最大值 `50` |
| `cursor` | string | 否 | — | 最短 `1`；最长 `2048` |
| `componentPath` | array<string> | 否 | — | 最多项 `16` |
| `group` | "application" / "liveness" / "readiness" | 否 | "application" | — |
| `includeDetails` | boolean | 否 | false | — |
| `includeHealthy` | boolean | 否 | false | — |
| `maxDepth` | integer | 否 | 4 | 最小值 `0`；最大值 `16` |

此对象不接受未列出的字段。

## 查询示例

```json
{}
```

```json
{
  "group": "readiness"
}
```

```json
{
  "componentPath": [
    "db"
  ],
  "includeDetails": true,
  "includeHealthy": true
}
```

## data 字段

以下为非空 data 的字段结构；失败时 data 为 null。表中必填允许同时具有 null 类型，不能将 null 补成确定事实。

### `data`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `overallStatus` | string / null | 是 | — | 最长 `64`；— |
| `activeGroup` | "application" / "liveness" / "readiness" | 是 | — | — |
| `items` | array<object> | 是 | — | 最多项 `50` |

此对象不接受未列出的字段。

### `data.items[]`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `id` | string | 是 | — | 最长 `96` |
| `endpointId` | "health" / "health-liveness" / "health-readiness" | 是 | — | — |
| `observationId` | string | 是 | — | 最长 `96` |
| `componentPath` | array<string> | 是 | — | 最多项 `16` |
| `parentId` | string / null | 是 | — | 最长 `96`；— |
| `status` | string | 是 | — | 最长 `64` |
| `details` | array<object> | 是 | — | 最多项 `10` |
| `errorType` | string / null | 是 | — | 最长 `256`；— |
| `remediationCodes` | array<string> | 是 | — | 最多项 `4` |
| `childrenComplete` | boolean | 是 | — | — |

此对象不接受未列出的字段。

### `data.items[].details[]`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `name` | string | 是 | — | 最长 `128` |
| `value` | ['string', 'number', 'boolean', 'null'] | 是 | — | 最长 `512` |

此对象不接受未列出的字段。

## 结果解读

按 totalMatched、truncated、coverage.gaps 和 nextAction 共同解读；totalMatched=null 表示完整匹配数未知。续页使用原查询和 nextCursor，快照默认 60 秒绝对 TTL。错误配方及各类预算见[调用策略](../tool-calling-policy.md)。
