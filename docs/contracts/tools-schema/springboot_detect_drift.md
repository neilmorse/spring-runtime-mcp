# springboot_detect_drift - Source/runtime drift

Compare Bean, route, migration-version, and profile expectations extracted by the caller from an authorized workspace. Return differences and graded cause candidates for source/runtime discrepancies. Omitted dimensions are not compared; file timestamps alone cannot prove a missing restart.

Fields follow the [tool Schema](../../../src/spring_runtime_mcp/schemas/tools-contract.json); shared results are described in the [common envelope](common-envelope.md).

## Calling rules

Compare explicit dimensions only. Omitted arrays mean no comparison; explicit empty arrays mean empty expectations. Extra objects require expectedScopeComplete=true and complete runtime evidence. Bean/route/migration-version expectations total at most 100 entities. Source revisions/timestamps are caller declarations; newer files alone cannot establish that a process was not restarted.

Patterns are bounded, case-sensitive globs with `*` and `?` as the only wildcards. Combine filters with AND. Additional arguments are rejected; invalid arguments do not read the target.

## Input fields

### `arguments`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `targetId` | string | No | "local" | minLength `1`; maxLength `64`; pattern `^[A-Za-z0-9_-]+$(?![\s\S])` |
| `maxResults` | integer | No | 50 | minimum `1`; maximum `50` |
| `cursor` | string | No | — | minLength `1`; maxLength `2048` |
| `expectedBeans` | array<object / object> | No | — | maxItems `100` |
| `expectedRoutes` | array<object> | No | — | maxItems `100` |
| `expectedMigrationVersion` | object | No | — | — |
| `expectedProfiles` | array<string> | No | — | maxItems `20`; unique items |
| `expectedScopeComplete` | boolean | No | false | — |
| `sourceRevision` | string | No | — | maxLength `128` |
| `sourceModifiedAt` | string | No | — | format `date-time` |
| `maxDepth` | integer | No | 2 | minimum `0`; maximum `16` |

This object rejects additional fields.

### `arguments.expectedBeans[]`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `name` | string | No | — | minLength `1`; maxLength `256`; pattern `^[^\u0000-\u001f\u007f]+$(?![\s\S])` |
| `type` | string | No | — | minLength `1`; maxLength `256`; pattern `^[^\u0000-\u001f\u007f]+$(?![\s\S])` |
| `contextId` | string | No | — | minLength `1`; maxLength `256`; pattern `^[^\u0000-\u001f\u007f]+$(?![\s\S])` |
| `aliases` | array<string> | No | — | maxItems `10` |

This object rejects additional fields.

### `arguments.expectedRoutes[]`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `path` | string | Yes | — | minLength `1`; maxLength `1024`; pattern `^/[^\u0000-\u001f\u007f?#]*$(?![\s\S])` |
| `httpMethod` | "GET" / "HEAD" / "POST" / "PUT" / "PATCH" / "DELETE" / "OPTIONS" / "TRACE" / "CONNECT" | Yes | — | — |
| `controllerClass` | string | No | — | minLength `1`; maxLength `256`; pattern `^[^\u0000-\u001f\u007f]+$(?![\s\S])` |
| `contextId` | string | No | — | minLength `1`; maxLength `256`; pattern `^[^\u0000-\u001f\u007f]+$(?![\s\S])` |

This object rejects additional fields.

### `arguments.expectedMigrationVersion`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `engine` | "flyway" / "liquibase" | Yes | — | — |
| `version` | string | Yes | — | minLength `1`; maxLength `256`; pattern `^[^\u0000-\u001f\u007f]+$(?![\s\S])` |
| `contextId` | string | No | — | minLength `1`; maxLength `256`; pattern `^[^\u0000-\u001f\u007f]+$(?![\s\S])` |
| `migrationBean` | string | No | — | minLength `1`; maxLength `256`; pattern `^[^\u0000-\u001f\u007f]+$(?![\s\S])` |

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
            "expectedBeans"
          ]
        },
        {
          "required": [
            "expectedRoutes"
          ]
        },
        {
          "required": [
            "expectedMigrationVersion"
          ]
        },
        {
          "required": [
            "expectedProfiles"
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
  "expectedBeans": [
    {
      "name": "orderService"
    }
  ],
  "expectedRoutes": [
    {
      "path": "/orders/{id}",
      "httpMethod": "GET"
    }
  ]
}
```

## Data fields

The following fields describe nonnull data; failures return data=null. Required fields can still allow null. Never replace null with an invented definite fact.

### `data`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `missingInRuntime` | array<object> | Yes | — | maxItems `50` |
| `unexpectedInRuntime` | array<object> | Yes | — | maxItems `50` |
| `profileMismatch` | object / null | Yes | — | —; — |
| `rootCauseInferences` | array<object> | Yes | — | maxItems `4` |

This object rejects additional fields.

### `data.missingInRuntime[]`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `id` | string | Yes | — | maxLength `96` |
| `dimension` | "beans" / "routes" / "migrations" | Yes | — | — |
| `identity` | string | Yes | — | maxLength `256` |
| `contextId` | string / null | Yes | — | maxLength `256`; — |
| `expected` | string / null | Yes | — | maxLength `256`; — |
| `actual` | string / null | Yes | — | maxLength `256`; — |
| `evidenceLevel` | "observed" / "inferred" / "unknown" | Yes | — | — |
| `affectedDependencyIds` | array<string> | Yes | — | maxItems `16` |

This object rejects additional fields.

### `data.unexpectedInRuntime[]`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `id` | string | Yes | — | maxLength `96` |
| `dimension` | "beans" / "routes" / "migrations" | Yes | — | — |
| `identity` | string | Yes | — | maxLength `256` |
| `contextId` | string / null | Yes | — | maxLength `256`; — |
| `expected` | string / null | Yes | — | maxLength `256`; — |
| `actual` | string / null | Yes | — | maxLength `256`; — |
| `evidenceLevel` | "observed" / "inferred" / "unknown" | Yes | — | — |
| `affectedDependencyIds` | array<string> | Yes | — | maxItems `16` |

This object rejects additional fields.

### `data.profileMismatch`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `expected` | array<string> | Yes | — | maxItems `20` |
| `actual` | array<string> / null | Yes | — | maxItems `20`; — |
| `state` | "match" / "mismatch" / "unknown" | Yes | — | — |

This object rejects additional fields.

### `data.rootCauseInferences[]`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `code` | "POSSIBLE_NOT_RESTARTED" / "PROFILE_MISMATCH" / "POSSIBLE_WRONG_INSTANCE" / "ENVIRONMENT_OVERRIDE" / "INSUFFICIENT_EVIDENCE" | Yes | — | — |
| `confidence` | "supported" / "candidate" / "unknown" | Yes | — | — |
| `evidenceIds` | array<string> | Yes | — | maxItems `8` |

This object rejects additional fields.

## Interpreting results

Interpret totalMatched, truncated, coverage.gaps, and nextAction together; totalMatched=null means the complete matching count is unknown. Continue using the original query and nextCursor; snapshots default to a 60-second absolute TTL. See [calling policy](../tool-calling-policy.md) for error recipes and budgets.
