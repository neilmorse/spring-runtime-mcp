# ADR 003: Complete tool responses capped at 16 KiB

**Status**: implemented

## Constraint

The complete JSON-RPC tool response is capped at **16,384 UTF-8 bytes**. This includes the request id, JSON-RPC fields, SDK metadata, structuredContent, and the equivalent compact JSON TextContent copy. It is not a budget for structuredContent alone or a fixed token allowance.

Static tools/list Schemas are not trimmed to this tool-result limit. Upstream HTTP responses have separate limits: 32 KiB headers and 8 MiB bodies, including bounded decompression.

## Enforcement

Pagination measures sanitized output using the complete frame. Generic pagination reduces record count on RESPONSE_TOO_LARGE; other safety errors propagate. The Bean tool has separate pagination and can trim associations or condition analysis, recording gaps such as RESPONSE_BUDGET.

If a safe result still cannot fit, return a fixed error. There is no universal guarantee of retaining one record or of every tool using the same halving algorithm.

The host validates the output Schema and independently checks the result. The actual SDK send layer checks the serialized frame again. Text and structured copies must represent the same sanitized object; safety failures never fall back to original upstream text.

## Operational effects

- Responses have a fixed wire-size bound despite the two-copy format.
- Long strings, nested associations, request ids, and metadata affect how many records fit.
- maxResults=50 does not guarantee 50 records fit.
- Depth and byte truncation must remain visible through coverage, truncated, and nextAction.
- Byte size does not imply a fixed token count or measured serialization latency.

Use precise selectors, the tool's supported depth controls, and continuation instructions. Do not interpret omitted records or trimmed relationships as absent runtime objects.

## References

- [Frame serialization](../../../src/spring_runtime_mcp/transport/responses.py)
- [Pagination support](../../../src/spring_runtime_mcp/tools/support.py)
- [Host validation](../../../src/spring_runtime_mcp/server.py)
- [Common envelope](../../contracts/tools-schema/common-envelope.md)
- [ADR 001: snapshot limits](001-snapshot-ttl-and-budget.md)
- [ADR 002: record limit](002-max-results-limit.md)
