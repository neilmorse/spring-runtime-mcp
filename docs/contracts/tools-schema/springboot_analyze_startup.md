# springboot_analyze_startup - 启动瓶颈诊断

返回非破坏性启动快照中的版本、时间线跨度、最慢步骤及父子链；排查慢启动时调用，不用于当前请求延迟，也不执行排空缓冲区的 POST。

字段依据 [工具 Schema](../../../src/spring_runtime_mcp/schemas/tools-contract.json)，公共结果见[信封说明](common-envelope.md)。

## 调用规则

读取固定 GET startup 快照；时间线跨度不是 JVM 完整启动时间，重叠步骤不相加。单位、父节点或时间证据缺失时保留 gaps。

pattern 为区分大小写的有界 glob，仅 `*`、`?` 是通配符；多条件按 AND。参数不接受额外字段，约束失败不读取目标。

## 输入字段

### `arguments`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `targetId` | string | 否 | "local" | 最短 `1`；最长 `64`；正则 `^[A-Za-z0-9_-]+$(?![\s\S])` |
| `maxResults` | integer | 否 | 50 | 最小值 `1`；最大值 `50` |
| `cursor` | string | 否 | — | 最短 `1`；最长 `2048` |
| `stepNamePattern` | string | 否 | — | 最短 `1`；最长 `128`；正则 `^[A-Za-z0-9_.$/{}:*?+@! -]+$(?![\s\S])` |
| `beanNamePattern` | string | 否 | — | 最短 `1`；最长 `128`；正则 `^[A-Za-z0-9_.$/{}:*?+@! -]+$(?![\s\S])` |
| `minDurationMs` | number | 否 | 0 | 最小值 `0` |
| `maxDepth` | integer | 否 | 4 | 最小值 `0`；最大值 `16` |

此对象不接受未列出的字段。

## 查询示例

```json
{
  "minDurationMs": 100,
  "maxResults": 10
}
```

```json
{
  "stepNamePattern": "spring.beans.*",
  "maxDepth": 8
}
```

## data 字段

以下为非空 data 的字段结构；失败时 data 为 null。表中必填允许同时具有 null 类型，不能将 null 补成确定事实。

### `data`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `springBootVersion` | string / null | 是 | — | 最长 `64`；— |
| `totalDurationMs` | number / null | 是 | — | 最小值 `0`；— |
| `durationBasis` | "timelineSpan" / "unknown" | 是 | — | — |
| `timelineComplete` | boolean | 是 | — | — |
| `items` | array<object> | 是 | — | 最多项 `50` |

此对象不接受未列出的字段。

### `data.items[]`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `id` | string | 是 | — | 最长 `96` |
| `endpointId` | "startup" | 是 | — | — |
| `observationId` | string | 是 | — | 最长 `96` |
| `stepId` | string | 是 | — | 最长 `20`；正则 `^[0-9]+$(?![\s\S])` |
| `parentStepId` | string / null | 是 | — | 最长 `20`；正则 `^[0-9]+$(?![\s\S])`；— |
| `name` | string | 是 | — | 最长 `256` |
| `startedAt` | string / null | 是 | — | 格式 `date-time`；— |
| `durationNanos` | string / null | 是 | — | 最长 `30`；正则 `^[0-9]+$(?![\s\S])`；— |
| `durationMs` | number / null | 是 | — | 最小值 `0`；— |
| `tags` | array<object> | 是 | — | 最多项 `10` |
| `ancestorIds` | array<string> | 是 | — | 最多项 `16` |
| `relationState` | "resolved" / "orphan" / "cycle" / "duplicate" | 是 | — | — |
| `bottleneckCode` | "BEAN_INSTANTIATION" / "PACKAGE_SCAN" / "AUTO_CONFIGURATION" / "OTHER" / "UNKNOWN" | 是 | — | — |

此对象不接受未列出的字段。

### `data.items[].tags[]`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `key` | string | 是 | — | 最长 `128` |
| `value` | string / null | 是 | — | 最长 `256`；— |

此对象不接受未列出的字段。

## 结果解读

按 totalMatched、truncated、coverage.gaps 和 nextAction 共同解读；totalMatched=null 表示完整匹配数未知。续页使用原查询和 nextCursor，快照默认 60 秒绝对 TTL。错误配方及各类预算见[调用策略](../tool-calling-policy.md)。
