# springboot_check_migrations - Migration audit

Return reported migrations, checksums, ordering, and anomalous states across Contexts and migration Beans. Use for failures or version differences. Unreported pending state requires trusted expectations; the tool executes no SQL or migrations.

Fields follow the [tool Schema](../../../src/spring_runtime_mcp/schemas/tools-contract.json); shared results are described in the [common envelope](common-envelope.md).

## Calling rules

engine=auto reads both engines separately. Express pending only from reported inventory or a complete trusted baseline; never execute migrations. expectedSetComplete permits PENDING inference for expected records absent from a completely read engine; it does not add a separate migration detector. Liquibase lacks Flyway's standard version semantics.

Patterns are bounded, case-sensitive globs with `*` and `?` as the only wildcards. Combine filters with AND. Additional arguments are rejected; invalid arguments do not read the target.

## Input fields

### `arguments`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `targetId` | string | No | "local" | minLength `1`; maxLength `64`; pattern `^[A-Za-z0-9_-]+$(?![\s\S])` |
| `maxResults` | integer | No | 50 | minimum `1`; maximum `50` |
| `cursor` | string | No | — | minLength `1`; maxLength `2048` |
| `engine` | "auto" / "flyway" / "liquibase" | No | "auto" | — |
| `contextId` | string | No | — | minLength `1`; maxLength `256`; pattern `^[^\u0000-\u001f\u007f]+$(?![\s\S])` |
| `migrationBean` | string | No | — | minLength `1`; maxLength `256`; pattern `^[^\u0000-\u001f\u007f]+$(?![\s\S])` |
| `state` | array<"APPLIED" / "PENDING" / "FAILED" / "OUT_OF_ORDER" / "MISSING_FAILED" / "UNKNOWN"> | No | — | maxItems `6`; unique items |
| `version` | string | No | — | maxLength `128` |
| `expectedMigrations` | array<object> | No | — | maxItems `100` |
| `expectedSetComplete` | boolean | No | false | — |

This object rejects additional fields.

### `arguments.expectedMigrations[]`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `engine` | "flyway" / "liquibase" | Yes | — | — |
| `contextId` | string | Yes | — | minLength `1`; maxLength `256`; pattern `^[^\u0000-\u001f\u007f]+$(?![\s\S])` |
| `migrationBean` | string | Yes | — | minLength `1`; maxLength `256`; pattern `^[^\u0000-\u001f\u007f]+$(?![\s\S])` |
| `identity` | string | Yes | — | minLength `1`; maxLength `256`; pattern `^[^\u0000-\u001f\u007f]+$(?![\s\S])` |
| `version` | string / null | No | — | maxLength `128`; — |
| `checksum` | string / null | No | — | maxLength `128`; — |

This object rejects additional fields.

## Query examples

```json
{
  "engine": "flyway"
}
```

```json
{
  "state": [
    "FAILED",
    "MISSING_FAILED"
  ]
}
```

## Data fields

The following fields describe nonnull data; failures return data=null. Required fields can still allow null. Never replace null with an invented definite fact.

### `data`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `pendingVisibility` | "reported" / "baselineInferred" / "unknown" | Yes | — | — |
| `items` | array<object> | Yes | — | maxItems `50` |

This object rejects additional fields.

### `data.items[]`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `id` | string | Yes | — | maxLength `96` |
| `endpointId` | "flyway" / "liquibase" | Yes | — | — |
| `observationId` | string | Yes | — | maxLength `96` |
| `contextId` | string / null | Yes | — | maxLength `256`; — |
| `parentContextId` | string / null | Yes | — | maxLength `256`; — |
| `engine` | "flyway" / "liquibase" | Yes | — | — |
| `migrationBean` | string | Yes | — | maxLength `256` |
| `identity` | string | Yes | — | maxLength `256` |
| `script` | string / null | Yes | — | maxLength `256`; — |
| `changeLog` | string / null | Yes | — | maxLength `256`; — |
| `changeSetId` | string / null | Yes | — | maxLength `256`; — |
| `author` | string / null | Yes | — | maxLength `256`; — |
| `version` | string / null | Yes | — | maxLength `128`; — |
| `description` | string / null | Yes | — | maxLength `256`; — |
| `checksum` | string / null | Yes | — | maxLength `128`; — |
| `checksumType` | "number" / "string" / "absent" | Yes | — | — |
| `checksumAlgorithm` | string / null | Yes | — | maxLength `64`; — |
| `executionTimeMs` | number / null | Yes | — | minimum `0`; — |
| `orderExecuted` | integer / null | Yes | — | minimum `0`; — |
| `executedAt` | string / null | Yes | — | maxLength `64`; — |
| `rawState` | string / null | Yes | — | maxLength `64`; — |
| `state` | "APPLIED" / "PENDING" / "FAILED" / "OUT_OF_ORDER" / "MISSING_FAILED" / "UNKNOWN" | Yes | — | — |
| `stateEvidence` | "reported" / "baselineInferred" / "unknown" | Yes | — | — |
| `attentionRequired` | boolean | Yes | — | — |

This object rejects additional fields.

## Interpreting results

Interpret totalMatched, truncated, coverage.gaps, and nextAction together; totalMatched=null means the complete matching count is unknown. Continue using the original query and nextCursor; snapshots default to a 60-second absolute TTL. See [calling policy](../tool-calling-policy.md) for error recipes and budgets.
