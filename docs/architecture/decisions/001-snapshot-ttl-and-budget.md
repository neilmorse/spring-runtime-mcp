# ADR 001: Snapshot TTL and storage budget

**Status**: implemented

## Constraint

SnapshotStore uses a **60-second absolute TTL** and a **32 MiB total storage budget**, with LRU eviction. Snapshots contain sanitized shared encoded records; they are process-local and are lost on restart.

The TTL starts when a snapshot is created. Access and continuation pages do not extend it. Eviction can remove a snapshot before its TTL expires, so a cursor does not guarantee future availability.

## Pagination behavior

A continuation request keeps the original tool, target, and normalized query and adds the returned cursor. The cursor records an offset into the original snapshot; normal continuation decodes/projects the current page without rereading the target.

If the cursor expires or the process restarts, start a new query without cursor. New results are a new observation, not continuation of the old snapshot. CURSOR_QUERY_MISMATCH requires restoring the original arguments or starting a new query.

Policy-stamp changes trigger safety revalidation of the complete snapshot. Unsafe cached content causes associated handles to be removed. Policy stamps do not store plaintext credentials.

## Operational effects

- Reusing a snapshot avoids repeated target reads during ordinary pagination.
- Expiration and LRU eviction bound retention, but callers must handle expired cursors.
- Large queries share the total memory budget with other snapshots.
- Snapshot storage, upstream response limits, and the 16 KiB response-frame budget are independent constraints.

There is no measured success-rate guarantee for continuation intervals. Snapshot availability also depends on query size, other queries, policy changes, and process lifetime.

## References

- [Snapshot implementation](../../../src/spring_runtime_mcp/snapshots.py)
- [Calling policy](../../contracts/tool-calling-policy.md)
- [ADR 002: record limit](002-max-results-limit.md)
- [ADR 003: response-frame limit](003-response-size-cap.md)
