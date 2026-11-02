# springboot_analyze_startup - Startup bottlenecks

Return reported version, timeline span, slowest steps, and parent chains from a nondestructive startup snapshot. Use for slow startup, not current request latency; never POST to drain the buffer.

Fields follow the [tool Schema](../../../src/spring_runtime_mcp/schemas/tools-contract.json); shared results are described in the [common envelope](common-envelope.md).

## Calling rules

Read fixed GET startup snapshots. Timeline span is not complete JVM startup time; do not sum overlapping steps. Preserve gaps for missing unit, parent, or timing evidence.

Patterns are bounded, case-sensitive globs with `*` and `?` as the only wildcards. Combine filters with AND. Additional arguments are rejected; invalid arguments do not read the target.

## Input fields

### `arguments`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `targetId` | string | No | "local" | minLength `1`; maxLength `64`; pattern `^[A-Za-z0-9_-]+$(?![\s\S])` |
| `maxResults` | integer | No | 50 | minimum `1`; maximum `50` |
| `cursor` | string | No | — | minLength `1`; maxLength `2048` |
| `stepNamePattern` | string | No | — | minLength `1`; maxLength `128`; pattern `^[A-Za-z0-9_.$/{}:*?+@! -]+$(?![\s\S])` |
| `beanNamePattern` | string | No | — | minLength `1`; maxLength `128`; pattern `^[A-Za-z0-9_.$/{}:*?+@! -]+$(?![\s\S])` |
| `minDurationMs` | number | No | 0 | minimum `0` |
| `maxDepth` | integer | No | 4 | minimum `0`; maximum `16` |

This object rejects additional fields.

## Query examples

```json
{
  "minDurationMs": 100,
  "maxResults": 10
}
```

```json
{
  "stepNamePattern": "spring.beans.*",
  "maxDepth": 8
}
```

## Data fields

The following fields describe nonnull data; failures return data=null. Required fields can still allow null. Never replace null with an invented definite fact.

### `data`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `springBootVersion` | string / null | Yes | — | maxLength `64`; — |
| `totalDurationMs` | number / null | Yes | — | minimum `0`; — |
| `durationBasis` | "timelineSpan" / "unknown" | Yes | — | — |
| `timelineComplete` | boolean | Yes | — | — |
| `items` | array<object> | Yes | — | maxItems `50` |

This object rejects additional fields.

### `data.items[]`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `id` | string | Yes | — | maxLength `96` |
| `endpointId` | "startup" | Yes | — | — |
| `observationId` | string | Yes | — | maxLength `96` |
| `stepId` | string | Yes | — | maxLength `20`; pattern `^[0-9]+$(?![\s\S])` |
| `parentStepId` | string / null | Yes | — | maxLength `20`; pattern `^[0-9]+$(?![\s\S])`; — |
| `name` | string | Yes | — | maxLength `256` |
| `startedAt` | string / null | Yes | — | format `date-time`; — |
| `durationNanos` | string / null | Yes | — | maxLength `30`; pattern `^[0-9]+$(?![\s\S])`; — |
| `durationMs` | number / null | Yes | — | minimum `0`; — |
| `tags` | array<object> | Yes | — | maxItems `10` |
| `ancestorIds` | array<string> | Yes | — | maxItems `16` |
| `relationState` | "resolved" / "orphan" / "cycle" / "duplicate" | Yes | — | — |
| `bottleneckCode` | "BEAN_INSTANTIATION" / "PACKAGE_SCAN" / "AUTO_CONFIGURATION" / "OTHER" / "UNKNOWN" | Yes | — | — |

This object rejects additional fields.

### `data.items[].tags[]`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `key` | string | Yes | — | maxLength `128` |
| `value` | string / null | Yes | — | maxLength `256`; — |

This object rejects additional fields.

## Interpreting results

Interpret totalMatched, truncated, coverage.gaps, and nextAction together; totalMatched=null means the complete matching count is unknown. Continue using the original query and nextCursor; snapshots default to a 60-second absolute TTL. See [calling policy](../tool-calling-policy.md) for error recipes and budgets.
