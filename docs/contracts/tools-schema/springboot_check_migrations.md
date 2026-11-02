# springboot_check_migrations - 数据库迁移审计

返回所有容器和迁移 Bean 的已报告迁移、校验和、顺序及异常状态；排查迁移失败或版本差异时调用，未报告的待执行状态需要可信预期，且不会执行 SQL 或迁移。

字段依据 [工具 Schema](../../../src/spring_runtime_mcp/schemas/tools-contract.json)，公共结果见[信封说明](common-envelope.md)。

## 调用规则

engine=auto 分别读取两引擎；只根据已报告库存或完整可信基线表达 pending，不执行迁移。expectedSetComplete 允许对完整读取引擎中未出现的预期记录推导 PENDING，不表示实现了额外迁移检测。Liquibase 不具有 Flyway 的标准版本语义。

pattern 为区分大小写的有界 glob，仅 `*`、`?` 是通配符；多条件按 AND。参数不接受额外字段，约束失败不读取目标。

## 输入字段

### `arguments`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `targetId` | string | 否 | "local" | 最短 `1`；最长 `64`；正则 `^[A-Za-z0-9_-]+$(?![\s\S])` |
| `maxResults` | integer | 否 | 50 | 最小值 `1`；最大值 `50` |
| `cursor` | string | 否 | — | 最短 `1`；最长 `2048` |
| `engine` | "auto" / "flyway" / "liquibase" | 否 | "auto" | — |
| `contextId` | string | 否 | — | 最短 `1`；最长 `256`；正则 `^[^\u0000-\u001f\u007f]+$(?![\s\S])` |
| `migrationBean` | string | 否 | — | 最短 `1`；最长 `256`；正则 `^[^\u0000-\u001f\u007f]+$(?![\s\S])` |
| `state` | array<"APPLIED" / "PENDING" / "FAILED" / "OUT_OF_ORDER" / "MISSING_FAILED" / "UNKNOWN"> | 否 | — | 最多项 `6`；元素唯一 |
| `version` | string | 否 | — | 最长 `128` |
| `expectedMigrations` | array<object> | 否 | — | 最多项 `100` |
| `expectedSetComplete` | boolean | 否 | false | — |

此对象不接受未列出的字段。

### `arguments.expectedMigrations[]`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `engine` | "flyway" / "liquibase" | 是 | — | — |
| `contextId` | string | 是 | — | 最短 `1`；最长 `256`；正则 `^[^\u0000-\u001f\u007f]+$(?![\s\S])` |
| `migrationBean` | string | 是 | — | 最短 `1`；最长 `256`；正则 `^[^\u0000-\u001f\u007f]+$(?![\s\S])` |
| `identity` | string | 是 | — | 最短 `1`；最长 `256`；正则 `^[^\u0000-\u001f\u007f]+$(?![\s\S])` |
| `version` | string / null | 否 | — | 最长 `128`；— |
| `checksum` | string / null | 否 | — | 最长 `128`；— |

此对象不接受未列出的字段。

## 查询示例

```json
{
  "engine": "flyway"
}
```

```json
{
  "state": [
    "FAILED",
    "MISSING_FAILED"
  ]
}
```

## data 字段

以下为非空 data 的字段结构；失败时 data 为 null。表中必填允许同时具有 null 类型，不能将 null 补成确定事实。

### `data`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `pendingVisibility` | "reported" / "baselineInferred" / "unknown" | 是 | — | — |
| `items` | array<object> | 是 | — | 最多项 `50` |

此对象不接受未列出的字段。

### `data.items[]`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `id` | string | 是 | — | 最长 `96` |
| `endpointId` | "flyway" / "liquibase" | 是 | — | — |
| `observationId` | string | 是 | — | 最长 `96` |
| `contextId` | string / null | 是 | — | 最长 `256`；— |
| `parentContextId` | string / null | 是 | — | 最长 `256`；— |
| `engine` | "flyway" / "liquibase" | 是 | — | — |
| `migrationBean` | string | 是 | — | 最长 `256` |
| `identity` | string | 是 | — | 最长 `256` |
| `script` | string / null | 是 | — | 最长 `256`；— |
| `changeLog` | string / null | 是 | — | 最长 `256`；— |
| `changeSetId` | string / null | 是 | — | 最长 `256`；— |
| `author` | string / null | 是 | — | 最长 `256`；— |
| `version` | string / null | 是 | — | 最长 `128`；— |
| `description` | string / null | 是 | — | 最长 `256`；— |
| `checksum` | string / null | 是 | — | 最长 `128`；— |
| `checksumType` | "number" / "string" / "absent" | 是 | — | — |
| `checksumAlgorithm` | string / null | 是 | — | 最长 `64`；— |
| `executionTimeMs` | number / null | 是 | — | 最小值 `0`；— |
| `orderExecuted` | integer / null | 是 | — | 最小值 `0`；— |
| `executedAt` | string / null | 是 | — | 最长 `64`；— |
| `rawState` | string / null | 是 | — | 最长 `64`；— |
| `state` | "APPLIED" / "PENDING" / "FAILED" / "OUT_OF_ORDER" / "MISSING_FAILED" / "UNKNOWN" | 是 | — | — |
| `stateEvidence` | "reported" / "baselineInferred" / "unknown" | 是 | — | — |
| `attentionRequired` | boolean | 是 | — | — |

此对象不接受未列出的字段。

## 结果解读

按 totalMatched、truncated、coverage.gaps 和 nextAction 共同解读；totalMatched=null 表示完整匹配数未知。续页使用原查询和 nextCursor，快照默认 60 秒绝对 TTL。错误配方及各类预算见[调用策略](../tool-calling-policy.md)。
