# springboot_inspect_config - 配置来源检查

返回双层强制脱敏后的生效属性、绑定 Bean、来源位置及 Active Profiles；排查属性绑定或配置覆盖时按前缀或键模式调用，能力默认关闭且不能用于获取秘密或导出全量配置。

字段依据 [工具 Schema](../../../src/spring_runtime_mcp/schemas/tools-contract.json)，公共结果见[信封说明](common-envelope.md)。

## 调用规则

至少提供 prefix 或 propertyKeyPattern。配置诊断默认关闭，查询与 CLI 登记范围取交集；includeValues=true 还需 --config-allow-values，值始终脱敏。网络仍读取固定完整 env/configprops，不能据本地筛选声称减少上游响应大小。

pattern 为区分大小写的有界 glob，仅 `*`、`?` 是通配符；多条件按 AND。参数不接受额外字段，约束失败不读取目标。

## 输入字段

### `arguments`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `targetId` | string | 否 | "local" | 最短 `1`；最长 `64`；正则 `^[A-Za-z0-9_-]+$(?![\s\S])` |
| `maxResults` | integer | 否 | 50 | 最小值 `1`；最大值 `50` |
| `cursor` | string | 否 | — | 最短 `1`；最长 `2048` |
| `prefix` | string | 否 | — | 最短 `1`；最长 `128`；正则 `^[A-Za-z_][A-Za-z0-9_.-]*$(?![\s\S])` |
| `propertyKeyPattern` | string | 否 | — | 最短 `1`；最长 `128`；正则 `^[A-Za-z0-9_.$/{}:*?+@! -]+$(?![\s\S])` |
| `contextId` | string | 否 | — | 最短 `1`；最长 `256`；正则 `^[^\u0000-\u001f\u007f]+$(?![\s\S])` |
| `includeValues` | boolean | 否 | false | — |

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
            "prefix"
          ]
        },
        {
          "required": [
            "propertyKeyPattern"
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
  "propertyKeyPattern": "server.port"
}
```

```json
{
  "prefix": "app.feature",
  "includeValues": true
}
```

## data 字段

以下为非空 data 的字段结构；失败时 data 为 null。表中必填允许同时具有 null 类型，不能将 null 补成确定事实。

### `data`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `activeProfiles` | array<string> / null | 是 | — | 最多项 `20`；— |
| `items` | array<object> | 是 | — | 最多项 `50` |

此对象不接受未列出的字段。

### `data.items[]`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `id` | string | 是 | — | 最长 `96` |
| `endpointId` | "env" / "configprops" / "env-property" | 是 | — | — |
| `observationId` | string | 是 | — | 最长 `96` |
| `contextId` | string / null | 是 | — | 最长 `256`；— |
| `parentContextId` | string / null | 是 | — | 最长 `256`；— |
| `propertyKey` | string | 是 | — | 最长 `256` |
| `prefix` | string / null | 是 | — | 最长 `256`；— |
| `configurationBean` | string / null | 是 | — | 最长 `256`；— |
| `effectiveValue` | ['string', 'number', 'boolean', 'null'] | 是 | — | 最长 `512` |
| `valueState` | "visible" / "redacted" / "notReported" | 是 | — | — |
| `bindingValue` | ['string', 'number', 'boolean', 'null'] | 是 | — | 最长 `512` |
| `bindingState` | "visible" / "redacted" / "notReported" | 是 | — | — |
| `origin` | object | 是 | — | — |
| `sourceKind` | "configurationFile" / "environmentVariable" / "systemProperty" / "commandLine" / "other" / "unknown" | 是 | — | — |
| `effective` | "yes" / "no" / "unknown" | 是 | — | — |

此对象不接受未列出的字段。

### `data.items[].origin`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `kind` | "configurationFile" / "environmentVariable" / "systemProperty" / "commandLine" / "other" / "unknown" | 是 | — | — |
| `file` | string / null | 是 | — | 最长 `256`；— |
| `line` | integer / null | 是 | — | 最小值 `1`；— |
| `column` | integer / null | 是 | — | 最小值 `1`；— |
| `environmentVariable` | string / null | 是 | — | 最长 `128`；正则 `^[A-Za-z_][A-Za-z0-9_]*$(?![\s\S])`；— |

此对象不接受未列出的字段。

## CLI 登记示例

以下参数先由操作者按获权范围登记，重复选项逐项传值；--config-profiles 是布尔开关，供活动 Profile 读取。

```bash
spring-runtime-mcp --base-url http://127.0.0.1:18081 \
  --config-prefix app.feature --config-prefix spring.application \
  --config-property server.port --config-property server.ssl.enabled \
  --config-profiles --config-allow-values
```

以上命令启动 STDIO 宿主；凭据转发和实际查询见[首次接入](../../first-query.md)。

## 结果解读

按 totalMatched、truncated、coverage.gaps 和 nextAction 共同解读；totalMatched=null 表示完整匹配数未知。续页使用原查询和 nextCursor，快照默认 60 秒绝对 TTL。错误配方及各类预算见[调用策略](../tool-calling-policy.md)。
