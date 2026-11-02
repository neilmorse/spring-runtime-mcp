# springboot_verify_mappings - 路由注册验证

返回统一的 MVC/WebFlux 路由、处理器和方法描述符；排查路径、方法或 Controller 未注册时调用，不向业务 URL 发请求，也不把注册匹配等同于请求一定成功。

字段依据 [工具 Schema](../../../src/spring_runtime_mcp/schemas/tools-contract.json)，公共结果见[信封说明](common-envelope.md)。

## 调用规则

至少提供 pathPattern、httpMethod 或 controllerClassPattern。只读取 mappings，不调用业务路径。非 DispatcherServlet 覆盖及未解析 predicate 会保留 partial/gaps；空结果不能在证据不足时证明未注册。

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
| `controllerClassPattern` | string | 否 | — | 最短 `1`；最长 `128`；正则 `^[A-Za-z0-9_.$/{}:*?+@! -]+$(?![\s\S])` |
| `contextId` | string | 否 | — | 最短 `1`；最长 `256`；正则 `^[^\u0000-\u001f\u007f]+$(?![\s\S])` |

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
            "controllerClassPattern"
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
  "pathPattern": "/orders/{id}",
  "httpMethod": "GET"
}
```

```json
{
  "controllerClassPattern": "example.*Controller"
}
```

## data 字段

以下为非空 data 的字段结构；失败时 data 为 null。表中必填允许同时具有 null 类型，不能将 null 补成确定事实。

### `data`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `items` | array<object> | 是 | — | 最多项 `50` |

此对象不接受未列出的字段。

### `data.items[]`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `id` | string | 是 | — | 最长 `96` |
| `endpointId` | "mappings" | 是 | — | — |
| `observationId` | string | 是 | — | 最长 `96` |
| `contextId` | string / null | 是 | — | 最长 `256`；— |
| `parentContextId` | string / null | 是 | — | 最长 `256`；— |
| `stack` | "mvc" / "webflux" | 是 | — | — |
| `dispatcherName` | string / null | 是 | — | 最长 `256`；— |
| `paths` | array<string> | 是 | — | 最多项 `16` |
| `httpMethods` | array<"GET" / "HEAD" / "POST" / "PUT" / "PATCH" / "DELETE" / "OPTIONS" / "TRACE" / "CONNECT"> | 是 | — | 最多项 `9` |
| `methodsUnrestricted` | boolean | 是 | — | — |
| `controllerClass` | string / null | 是 | — | 最长 `256`；— |
| `handlerMethod` | string / null | 是 | — | 最长 `256`；— |
| `descriptor` | string / null | 是 | — | 最长 `1024`；— |
| `handlerKind` | "method" / "function" / "resource" / "unknown" | 是 | — | — |
| `conditions` | array<object> | 是 | — | 最多项 `16` |
| `matchingComplete` | boolean | 是 | — | — |

此对象不接受未列出的字段。

### `data.items[].conditions[]`

| 字段 | 类型或枚举 | 必填 | 默认值 | 约束 |
| --- | --- | --- | --- | --- |
| `kind` | "header" / "param" / "consumes" / "produces" | 是 | — | — |
| `name` | string / null | 是 | — | 最长 `128`；— |
| `value` | string / null | 是 | — | 最长 `256`；— |
| `negated` | boolean | 是 | — | — |

此对象不接受未列出的字段。

## 结果解读

按 totalMatched、truncated、coverage.gaps 和 nextAction 共同解读；totalMatched=null 表示完整匹配数未知。续页使用原查询和 nextCursor，快照默认 60 秒绝对 TTL。错误配方及各类预算见[调用策略](../tool-calling-policy.md)。
