# springboot_verify_mappings - Route registration

Return normalized MVC/WebFlux handlers or Spring Cloud Gateway forwarding routes. All queries read fixed Actuator metadata. A reported route is evidence of registration and does not establish the result of a business request.

Fields follow the [tool Schema](../../../src/spring_runtime_mcp/schemas/tools-contract.json); shared results are described in the [common envelope](common-envelope.md).

## Calling rules

Application mode requires pathPattern, httpMethod, or controllerClassPattern. It reads `/actuator/mappings`. Non-DispatcherServlet coverage and unparsed predicates preserve partial evidence.

Gateway mode requires the operator to start the CLI with `--enable-gateway-routes` and register the Gateway origin. The target needs the read-only Gateway Actuator endpoint. The tool reads `GET /actuator/gateway/routes` and can filter declared paths locally.

Patterns are bounded, case-sensitive globs with `*` and `?` as the only wildcards. Combine filters with AND. Additional arguments are rejected; invalid arguments do not read the target.

## Input fields

### `arguments`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `targetId` | string | No | "local" | minLength `1`; maxLength `64`; pattern `^[A-Za-z0-9_-]+$(?![\s\S])` |
| `maxResults` | integer | No | 50 | minimum `1`; maximum `50` |
| `cursor` | string | No | — | minLength `1`; maxLength `2048` |
| `routeSource` | "application" / "gateway" | No | "application" | Gateway mode allows pathPattern as its optional selector |
| `pathPattern` | string | No | — | minLength `1`; maxLength `128`; pattern `^[A-Za-z0-9_.$/{}:*?+@! -]+$(?![\s\S])` |
| `httpMethod` | "GET" / "HEAD" / "POST" / "PUT" / "PATCH" / "DELETE" / "OPTIONS" / "TRACE" / "CONNECT" | No | — | — |
| `controllerClassPattern` | string | No | — | minLength `1`; maxLength `128`; pattern `^[A-Za-z0-9_.$/{}:*?+@! -]+$(?![\s\S])` |
| `contextId` | string | No | — | minLength `1`; maxLength `256`; pattern `^[^\u0000-\u001f\u007f]+$(?![\s\S])` |

This object rejects additional fields.

### Selector constraints

Gateway mode rejects httpMethod, controllerClassPattern, and contextId. Its continuation must keep routeSource and the same selectors.

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

```json
{
  "targetId": "tdd_gateway",
  "routeSource": "gateway",
  "pathPattern": "/api/catalog/*"
}
```

## Data fields

The following fields describe nonnull data; failures return data=null. Required fields can still allow null. Never replace null with an invented definite fact.

### `data`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `items` | array<object> | Yes | — | maxItems `50` |

This object rejects additional fields.

### Application mode items

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

### Gateway mode items

| Field | Type | Meaning |
| --- | --- | --- |
| `id`, `observationId` | string | Record and observation identifiers |
| `endpointId` | "gateway-routes" | Gateway route collection |
| `routeId` | string | Reported route identifier |
| `paths` | array<string> / null | Up to 16 recognized path patterns from a standalone Path predicate |
| `matchTrailingSlash` | boolean / null | Reported Path predicate setting |
| `order` | integer / null | Reported signed 32-bit route order |
| `targetService` | string / null | Service name from a plain `lb://service` destination |

Rows retain the inventory's reported order. Unknown path predicates, destinations, row IDs, or orders produce coverage gaps. A path filter returns confirmed matches and leaves the total unknown if unparsed predicates could qualify. The tool projects at most 2,000 upstream rows before the standard pagination and response budgets. An upstream inventory beyond that limit remains truncated even on the last captured page.

## Interpreting results

Interpret totalMatched, truncated, coverage.gaps, and nextAction together; totalMatched=null means the complete matching count is unknown. Continue using the original query and nextCursor; snapshots default to a 60-second absolute TTL. See [calling policy](../tool-calling-policy.md) for error recipes and budgets.
