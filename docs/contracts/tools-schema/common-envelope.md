# 公共信封结构

八工具的领域结果同时以 structuredContent 和同内容的紧凑 JSON 文本提供；完整 JSON-RPC 工具回包最多 16,384 UTF-8 字节。字段以[工具 Schema](../../../src/spring_runtime_mcp/schemas/tools-contract.json)为准。

## 状态与证据

schemaVersion 是字符串常量 "2"。ok/partial 为有效诊断（isError=false）；健康 DOWN、迁移失败或漂移事实不等于工具调用错误。失败信封的 data、totalMatched、nextCursor 为 null，errors 至少一项，coverage.state=unavailable。

failed() 当前将 INVALID_ARGUMENT 映射为 invalid，将 ENDPOINT_UNAUTHORIZED/TARGET_NOT_REGISTERED 映射为 denied，其余失败映射为 unavailable。too_large 是 Schema 允许的状态，不能据此宣称当前每个预算错误都会返回该状态。

证据不足保留 null/unknown/partial。truncated 还可能由深度、关联或分析预算导致，并不保证存在可续页记录。redactions 记录安全输出字段/索引，不是固定的脱敏类型枚举。时间字段使用受限 RFC3339 校验，详见[实现约定](../../architecture/implementation-conventions.md)。

## 信封字段

### `envelope`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `schemaVersion` | "2" | 是 | — | — |
| `status` | "ok" / "partial" / "denied" / "unavailable" / "invalid" / "too_large" | 是 | — | — |
| `source` | object | 是 | — | — |
| `totalMatched` | integer / null | 是 | — | 最小值 `0`；— |
| `truncated` | boolean | 是 | — | — |
| `truncationReasons` | array<string> | 是 | — | 最多项 `8` |
| `coverage` | object | 是 | — | — |
| `warnings` | array<object> | 是 | — | 最多项 `10` |
| `redactions` | array<string> | 是 | — | 最多项 `50` |
| `nextCursor` | string / null | 是 | — | 最长 `2048`；— |
| `nextAction` | object | 是 | — | — |
| `errors` | array<DiagnosticError> | 是 | — | 最多项 `8` |

此对象不接受未列出的字段。

### `envelope.source`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `targetId` | string | 是 | — | 最长 `64` |
| `snapshotId` | string / null | 是 | — | 最长 `96`；— |
| `observedAt` | string | 是 | — | 格式 `date-time` |
| `endpointIds` | array<"startup" / "flyway" / "liquibase" / "beans" / "conditions" / "mappings" / "health" / "health-liveness" / "health-readiness" / "env" / "configprops" / "env-property" / "info" / "openapi"> | 是 | — | 最多项 `14`；元素唯一 |
| `bootVersion` | string / null | 是 | — | 最长 `64`；— |
| `adapterVersion` | string | 是 | — | 最长 `32` |
| `policyVersion` | string | 是 | — | 最长 `32` |

此对象不接受未列出的字段。

### `envelope.coverage`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `state` | "complete" / "partial" / "unavailable" | 是 | — | — |
| `scope` | string | 是 | — | 最长 `256` |
| `gaps` | array<string> | 是 | — | 最多项 `10` |

此对象不接受未列出的字段。

### `envelope.warnings[]`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `code` | string | 是 | — | 最长 `64` |
| `recordId` | string / null | 是 | — | 最长 `96`；— |

此对象不接受未列出的字段。

### `envelope.nextAction`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `kind` | "done" / "refine" / "page" / "remediate" | 是 | — | — |
| `reasonCode` | string | 是 | — | 最长 `64`；正则 `^[A-Z][A-Z0-9_]*$(?![\s\S])` |
| `filterSuggestions` | array<object> | 是 | — | 最多项 `4` |

此对象不接受未列出的字段。

### `envelope.nextAction.filterSuggestions[]`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `parameter` | string | 是 | — | 最长 `64` |
| `value` | ['string', 'number', 'boolean', 'null'] / array<string> | 是 | — | 最长 `512`；最多项 `10` |

此对象不接受未列出的字段。

data 是各工具定义的 object 或 null，具体字段见对应工具文档。source.endpointIds 的 Schema 枚举也包含保留身份，不能据此推导支持动态 env-property 或 info 请求；实际固定端点见[安全架构](../../architecture/security-and-sanitization.md)。

### `DiagnosticError`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `code` | string | 是 | — | 最长 `64`；正则 `^[A-Z][A-Z0-9_]*$(?![\s\S])` |
| `endpointId` | "startup" / "flyway" / "liquibase" / "beans" / "conditions" / "mappings" / "health" / "health-liveness" / "health-readiness" / "env" / "configprops" / "env-property" / "info" / "openapi" / null | 是 | — | —；— |
| `httpStatus` | integer / null | 是 | — | 最小值 `100`；最大值 `599`；— |
| `retryable` | boolean | 是 | — | — |
| `message` | string | 是 | — | 最长 `256` |
| `remediation` | object | 是 | — | — |

此对象不接受未列出的字段。

### `DiagnosticError.remediation`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `recipeId` | string | 是 | — | 最长 `96` |
| `action` | "refineQuery" / "configureCapability" / "reviewExposure" / "reviewAuthorization" / "configureStartup" / "reviewTarget" / "reviewSource" / "stop" | 是 | — | — |
| `configKeys` | array<string> | 是 | — | 最多项 `8` |
| `steps` | array<string> | 是 | — | 最多项 `4` |
| `requiresApproval` | boolean | 是 | — | — |
| `retryAfterMs` | integer / null | 是 | — | 最小值 `0`；最大值 `5000`；— |

此对象不接受未列出的字段。

## 分页与错误处理

首次查询不传 cursor；续页重发原工具和所有规范化查询参数，只增加服务端返回的 nextCursor。游标为不透明句柄，不解码或自行拼接。默认快照 TTL 60 秒、总预算 32 MiB，续页不延长期限，过期或进程重启后需建立新查询。

记录数、字节、关联和深度预算分别约束输出。通用分页会收缩条目数，Bean 工具还可裁剪关联；仍无法安全容纳时返回固定错误。不存在所有工具统一“自动减半且至少保留一条”的保证。

错误消息、配方由本地模板产生，不回显上游建议。retryable 当前固定 false，retryAfterMs 固定 null；INVALID_ARGUMENT 配方 requiresApproval=false，其他为 true，仍需核对已有同范围授权。错误码与状态、配方的对应关系见[调用策略](../tool-calling-policy.md)。
