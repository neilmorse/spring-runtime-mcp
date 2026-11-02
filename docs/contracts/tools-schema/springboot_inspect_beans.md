# springboot_inspect_beans - Bean wiring and conditions

Return matching Beans, aliases, and bidirectional dependency graphs. For missing Beans, automatically read authorized condition reports and expand nested/transitive blocking chains. Use for injection or conditional-wiring problems; insufficient evidence returns unknown without guessing an exact cause.

Fields follow the [tool Schema](../../../src/spring_runtime_mcp/schemas/tools-contract.json); shared results are described in the [common envelope](common-envelope.md).

## Calling rules

Require beanNamePattern, typePattern, or packagePrefix. Build the full visible graph before filtering/pagination; direction selects dependencies, dependents, or both. Condition attribution needs readable conditions and an exactly registered Source catalog. Catalog gaps do not establish Bean absence.

Patterns are bounded, case-sensitive globs with `*` and `?` as the only wildcards. Combine filters with AND. Additional arguments are rejected; invalid arguments do not read the target.

## Input fields

### `arguments`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `targetId` | string | No | "local" | minLength `1`; maxLength `64`; pattern `^[A-Za-z0-9_-]+$(?![\s\S])` |
| `maxResults` | integer | No | 50 | minimum `1`; maximum `50` |
| `cursor` | string | No | — | minLength `1`; maxLength `2048` |
| `beanNamePattern` | string | No | — | minLength `1`; maxLength `128`; pattern `^[A-Za-z0-9_.$/{}:*?+@! -]+$(?![\s\S])` |
| `typePattern` | string | No | — | minLength `1`; maxLength `128`; pattern `^[A-Za-z0-9_.$/{}:*?+@! -]+$(?![\s\S])` |
| `packagePrefix` | string | No | — | minLength `1`; maxLength `256`; pattern `^[^\u0000-\u001f\u007f]+$(?![\s\S])` |
| `contextId` | string | No | — | minLength `1`; maxLength `256`; pattern `^[^\u0000-\u001f\u007f]+$(?![\s\S])` |
| `direction` | "dependencies" / "dependents" / "both" | No | "both" | — |
| `maxDepth` | integer | No | 2 | minimum `0`; maximum `16` |
| `conditionDepth` | integer | No | 4 | minimum `0`; maximum `16` |

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
            "beanNamePattern"
          ]
        },
        {
          "required": [
            "typePattern"
          ]
        },
        {
          "required": [
            "packagePrefix"
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
  "beanNamePattern": "orderService"
}
```

```json
{
  "typePattern": "example.*",
  "direction": "dependents",
  "maxDepth": 4
}
```

## Data fields

The following fields describe nonnull data; failures return data=null. Required fields can still allow null. Never replace null with an invented definite fact.

### `data`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `items` | array<object> | Yes | — | maxItems `50` |
| `missingBeanAnalysis` | object | Yes | — | — |

This object rejects additional fields.

### `data.items[]`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `id` | string | Yes | — | maxLength `96` |
| `endpointId` | "beans" | Yes | — | — |
| `observationId` | string | Yes | — | maxLength `96` |
| `contextId` | string / null | Yes | — | maxLength `256`; — |
| `parentContextId` | string / null | Yes | — | maxLength `256`; — |
| `name` | string | Yes | — | maxLength `256` |
| `type` | string / null | Yes | — | maxLength `256`; — |
| `scope` | string / null | Yes | — | maxLength `64`; — |
| `resource` | string / null | Yes | — | maxLength `256`; — |
| `aliases` | array<string> | Yes | — | maxItems `16` |
| `producer` | object / null | Yes | — | —; — |
| `dependencies` | array<object> | Yes | — | maxItems `16` |
| `dependents` | array<object> | Yes | — | maxItems `16` |

This object rejects additional fields.

### `data.items[].producer`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `kind` | "configuration" / "factoryMethod" / "factoryBean" | Yes | — | — |
| `configurationClass` | string / null | Yes | — | maxLength `256`; — |
| `methodName` | string / null | Yes | — | maxLength `256`; — |
| `evidenceLevel` | "observed" / "correlated" | Yes | — | — |

This object rejects additional fields.

### `data.items[].dependencies[]`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `fromId` | string | Yes | — | maxLength `96` |
| `toId` | string / null | Yes | — | maxLength `96`; — |
| `requestedName` | string / null | Yes | — | maxLength `256`; — |
| `targetContextId` | string / null | Yes | — | maxLength `256`; — |
| `targetName` | string / null | Yes | — | maxLength `256`; — |
| `resolution` | "resolved" / "ambiguous" / "unresolved" | Yes | — | — |
| `depth` | integer | Yes | — | minimum `0`; maximum `16` |

This object rejects additional fields.

### `data.items[].dependents[]`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `fromId` | string | Yes | — | maxLength `96` |
| `toId` | string / null | Yes | — | maxLength `96`; — |
| `requestedName` | string / null | Yes | — | maxLength `256`; — |
| `targetContextId` | string / null | Yes | — | maxLength `256`; — |
| `targetName` | string / null | Yes | — | maxLength `256`; — |
| `resolution` | "resolved" / "ambiguous" / "unresolved" | Yes | — | — |
| `depth` | integer | Yes | — | minimum `0`; maximum `16` |

This object rejects additional fields.

### `data.missingBeanAnalysis`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `state` | "notNeeded" / "explained" / "partial" / "unknown" | Yes | — | — |
| `conditions` | array<object> | Yes | — | maxItems `16` |
| `blockingPaths` | array<array<string>> | Yes | — | maxItems `8` |

This object rejects additional fields.

### `data.missingBeanAnalysis.conditions[]`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `id` | string | Yes | — | maxLength `96` |
| `configurationClass` | string / null | Yes | — | maxLength `256`; — |
| `conditionType` | string / null | Yes | — | maxLength `256`; — |
| `operator` | "leaf" / "any" / "all" / "none" / "unknown" | Yes | — | — |
| `outcome` | "matched" / "notMatched" / "unknown" | Yes | — | — |
| `reasonCode` | string | Yes | — | maxLength `64` |
| `childIds` | array<string> | Yes | — | maxItems `16` |
| `requiredBeanIds` | array<string> | Yes | — | maxItems `16` |
| `childrenComplete` | boolean | Yes | — | — |

This object rejects additional fields.

## Interpreting results

Interpret totalMatched, truncated, coverage.gaps, and nextAction together; totalMatched=null means the complete matching count is unknown. Continue using the original query and nextCursor; snapshots default to a 60-second absolute TTL. See [calling policy](../tool-calling-policy.md) for error recipes and budgets.
