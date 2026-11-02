# springboot_inspect_config - Configuration sources

Return effective properties, binding Beans, source positions, and active profiles after mandatory two-layer sanitization. Query by prefix or key pattern for binding/override issues. The capability is disabled by default and cannot retrieve secrets or export complete configuration.

Fields follow the [tool Schema](../../../src/spring_runtime_mcp/schemas/tools-contract.json); shared results are described in the [common envelope](common-envelope.md).

## Calling rules

Require prefix or propertyKeyPattern. Diagnostics are disabled by default; intersect queries with CLI registration. includeValues=true also needs --config-allow-values, and values are always sanitized. The network still reads complete fixed env/configprops endpoints; local filters do not reduce upstream response size.

Patterns are bounded, case-sensitive globs with `*` and `?` as the only wildcards. Combine filters with AND. Additional arguments are rejected; invalid arguments do not read the target.

## Input fields

### `arguments`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `targetId` | string | No | "local" | minLength `1`; maxLength `64`; pattern `^[A-Za-z0-9_-]+$(?![\s\S])` |
| `maxResults` | integer | No | 50 | minimum `1`; maximum `50` |
| `cursor` | string | No | — | minLength `1`; maxLength `2048` |
| `prefix` | string | No | — | minLength `1`; maxLength `128`; pattern `^[A-Za-z_][A-Za-z0-9_.-]*$(?![\s\S])` |
| `propertyKeyPattern` | string | No | — | minLength `1`; maxLength `128`; pattern `^[A-Za-z0-9_.$/{}:*?+@! -]+$(?![\s\S])` |
| `contextId` | string | No | — | minLength `1`; maxLength `256`; pattern `^[^\u0000-\u001f\u007f]+$(?![\s\S])` |
| `includeValues` | boolean | No | false | — |

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

## Query examples

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

## Data fields

The following fields describe nonnull data; failures return data=null. Required fields can still allow null. Never replace null with an invented definite fact.

### `data`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `activeProfiles` | array<string> / null | Yes | — | maxItems `20`; — |
| `items` | array<object> | Yes | — | maxItems `50` |

This object rejects additional fields.

### `data.items[]`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `id` | string | Yes | — | maxLength `96` |
| `endpointId` | "env" / "configprops" / "env-property" | Yes | — | — |
| `observationId` | string | Yes | — | maxLength `96` |
| `contextId` | string / null | Yes | — | maxLength `256`; — |
| `parentContextId` | string / null | Yes | — | maxLength `256`; — |
| `propertyKey` | string | Yes | — | maxLength `256` |
| `prefix` | string / null | Yes | — | maxLength `256`; — |
| `configurationBean` | string / null | Yes | — | maxLength `256`; — |
| `effectiveValue` | ['string', 'number', 'boolean', 'null'] | Yes | — | maxLength `512` |
| `valueState` | "visible" / "redacted" / "notReported" | Yes | — | — |
| `bindingValue` | ['string', 'number', 'boolean', 'null'] | Yes | — | maxLength `512` |
| `bindingState` | "visible" / "redacted" / "notReported" | Yes | — | — |
| `origin` | object | Yes | — | — |
| `sourceKind` | "configurationFile" / "environmentVariable" / "systemProperty" / "commandLine" / "other" / "unknown" | Yes | — | — |
| `effective` | "yes" / "no" / "unknown" | Yes | — | — |

This object rejects additional fields.

### `data.items[].origin`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `kind` | "configurationFile" / "environmentVariable" / "systemProperty" / "commandLine" / "other" / "unknown" | Yes | — | — |
| `file` | string / null | Yes | — | maxLength `256`; — |
| `line` | integer / null | Yes | — | minimum `1`; — |
| `column` | integer / null | Yes | — | minimum `1`; — |
| `environmentVariable` | string / null | Yes | — | maxLength `128`; pattern `^[A-Za-z_][A-Za-z0-9_]*$(?![\s\S])`; — |

This object rejects additional fields.

## CLI registration example

Operators first register the authorized scope; repeat options for individual values. --config-profiles is a Boolean switch permitting active-profile reads.

```bash
spring-runtime-mcp --base-url http://127.0.0.1:18081 \
  --config-prefix app.feature --config-prefix spring.application \
  --config-property server.port --config-property server.ssl.enabled \
  --config-profiles --config-allow-values
```

The command starts a STDIO host. See the [first-query guide](../../first-query.md) for credential forwarding and an actual query.

## Interpreting results

Interpret totalMatched, truncated, coverage.gaps, and nextAction together; totalMatched=null means the complete matching count is unknown. Continue using the original query and nextCursor; snapshots default to a 60-second absolute TTL. See [calling policy](../tool-calling-policy.md) for error recipes and budgets.
