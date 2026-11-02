# springboot_search_openapi - OpenAPI 查询

返回匹配操作或 Schema，并默认内联直接与二阶同文档引用；确认接口契约时使用精确选择器调用，不执行业务接口、不返回全量文档，也不解析远程引用。

字段依据 [工具 Schema](../../../src/spring_runtime_mcp/schemas/tools-contract.json)，公共结果见[信封说明](common-envelope.md)。

## 调用规则

schemaName 与操作查询互斥。操作查询至少提供 pathPattern 或 operationId；httpMethod 不能单独查询。固定 GET /actuator/openapi，不执行 API，也不请求远程引用。maxRefDepth 默认 2、上限 8；自由描述不出站。

pattern 为区分大小写的有界 glob，仅 `*`、`?` 是通配符；多条件按 AND。参数不接受额外字段，约束失败不读取目标。

## 输入字段

### `arguments`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `targetId` | string | 否 | "local" | 最短 `1`；最长 `64`；正则 `^[A-Za-z0-9_-]+$(?![\s\S])` |
| `maxResults` | integer | 否 | 50 | 最小值 `1`；最大值 `50` |
| `cursor` | string | 否 | — | 最短 `1`；最长 `2048` |
| `pathPattern` | string | 否 | — | 最短 `1`；最长 `128`；正则 `^[A-Za-z0-9_.$/{}:*?+@! -]+$(?![\s\S])` |
| `httpMethod` | "GET" / "HEAD" / "POST" / "PUT" / "PATCH" / "DELETE" / "OPTIONS" / "TRACE" / "CONNECT" | 否 | — | — |
| `operationId` | string | 否 | — | 最短 `1`；最长 `256`；正则 `^[^\u0000-\u001f\u007f]+$(?![\s\S])` |
| `schemaName` | string | 否 | — | 最短 `1`；最长 `256`；正则 `^[^\u0000-\u001f\u007f]+$(?![\s\S])` |
| `maxRefDepth` | integer | 否 | 2 | 最小值 `0`；最大值 `8` |

此对象不接受未列出的字段。

### 选择器约束

以下为 Schema 中的组合约束：

```json
{
  "allOf": [
    {
      "oneOf": [
        {
          "required": [
            "schemaName"
          ],
          "not": {
            "anyOf": [
              {
                "required": [
                  "pathPattern"
                ]
              },
              {
                "required": [
                  "httpMethod"
                ]
              },
              {
                "required": [
                  "operationId"
                ]
              }
            ]
          }
        },
        {
          "anyOf": [
            {
              "required": [
                "pathPattern"
              ]
            },
            {
              "required": [
                "operationId"
              ]
            }
          ],
          "not": {
            "required": [
              "schemaName"
            ]
          }
        }
      ]
    }
  ]
}
```

## 查询示例

```json
{
  "pathPattern": "/api/users/*",
  "httpMethod": "GET"
}
```

```json
{
  "operationId": "getUser"
}
```

```json
{
  "schemaName": "User",
  "maxRefDepth": 2
}
```

## data 字段

以下为非空 data 的字段结构；失败时 data 为 null。表中必填允许同时具有 null 类型，不能将 null 补成确定事实。

### `data`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `openapiVersion` | string / null | 是 | — | 最长 `32`；— |
| `candidateId` | string / null | 是 | — | 最长 `64`；— |
| `items` | array<object> | 是 | — | 最多项 `50` |

此对象不接受未列出的字段。

### `data.items[]`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `id` | string | 是 | — | 最长 `96` |
| `endpointId` | "openapi" | 是 | — | — |
| `observationId` | string | 是 | — | 最长 `96` |
| `kind` | "operation" / "schema" | 是 | — | — |
| `path` | string / null | 是 | — | 最短 `1`；最长 `1024`；正则 `^/[^\u0000-\u001f\u007f?#]*$(?![\s\S])`；— |
| `httpMethod` | "GET" / "HEAD" / "POST" / "PUT" / "PATCH" / "DELETE" / "OPTIONS" / "TRACE" / "CONNECT" / null | 是 | — | —；— |
| `operationId` | string / null | 是 | — | 最长 `256`；— |
| `schemaName` | string / null | 是 | — | 最长 `256`；— |
| `parameters` | array<object> | 是 | — | 最多项 `16` |
| `requestBody` | array<object> | 是 | — | 最多项 `8` |
| `responses` | array<object> | 是 | — | 最多项 `16` |
| `schema` | Schema / null | 是 | — | —；— |
| `expansionComplete` | boolean | 是 | — | — |

此对象不接受未列出的字段。

### `data.items[].parameters[]`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `name` | string | 是 | — | 最长 `128` |
| `in` | "path" / "query" / "header" / "cookie" | 是 | — | — |
| `required` | boolean | 是 | — | — |
| `schema` | Schema | 是 | — | — |

此对象不接受未列出的字段。

### `data.items[].requestBody[]`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `mediaType` | string | 是 | — | 最长 `128` |
| `schema` | Schema | 是 | — | — |

此对象不接受未列出的字段。

### `data.items[].responses[]`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `status` | string | 是 | — | 最长 `16` |
| `mediaType` | string / null | 是 | — | 最长 `128`；— |
| `schema` | Schema / null | 是 | — | —；— |

此对象不接受未列出的字段。

### `$defs.Schema`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `type` | "null" / "boolean" / "object" / "array" / "number" / "string" / "integer" / array<"null" / "boolean" / "object" / "array" / "number" / "string" / "integer"> | 否 | — | —；最多项 `7` |
| `format` | string | 否 | — | 最长 `64` |
| `nullable` | boolean | 否 | — | — |
| `readOnly` | boolean | 否 | — | — |
| `writeOnly` | boolean | 否 | — | — |
| `minimum` | number | 否 | — | — |
| `maximum` | number | 否 | — | — |
| `exclusiveMinimum` | ['number', 'boolean'] | 否 | — | — |
| `exclusiveMaximum` | ['number', 'boolean'] | 否 | — | — |
| `multipleOf` | number | 否 | — | — |
| `minLength` | integer | 否 | — | 最小值 `0` |
| `maxLength` | integer | 否 | — | 最小值 `0` |
| `pattern` | string | 否 | — | 最长 `512` |
| `minItems` | integer | 否 | — | 最小值 `0` |
| `maxItems` | integer | 否 | — | 最小值 `0` |
| `uniqueItems` | boolean | 否 | — | — |
| `required` | array<string> | 否 | — | 最多项 `50` |
| `properties` | object | 否 | — | — |
| `items` | Schema | 否 | — | — |
| `additionalProperties` | boolean / Schema | 否 | — | —；— |
| `allOf` | array<Schema> | 否 | — | 最多项 `16` |
| `oneOf` | array<Schema> | 否 | — | 最多项 `16` |
| `anyOf` | array<Schema> | 否 | — | 最多项 `16` |
| `$ref` | string | 否 | — | 最长 `512`；正则 `^#(?:/.*)?$(?![\s\S])` |
| `referenceState` | "resolved" / "cycle" / "depthLimit" / "invalid" / "externalBlocked" / "unsupported" | 否 | — | — |
| `omissionCodes` | array<string> | 否 | — | 最多项 `8` |
| `enum` | array<['string', 'number', 'boolean', 'null']> | 否 | — | 最多项 `16` |

此对象不接受未列出的字段。

## 结果解读

按 totalMatched、truncated、coverage.gaps 和 nextAction 共同解读；totalMatched=null 表示完整匹配数未知。续页使用原查询和 nextCursor，快照默认 60 秒绝对 TTL。错误配方及各类预算见[调用策略](../tool-calling-policy.md)。
