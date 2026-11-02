# springboot_search_openapi - OpenAPI queries

Return matching operations or Schemas, inlining direct and second-level in-document references by default. Use precise selectors to check API contracts. Do not invoke business APIs, return the full document, or resolve remote references.

Fields follow the [tool Schema](../../../src/spring_runtime_mcp/schemas/tools-contract.json); shared results are described in the [common envelope](common-envelope.md).

## Calling rules

schemaName is exclusive with operation queries. Operations require pathPattern or operationId; httpMethod cannot stand alone. Fixed GET /actuator/openapi invokes no API and fetches no remote references. maxRefDepth defaults to 2 and is capped at 8; free-text descriptions are not emitted.

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
| `operationId` | string | No | — | minLength `1`; maxLength `256`; pattern `^[^\u0000-\u001f\u007f]+$(?![\s\S])` |
| `schemaName` | string | No | — | minLength `1`; maxLength `256`; pattern `^[^\u0000-\u001f\u007f]+$(?![\s\S])` |
| `maxRefDepth` | integer | No | 2 | minimum `0`; maximum `8` |

This object rejects additional fields.

### Selector constraints

The Schema defines these combined selector constraints:

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

## Query examples

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

## Data fields

The following fields describe nonnull data; failures return data=null. Required fields can still allow null. Never replace null with an invented definite fact.

### `data`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `openapiVersion` | string / null | Yes | — | maxLength `32`; — |
| `candidateId` | string / null | Yes | — | maxLength `64`; — |
| `items` | array<object> | Yes | — | maxItems `50` |

This object rejects additional fields.

### `data.items[]`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `id` | string | Yes | — | maxLength `96` |
| `endpointId` | "openapi" | Yes | — | — |
| `observationId` | string | Yes | — | maxLength `96` |
| `kind` | "operation" / "schema" | Yes | — | — |
| `path` | string / null | Yes | — | minLength `1`; maxLength `1024`; pattern `^/[^\u0000-\u001f\u007f?#]*$(?![\s\S])`; — |
| `httpMethod` | "GET" / "HEAD" / "POST" / "PUT" / "PATCH" / "DELETE" / "OPTIONS" / "TRACE" / "CONNECT" / null | Yes | — | —; — |
| `operationId` | string / null | Yes | — | maxLength `256`; — |
| `schemaName` | string / null | Yes | — | maxLength `256`; — |
| `parameters` | array<object> | Yes | — | maxItems `16` |
| `requestBody` | array<object> | Yes | — | maxItems `8` |
| `responses` | array<object> | Yes | — | maxItems `16` |
| `schema` | Schema / null | Yes | — | —; — |
| `expansionComplete` | boolean | Yes | — | — |

This object rejects additional fields.

### `data.items[].parameters[]`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `name` | string | Yes | — | maxLength `128` |
| `in` | "path" / "query" / "header" / "cookie" | Yes | — | — |
| `required` | boolean | Yes | — | — |
| `schema` | Schema | Yes | — | — |

This object rejects additional fields.

### `data.items[].requestBody[]`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `mediaType` | string | Yes | — | maxLength `128` |
| `schema` | Schema | Yes | — | — |

This object rejects additional fields.

### `data.items[].responses[]`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `status` | string | Yes | — | maxLength `16` |
| `mediaType` | string / null | Yes | — | maxLength `128`; — |
| `schema` | Schema / null | Yes | — | —; — |

This object rejects additional fields.

### `$defs.Schema`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `type` | "null" / "boolean" / "object" / "array" / "number" / "string" / "integer" / array<"null" / "boolean" / "object" / "array" / "number" / "string" / "integer"> | No | — | —; maxItems `7` |
| `format` | string | No | — | maxLength `64` |
| `nullable` | boolean | No | — | — |
| `readOnly` | boolean | No | — | — |
| `writeOnly` | boolean | No | — | — |
| `minimum` | number | No | — | — |
| `maximum` | number | No | — | — |
| `exclusiveMinimum` | ['number', 'boolean'] | No | — | — |
| `exclusiveMaximum` | ['number', 'boolean'] | No | — | — |
| `multipleOf` | number | No | — | — |
| `minLength` | integer | No | — | minimum `0` |
| `maxLength` | integer | No | — | minimum `0` |
| `pattern` | string | No | — | maxLength `512` |
| `minItems` | integer | No | — | minimum `0` |
| `maxItems` | integer | No | — | minimum `0` |
| `uniqueItems` | boolean | No | — | — |
| `required` | array<string> | No | — | maxItems `50` |
| `properties` | object | No | — | — |
| `items` | Schema | No | — | — |
| `additionalProperties` | boolean / Schema | No | — | —; — |
| `allOf` | array<Schema> | No | — | maxItems `16` |
| `oneOf` | array<Schema> | No | — | maxItems `16` |
| `anyOf` | array<Schema> | No | — | maxItems `16` |
| `$ref` | string | No | — | maxLength `512`; pattern `^#(?:/.*)?$(?![\s\S])` |
| `referenceState` | "resolved" / "cycle" / "depthLimit" / "invalid" / "externalBlocked" / "unsupported" | No | — | — |
| `omissionCodes` | array<string> | No | — | maxItems `8` |
| `enum` | array<['string', 'number', 'boolean', 'null']> | No | — | maxItems `16` |

This object rejects additional fields.

## Interpreting results

Interpret totalMatched, truncated, coverage.gaps, and nextAction together; totalMatched=null means the complete matching count is unknown. Continue using the original query and nextCursor; snapshots default to a 60-second absolute TTL. See [calling policy](../tool-calling-policy.md) for error recipes and budgets.
