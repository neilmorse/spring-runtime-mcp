# springboot_inspect_beans - Bean 装配与条件诊断

返回匹配 Bean、别名及双向依赖图，并在 Bean 缺失时自动读取已授权条件报告、展开嵌套与传递阻塞链；排查注入或条件装配时调用，证据不足时返回 unknown，不猜测确切原因。

字段依据 [工具 Schema](../../../src/spring_runtime_mcp/schemas/tools-contract.json)，公共结果见[信封说明](common-envelope.md)。

## 调用规则

至少提供 beanNamePattern、typePattern 或 packagePrefix。先建立完整可见图再筛选和分页；direction 选择依赖、被依赖或双向。条件归因需要可读 conditions 与精确登记的 Source catalog；目录未覆盖不能证明 Bean 不存在。

pattern 为区分大小写的有界 glob，仅 `*`、`?` 是通配符；多条件按 AND。参数不接受额外字段，约束失败不读取目标。

## 输入字段

### `arguments`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `targetId` | string | 否 | "local" | 最短 `1`；最长 `64`；正则 `^[A-Za-z0-9_-]+$(?![\s\S])` |
| `maxResults` | integer | 否 | 50 | 最小值 `1`；最大值 `50` |
| `cursor` | string | 否 | — | 最短 `1`；最长 `2048` |
| `beanNamePattern` | string | 否 | — | 最短 `1`；最长 `128`；正则 `^[A-Za-z0-9_.$/{}:*?+@! -]+$(?![\s\S])` |
| `typePattern` | string | 否 | — | 最短 `1`；最长 `128`；正则 `^[A-Za-z0-9_.$/{}:*?+@! -]+$(?![\s\S])` |
| `packagePrefix` | string | 否 | — | 最短 `1`；最长 `256`；正则 `^[^\u0000-\u001f\u007f]+$(?![\s\S])` |
| `contextId` | string | 否 | — | 最短 `1`；最长 `256`；正则 `^[^\u0000-\u001f\u007f]+$(?![\s\S])` |
| `direction` | "dependencies" / "dependents" / "both" | 否 | "both" | — |
| `maxDepth` | integer | 否 | 2 | 最小值 `0`；最大值 `16` |
| `conditionDepth` | integer | 否 | 4 | 最小值 `0`；最大值 `16` |

此对象不接受未列出的字段。

### 选择器约束

以下为 Schema 中的组合约束：

```json
{
  "allOf": [
    {
      "anyOf": [
        {
          "required": [
            "beanNamePattern"
          ]
        },
        {
          "required": [
            "typePattern"
          ]
        },
        {
          "required": [
            "packagePrefix"
          ]
        }
      ]
    }
  ]
}
```

## 查询示例

```json
{
  "beanNamePattern": "orderService"
}
```

```json
{
  "typePattern": "example.*",
  "direction": "dependents",
  "maxDepth": 4
}
```

## data 字段

以下为非空 data 的字段结构；失败时 data 为 null。表中必填允许同时具有 null 类型，不能将 null 补成确定事实。

### `data`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `items` | array<object> | 是 | — | 最多项 `50` |
| `missingBeanAnalysis` | object | 是 | — | — |

此对象不接受未列出的字段。

### `data.items[]`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `id` | string | 是 | — | 最长 `96` |
| `endpointId` | "beans" | 是 | — | — |
| `observationId` | string | 是 | — | 最长 `96` |
| `contextId` | string / null | 是 | — | 最长 `256`；— |
| `parentContextId` | string / null | 是 | — | 最长 `256`；— |
| `name` | string | 是 | — | 最长 `256` |
| `type` | string / null | 是 | — | 最长 `256`；— |
| `scope` | string / null | 是 | — | 最长 `64`；— |
| `resource` | string / null | 是 | — | 最长 `256`；— |
| `aliases` | array<string> | 是 | — | 最多项 `16` |
| `producer` | object / null | 是 | — | —；— |
| `dependencies` | array<object> | 是 | — | 最多项 `16` |
| `dependents` | array<object> | 是 | — | 最多项 `16` |

此对象不接受未列出的字段。

### `data.items[].producer`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `kind` | "configuration" / "factoryMethod" / "factoryBean" | 是 | — | — |
| `configurationClass` | string / null | 是 | — | 最长 `256`；— |
| `methodName` | string / null | 是 | — | 最长 `256`；— |
| `evidenceLevel` | "observed" / "correlated" | 是 | — | — |

此对象不接受未列出的字段。

### `data.items[].dependencies[]`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `fromId` | string | 是 | — | 最长 `96` |
| `toId` | string / null | 是 | — | 最长 `96`；— |
| `requestedName` | string / null | 是 | — | 最长 `256`；— |
| `targetContextId` | string / null | 是 | — | 最长 `256`；— |
| `targetName` | string / null | 是 | — | 最长 `256`；— |
| `resolution` | "resolved" / "ambiguous" / "unresolved" | 是 | — | — |
| `depth` | integer | 是 | — | 最小值 `0`；最大值 `16` |

此对象不接受未列出的字段。

### `data.items[].dependents[]`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `fromId` | string | 是 | — | 最长 `96` |
| `toId` | string / null | 是 | — | 最长 `96`；— |
| `requestedName` | string / null | 是 | — | 最长 `256`；— |
| `targetContextId` | string / null | 是 | — | 最长 `256`；— |
| `targetName` | string / null | 是 | — | 最长 `256`；— |
| `resolution` | "resolved" / "ambiguous" / "unresolved" | 是 | — | — |
| `depth` | integer | 是 | — | 最小值 `0`；最大值 `16` |

此对象不接受未列出的字段。

### `data.missingBeanAnalysis`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `state` | "notNeeded" / "explained" / "partial" / "unknown" | 是 | — | — |
| `conditions` | array<object> | 是 | — | 最多项 `16` |
| `blockingPaths` | array<array<string>> | 是 | — | 最多项 `8` |

此对象不接受未列出的字段。

### `data.missingBeanAnalysis.conditions[]`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `id` | string | 是 | — | 最长 `96` |
| `configurationClass` | string / null | 是 | — | 最长 `256`；— |
| `conditionType` | string / null | 是 | — | 最长 `256`；— |
| `operator` | "leaf" / "any" / "all" / "none" / "unknown" | 是 | — | — |
| `outcome` | "matched" / "notMatched" / "unknown" | 是 | — | — |
| `reasonCode` | string | 是 | — | 最长 `64` |
| `childIds` | array<string> | 是 | — | 最多项 `16` |
| `requiredBeanIds` | array<string> | 是 | — | 最多项 `16` |
| `childrenComplete` | boolean | 是 | — | — |

此对象不接受未列出的字段。

## 结果解读

按 totalMatched、truncated、coverage.gaps 和 nextAction 共同解读；totalMatched=null 表示完整匹配数未知。续页使用原查询和 nextCursor，快照默认 60 秒绝对 TTL。错误配方及各类预算见[调用策略](../tool-calling-policy.md)。
