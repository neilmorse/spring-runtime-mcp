# Common envelope

Each of the eight domain results is provided as structuredContent and an equivalent compact JSON text copy. The complete JSON-RPC tool response is capped at 16,384 UTF-8 bytes. The [tool Schema](../../../src/spring_runtime_mcp/schemas/tools-contract.json) defines the fields.

## Status and evidence

schemaVersion is the string constant "2". ok/partial are valid diagnoses (isError=false); health DOWN, failed migrations, or drift facts are not tool-call errors. Failure envelopes have null data, totalMatched, and nextCursor, nonempty errors, and coverage.state=unavailable.

failed() maps INVALID_ARGUMENT to invalid, ENDPOINT_UNAUTHORIZED/TARGET_NOT_REGISTERED to denied, and other failures to unavailable. The Schema permits too_large, but that does not mean every current budget error returns that status.

Preserve null/unknown/partial when evidence is insufficient. Depth, association, or analysis budgets can also cause truncated, so continuation records are not guaranteed. redactions identifies safe output fields/indices, not a fixed redaction-type enum. Time fields use restricted RFC3339 validation; see [implementation conventions](../../architecture/implementation-conventions.md).

## Envelope fields

### `envelope`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `schemaVersion` | "2" | Yes | — | — |
| `status` | "ok" / "partial" / "denied" / "unavailable" / "invalid" / "too_large" | Yes | — | — |
| `source` | object | Yes | — | — |
| `totalMatched` | integer / null | Yes | — | minimum `0`; — |
| `truncated` | boolean | Yes | — | — |
| `truncationReasons` | array<string> | Yes | — | maxItems `8` |
| `coverage` | object | Yes | — | — |
| `warnings` | array<object> | Yes | — | maxItems `10` |
| `redactions` | array<string> | Yes | — | maxItems `50` |
| `nextCursor` | string / null | Yes | — | maxLength `2048`; — |
| `nextAction` | object | Yes | — | — |
| `errors` | array<DiagnosticError> | Yes | — | maxItems `8` |

This object rejects additional fields.

### `envelope.source`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `targetId` | string | Yes | — | maxLength `64` |
| `snapshotId` | string / null | Yes | — | maxLength `96`; — |
| `observedAt` | string | Yes | — | format `date-time` |
| `endpointIds` | array<"startup" / "flyway" / "liquibase" / "beans" / "conditions" / "mappings" / "health" / "health-liveness" / "health-readiness" / "env" / "configprops" / "env-property" / "info" / "openapi"> | Yes | — | maxItems `14`; unique items |
| `bootVersion` | string / null | Yes | — | maxLength `64`; — |
| `adapterVersion` | string | Yes | — | maxLength `32` |
| `policyVersion` | string | Yes | — | maxLength `32` |

This object rejects additional fields.

### `envelope.coverage`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `state` | "complete" / "partial" / "unavailable" | Yes | — | — |
| `scope` | string | Yes | — | maxLength `256` |
| `gaps` | array<string> | Yes | — | maxItems `10` |

This object rejects additional fields.

### `envelope.warnings[]`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `code` | string | Yes | — | maxLength `64` |
| `recordId` | string / null | Yes | — | maxLength `96`; — |

This object rejects additional fields.

### `envelope.nextAction`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `kind` | "done" / "refine" / "page" / "remediate" | Yes | — | — |
| `reasonCode` | string | Yes | — | maxLength `64`; pattern `^[A-Z][A-Z0-9_]*$(?![\s\S])` |
| `filterSuggestions` | array<object> | Yes | — | maxItems `4` |

This object rejects additional fields.

### `envelope.nextAction.filterSuggestions[]`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `parameter` | string | Yes | — | maxLength `64` |
| `value` | ['string', 'number', 'boolean', 'null'] / array<string> | Yes | — | maxLength `512`; maxItems `10` |

This object rejects additional fields.

data is a tool-specific object or null; see the corresponding tool reference. The source.endpointIds Schema enum includes reserved identities and does not establish support for dynamic env-property or info requests. See [security architecture](../../architecture/security-and-sanitization.md) for actual fixed endpoints.

### `DiagnosticError`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `code` | string | Yes | — | maxLength `64`; pattern `^[A-Z][A-Z0-9_]*$(?![\s\S])` |
| `endpointId` | "startup" / "flyway" / "liquibase" / "beans" / "conditions" / "mappings" / "health" / "health-liveness" / "health-readiness" / "env" / "configprops" / "env-property" / "info" / "openapi" / null | Yes | — | —; — |
| `httpStatus` | integer / null | Yes | — | minimum `100`; maximum `599`; — |
| `retryable` | boolean | Yes | — | — |
| `message` | string | Yes | — | maxLength `256` |
| `remediation` | object | Yes | — | — |

This object rejects additional fields.

### `DiagnosticError.remediation`

| Field | Type or enum | Required | Default | Constraints |
| --- | --- | --- | --- | --- |
| `recipeId` | string | Yes | — | maxLength `96` |
| `action` | "refineQuery" / "configureCapability" / "reviewExposure" / "reviewAuthorization" / "configureStartup" / "reviewTarget" / "reviewSource" / "stop" | Yes | — | — |
| `configKeys` | array<string> | Yes | — | maxItems `8` |
| `steps` | array<string> | Yes | — | maxItems `4` |
| `requiresApproval` | boolean | Yes | — | — |
| `retryAfterMs` | integer / null | Yes | — | minimum `0`; maximum `5000`; — |

This object rejects additional fields.

## Pagination and errors

Omit cursor on the first query. Continue with the original tool and normalized arguments, adding only the returned nextCursor. Cursors are opaque: do not decode or construct them. Default snapshot TTL is 60 seconds with a 32 MiB total budget; continuation does not extend TTL. Expiry or process restart requires a new query.

Record, byte, association, and depth budgets constrain output separately. Generic pagination reduces records; Bean tools can also trim associations. If safe output still cannot fit, return a fixed error. There is no universal guarantee of automatic halving or retaining at least one item.

Local templates generate error messages and recipes without echoing upstream suggestions. retryable is currently false and retryAfterMs null. INVALID_ARGUMENT recipes use requiresApproval=false; others use true, subject to existing same-scope authorization. See [calling policy](../tool-calling-policy.md) for code/status/recipe mappings.
