# springboot_detect_drift - 源码与运行态漂移诊断

比较调用者从获权工作区提取的 Bean、路由、迁移版本和 Profile 预期，返回差异及分级根因候选；源码与运行行为不一致时调用，省略维度不参与比较，文件时间本身不能证明未重启。

字段依据 [工具 Schema](../../../src/spring_runtime_mcp/schemas/tools-contract.json)，公共结果见[信封说明](common-envelope.md)。

## 调用规则

只比较显式提供的维度；省略数组表示不比较，显式空数组表示预期为空。expectedScopeComplete=true 且运行证据完整时才判断额外对象。Bean、路由、迁移版本预期合计最多 100 个实体。源码版本和修改时间是调用者声明，不能单凭文件较新确定进程未重启。

pattern 为区分大小写的有界 glob，仅 `*`、`?` 是通配符；多条件按 AND。参数不接受额外字段，约束失败不读取目标。

## 输入字段

### `arguments`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `targetId` | string | 否 | "local" | 最短 `1`；最长 `64`；正则 `^[A-Za-z0-9_-]+$(?![\s\S])` |
| `maxResults` | integer | 否 | 50 | 最小值 `1`；最大值 `50` |
| `cursor` | string | 否 | — | 最短 `1`；最长 `2048` |
| `expectedBeans` | array<object / object> | 否 | — | 最多项 `100` |
| `expectedRoutes` | array<object> | 否 | — | 最多项 `100` |
| `expectedMigrationVersion` | object | 否 | — | — |
| `expectedProfiles` | array<string> | 否 | — | 最多项 `20`；元素唯一 |
| `expectedScopeComplete` | boolean | 否 | false | — |
| `sourceRevision` | string | 否 | — | 最长 `128` |
| `sourceModifiedAt` | string | 否 | — | 格式 `date-time` |
| `maxDepth` | integer | 否 | 2 | 最小值 `0`；最大值 `16` |

此对象不接受未列出的字段。

### `arguments.expectedBeans[]`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `name` | string | 否 | — | 最短 `1`；最长 `256`；正则 `^[^\u0000-\u001f\u007f]+$(?![\s\S])` |
| `type` | string | 否 | — | 最短 `1`；最长 `256`；正则 `^[^\u0000-\u001f\u007f]+$(?![\s\S])` |
| `contextId` | string | 否 | — | 最短 `1`；最长 `256`；正则 `^[^\u0000-\u001f\u007f]+$(?![\s\S])` |
| `aliases` | array<string> | 否 | — | 最多项 `10` |

此对象不接受未列出的字段。

### `arguments.expectedRoutes[]`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `path` | string | 是 | — | 最短 `1`；最长 `1024`；正则 `^/[^\u0000-\u001f\u007f?#]*$(?![\s\S])` |
| `httpMethod` | "GET" / "HEAD" / "POST" / "PUT" / "PATCH" / "DELETE" / "OPTIONS" / "TRACE" / "CONNECT" | 是 | — | — |
| `controllerClass` | string | 否 | — | 最短 `1`；最长 `256`；正则 `^[^\u0000-\u001f\u007f]+$(?![\s\S])` |
| `contextId` | string | 否 | — | 最短 `1`；最长 `256`；正则 `^[^\u0000-\u001f\u007f]+$(?![\s\S])` |

此对象不接受未列出的字段。

### `arguments.expectedMigrationVersion`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `engine` | "flyway" / "liquibase" | 是 | — | — |
| `version` | string | 是 | — | 最短 `1`；最长 `256`；正则 `^[^\u0000-\u001f\u007f]+$(?![\s\S])` |
| `contextId` | string | 否 | — | 最短 `1`；最长 `256`；正则 `^[^\u0000-\u001f\u007f]+$(?![\s\S])` |
| `migrationBean` | string | 否 | — | 最短 `1`；最长 `256`；正则 `^[^\u0000-\u001f\u007f]+$(?![\s\S])` |

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
            "expectedBeans"
          ]
        },
        {
          "required": [
            "expectedRoutes"
          ]
        },
        {
          "required": [
            "expectedMigrationVersion"
          ]
        },
        {
          "required": [
            "expectedProfiles"
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
  "expectedBeans": [
    {
      "name": "orderService"
    }
  ],
  "expectedRoutes": [
    {
      "path": "/orders/{id}",
      "httpMethod": "GET"
    }
  ]
}
```

## data 字段

以下为非空 data 的字段结构；失败时 data 为 null。表中必填允许同时具有 null 类型，不能将 null 补成确定事实。

### `data`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `missingInRuntime` | array<object> | 是 | — | 最多项 `50` |
| `unexpectedInRuntime` | array<object> | 是 | — | 最多项 `50` |
| `profileMismatch` | object / null | 是 | — | —；— |
| `rootCauseInferences` | array<object> | 是 | — | 最多项 `4` |

此对象不接受未列出的字段。

### `data.missingInRuntime[]`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `id` | string | 是 | — | 最长 `96` |
| `dimension` | "beans" / "routes" / "migrations" | 是 | — | — |
| `identity` | string | 是 | — | 最长 `256` |
| `contextId` | string / null | 是 | — | 最长 `256`；— |
| `expected` | string / null | 是 | — | 最长 `256`；— |
| `actual` | string / null | 是 | — | 最长 `256`；— |
| `evidenceLevel` | "observed" / "inferred" / "unknown" | 是 | — | — |
| `affectedDependencyIds` | array<string> | 是 | — | 最多项 `16` |

此对象不接受未列出的字段。

### `data.unexpectedInRuntime[]`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `id` | string | 是 | — | 最长 `96` |
| `dimension` | "beans" / "routes" / "migrations" | 是 | — | — |
| `identity` | string | 是 | — | 最长 `256` |
| `contextId` | string / null | 是 | — | 最长 `256`；— |
| `expected` | string / null | 是 | — | 最长 `256`；— |
| `actual` | string / null | 是 | — | 最长 `256`；— |
| `evidenceLevel` | "observed" / "inferred" / "unknown" | 是 | — | — |
| `affectedDependencyIds` | array<string> | 是 | — | 最多项 `16` |

此对象不接受未列出的字段。

### `data.profileMismatch`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `expected` | array<string> | 是 | — | 最多项 `20` |
| `actual` | array<string> / null | 是 | — | 最多项 `20`；— |
| `state` | "match" / "mismatch" / "unknown" | 是 | — | — |

此对象不接受未列出的字段。

### `data.rootCauseInferences[]`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `code` | "POSSIBLE_NOT_RESTARTED" / "PROFILE_MISMATCH" / "POSSIBLE_WRONG_INSTANCE" / "ENVIRONMENT_OVERRIDE" / "INSUFFICIENT_EVIDENCE" | 是 | — | — |
| `confidence` | "supported" / "candidate" / "unknown" | 是 | — | — |
| `evidenceIds` | array<string> | 是 | — | 最多项 `8` |

此对象不接受未列出的字段。

## 结果解读

按 totalMatched、truncated、coverage.gaps 和 nextAction 共同解读；totalMatched=null 表示完整匹配数未知。续页使用原查询和 nextCursor，快照默认 60 秒绝对 TTL。错误配方及各类预算见[调用策略](../tool-calling-policy.md)。
