# Implementation conventions

Use this page to check actual interfaces and propagation paths before editing modules. [AGENTS.md](../../AGENTS.md) defines coding rules and protected core areas.

## Interfaces and data

Python uses snake_case and PascalCase; public JSON uses camelCase. All eight tool handlers are wrapped by `@tool_handler`, accept `arguments: Mapping[str, Any]` and `services: Services`, and asynchronously return domain envelopes.

Each adapter defines its own inputs and outputs; do not impose an assumed common signature:

| Adapter entry point | Inputs and result |
| --- | --- |
| `normalize_beans` | ParsedObservation and budget → BeanGraph |
| `normalize_conditions` | ParsedObservation and budget → ConditionReport |
| `normalize_config` | env, configprops, ConfigQuery, SanitizerPipeline, optional policy → profiles/items/gaps |
| `normalize_health` | body plus component, detail, health-filter, and depth arguments → overall/items/gaps |
| `normalize_mappings` | body plus route, method, controller, and Context arguments → items/gaps |
| `normalize_migrations` | flyway, liquibase, MigrationQuery → items/gaps/status |
| `normalize_openapi` | body、OpenApiQuery → version/candidate/items/gaps/blocked |
| `normalize_startup` | body plus name, duration, and depth arguments → six-element tuple unpacked by the tool |
| `load_source_catalog` | Parsed Mapping, target_id, and budget → SourceCatalog; the CLI reads the file. |

Fact states known/unknown/notReported/redacted carry distinct evidence meanings; known + null can indicate a root Context with no parent. Interpret None, empty collections, and Boolean results at each call site. Missing states for new public fields must follow the Schema.

## Errors and gaps

- NormalizationError extends ValueError; AnalysisLimit extends NormalizationError. Tool boundaries handle domain exceptions first, then convert designated parse errors, timeouts, and unexpected errors.
- Adapters may return gaps; the tool constructing the domain envelope calls `partial()`. Zero filter matches and invisible evidence remain distinct.
- `failed()` maps INVALID_ARGUMENT to invalid, ENDPOINT_UNAUTHORIZED/TARGET_NOT_REGISTERED to denied, and other codes to unavailable. All return `data=null`, `totalMatched=null`, unavailable coverage, and an errors array.
- ResponseGateReader converts transport failures to fixed EndpointReadError codes and re-raises TypeError/AssertionError. Protocol/tool catch-all boundaries produce fixed safe errors. Connector cleanup-and-re-raise paths preserve cancellation and failure semantics.
- CLI configuration errors go to stderr and exit 2; KeyboardInterrupt exits 130. Original exception text, stacks, and credentials never leave the boundary.

Error codes and recipes are implemented in [diagnostics.py](../../src/spring_runtime_mcp/diagnostics.py); caller semantics are in the [calling policy](../contracts/tool-calling-policy.md).

## Pagination and budgets

Generic `tools.support.finalize` sanitizes before pagination, measuring the JSON-RPC frame including both structured and text copies. Only RESPONSE_TOO_LARGE triggers record-count reduction; other safety errors propagate. The Bean tool paginates independently and may trim association arrays or condition analysis, recording gaps such as RESPONSE_BUDGET.

SnapshotStore retains shared immutable encoded records and cursor offsets. Continuation pages decode/project only the current page and advance by the actual consumed count. Cursors bind the tool and normalized query; policy-stamp changes trigger safety revalidation. TTL starts at snapshot creation and is not extended by reads or continuation pages.

| Limit | Current value and implementation |
| --- | --- |
| Total tool deadline | 15 seconds; `tools/support.py`, host callback |
| Concurrent reads per target | 2; `services.py` |
| Services read wait | At most 5 seconds and the remaining call deadline |
| Socket connection budget | 2 seconds shared by all candidate addresses, bounded by the read deadline |
| HTTP response headers | 32 KiB cumulative |
| HTTP response body | 8 MiB; limits apply separately before and after gzip decompression |
| Bounded JSON depth/nodes | 64 / 100,000 |
| Default AnalysisBudget visits/depth | 20,000 / 16 |
| Total CallBudget visits | 20,000 |
| maxResults default/maximum | 50 / 50 |
| Complete tool response frame | 16,384 UTF-8 bytes |
| STDIO input frame | 64 KiB |
| Source catalog file | 256 KiB |
| Snapshot TTL/storage budget | 60 seconds / 32 MiB |

`CALL_BUDGET` uses a ContextVar. The host establishes a scope; tool wrappers reuse or create a scope and reset it in finally. Graph visits, upstream reads, and output byte budgets are separate limits.

## Assembly and I/O

Production environment-variable reads are centralized in `cli.py`; maintenance scripts and tests manage their own execution environments. HTTP uses `http.client` in worker threads; the online protocol host uses the official SDK. Console-isolation helpers in `transport/stdio.py` support offline replay.

Without a registered SourceCatalog, Services uses an empty fact catalog with SOURCE_CATALOG_UNPROVIDED. Without a configuration read policy, env/configprops capabilities are disabled. A health endpoint's 503 may provide health evidence; other endpoint 503 responses are treated as unavailable.
