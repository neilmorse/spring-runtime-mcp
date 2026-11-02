# springboot_diagnose_health - Application and dependency health

Return overall health, anomalous component trees, sanitized structured errors, and remediation codes. Use for dependency failures or probe anomalies. Component drilldown is local; no logs, heap dumps, or raw exception stacks are fetched.

Fields follow the [tool Schema](../../../src/spring_runtime_mcp/schemas/tools-contract.json); shared results are described in the [common envelope](common-envelope.md).

## Calling rules

Healthy children (includeHealthy=false) and details (includeDetails=false) are excluded by default; anomalous components may still be returned. componentPath is a local tree-path array. Fixed liveness/readiness 503 responses can provide valid health evidence. Hidden details or unreadable components preserve partial/unknown.

Patterns are bounded, case-sensitive globs with `*` and `?` as the only wildcards. Combine filters with AND. Additional arguments are rejected; invalid arguments do not read the target.

## Input fields

### `arguments`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `targetId` | string | No | "local" | minLength `1`; maxLength `64`; pattern `^[A-Za-z0-9_-]+$(?![\s\S])` |
| `maxResults` | integer | No | 50 | minimum `1`; maximum `50` |
| `cursor` | string | No | — | minLength `1`; maxLength `2048` |
| `componentPath` | array<string> | No | — | maxItems `16` |
| `group` | "application" / "liveness" / "readiness" | No | "application" | — |
| `includeDetails` | boolean | No | false | — |
| `includeHealthy` | boolean | No | false | — |
| `maxDepth` | integer | No | 4 | minimum `0`; maximum `16` |

This object rejects additional fields.

## Query examples

```json
{}
```

```json
{
  "group": "readiness"
}
```

```json
{
  "componentPath": [
    "db"
  ],
  "includeDetails": true,
  "includeHealthy": true
}
```

## Data fields

The following fields describe nonnull data; failures return data=null. Required fields can still allow null. Never replace null with an invented definite fact.

### `data`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `overallStatus` | string / null | Yes | — | maxLength `64`; — |
| `activeGroup` | "application" / "liveness" / "readiness" | Yes | — | — |
| `items` | array<object> | Yes | — | maxItems `50` |

This object rejects additional fields.

### `data.items[]`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `id` | string | Yes | — | maxLength `96` |
| `endpointId` | "health" / "health-liveness" / "health-readiness" | Yes | — | — |
| `observationId` | string | Yes | — | maxLength `96` |
| `componentPath` | array<string> | Yes | — | maxItems `16` |
| `parentId` | string / null | Yes | — | maxLength `96`; — |
| `status` | string | Yes | — | maxLength `64` |
| `details` | array<object> | Yes | — | maxItems `10` |
| `errorType` | string / null | Yes | — | maxLength `256`; — |
| `remediationCodes` | array<string> | Yes | — | maxItems `4` |
| `childrenComplete` | boolean | Yes | — | — |

This object rejects additional fields.

### `data.items[].details[]`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `name` | string | Yes | — | maxLength `128` |
| `value` | ['string', 'number', 'boolean', 'null'] | Yes | — | maxLength `512` |

This object rejects additional fields.

## Interpreting results

Interpret totalMatched, truncated, coverage.gaps, and nextAction together; totalMatched=null means the complete matching count is unknown. Continue using the original query and nextCursor; snapshots default to a 60-second absolute TTL. See [calling policy](../tool-calling-policy.md) for error recipes and budgets.
