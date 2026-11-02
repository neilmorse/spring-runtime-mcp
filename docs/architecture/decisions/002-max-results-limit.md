# ADR 002: maxResults default and maximum of 50

**Status**: implemented

## Constraint

All eight tools use **50** as the default and maximum maxResults. Valid values are integers from 1 through 50; invalid values are rejected rather than silently clamped.

maxResults controls returned records. It does not limit how many upstream records the fixed Actuator endpoint returns, nor replace graph, depth, read, or output-byte budgets. Build the complete visible graph and associations before filtering and pagination.

## Result semantics

- totalMatched describes the complete filtered count when it can be established, not merely the current page length.
- Unknown counts remain null.
- The complete response-frame budget may allow fewer than maxResults records.
- Preserve truncated, truncationReasons, coverage, and nextAction when a budget limits results.
- Use nextCursor only when provided by the response. Truncation caused by depth or analysis limits does not necessarily have a continuation page.

Examples:

```json
{"beanNamePattern":"orderService","maxResults":1}
```

```json
{"packagePrefix":"example","maxResults":50}
```

For continuation, resend the same tool and normalized query arguments with the returned cursor. Follow nextAction and preserve the snapshot's scope.

## Operational effects

The shared limit keeps the public contract consistent and bounds per-page record count. It does not guarantee a particular byte size, graph-traversal count, target load, or number of pages. Use selective queries and interpret coverage before drawing conclusions.

## References

- [Tool contract](../../../src/spring_runtime_mcp/schemas/tools-contract.json)
- [Pagination support](../../../src/spring_runtime_mcp/tools/support.py)
- [ADR 001: snapshot limits](001-snapshot-ttl-and-budget.md)
- [ADR 003: response-frame limit](003-response-size-cap.md)
