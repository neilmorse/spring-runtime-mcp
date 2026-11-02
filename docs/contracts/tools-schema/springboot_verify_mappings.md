# springboot_verify_mappings - Route registration

Return normalized MVC/WebFlux routes, handlers, and method descriptors. Use for missing path/method/Controller registrations. Never request business URLs or equate a registration match with guaranteed request success.

Fields follow the [tool Schema](../../../src/spring_runtime_mcp/schemas/tools-contract.json); shared results are described in the [common envelope](common-envelope.md).

## Calling rules

Require pathPattern, httpMethod, or controllerClassPattern. Read mappings only, without business-path calls. Non-DispatcherServlet coverage and unparsed predicates preserve partial/gaps; empty results cannot establish nonregistration without sufficient evidence.

Patterns are bounded, case-sensitive globs with `*` and `?` as the only wildcards. Combine filters with AND. Additional arguments are rejected; invalid arguments do not read the target.

## Input fields

### `arguments`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `targetId` | string | No | "local" | minLength `1`; maxLength `64`; pattern `^[A-Za-z0-9_-]+$(?![\s\S])` |
| `maxResults` | integer | No | 50 | minimum `1`; maximum `50` |
| `cursor` | string | No | — | minLength `1`; maxLength `2048` |
| `pathPattern` | string | No | — | minLength `1`; maxLength `128`; pattern `^[A-Za-z0-9_.$/{}:*?+@! -]+$(?![\s\S])` |
| `httpMethod` | "GET" / "HEAD" / "POST" / "PUT" / "PATCH" / "DELETE" / "OPTIONS" / "TRACE" / "CONNECT" | No | — | — |
| `controllerClassPattern` | string | No | — | minLength `1`; maxLength `128`; pattern `^[A-Za-z0-9_.$/{}:*?+@! -]+$(?![\s\S])` |
| `contextId` | string | No | — | minLength `1`; maxLength `256`; pattern `^[^\u0000-\u001f\u007f]+$(?![\s\S])` |

This object rejects additional fields.

### Selector constraints

The Schema defines these combined selector constraints:

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

## Query examples

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

## Data fields

The following fields describe nonnull data; failures return data=null. Required fields can still allow null. Never replace null with an invented definite fact.

### `data`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `items` | array<object> | Yes | — | maxItems `50` |

This object rejects additional fields.

### `data.items[]`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `id` | string | Yes | — | maxLength `96` |
| `endpointId` | "mappings" | Yes | — | — |
| `observationId` | string | Yes | — | maxLength `96` |
| `contextId` | string / null | Yes | — | maxLength `256`; — |
| `parentContextId` | string / null | Yes | — | maxLength `256`; — |
| `stack` | "mvc" / "webflux" | Yes | — | — |
| `dispatcherName` | string / null | Yes | — | maxLength `256`; — |
| `paths` | array<string> | Yes | — | maxItems `16` |
| `httpMethods` | array<"GET" / "HEAD" / "POST" / "PUT" / "PATCH" / "DELETE" / "OPTIONS" / "TRACE" / "CONNECT"> | Yes | — | maxItems `9` |
| `methodsUnrestricted` | boolean | Yes | — | — |
| `controllerClass` | string / null | Yes | — | maxLength `256`; — |
| `handlerMethod` | string / null | Yes | — | maxLength `256`; — |
| `descriptor` | string / null | Yes | — | maxLength `1024`; — |
| `handlerKind` | "method" / "function" / "resource" / "unknown" | Yes | — | — |
| `conditions` | array<object> | Yes | — | maxItems `16` |
| `matchingComplete` | boolean | Yes | — | — |

This object rejects additional fields.

### `data.items[].conditions[]`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `kind` | "header" / "param" / "consumes" / "produces" | Yes | — | — |
| `name` | string / null | Yes | — | maxLength `128`; — |
| `value` | string / null | Yes | — | maxLength `256`; — |
| `negated` | boolean | Yes | — | — |

This object rejects additional fields.

## Interpreting results

Interpret totalMatched, truncated, coverage.gaps, and nextAction together; totalMatched=null means the complete matching count is unknown. Continue using the original query and nextCursor; snapshots default to a 60-second absolute TTL. See [calling policy](../tool-calling-policy.md) for error recipes and budgets.
