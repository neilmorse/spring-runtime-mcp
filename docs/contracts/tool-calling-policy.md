# Tool calling policy and error contract

Public contract version is 2, targeting MCP 2026-07-28; the host also supports the SDK legacy mode. The eight Tool definitions in [tools-contract.json](../../src/spring_runtime_mcp/schemas/tools-contract.json) are published by tools/list. Package-level contractVersion/protocolVersion are not sent as Tool fields.

## Discovery, arguments, and tool selection

Publish the fixed eight tools in ASCII name order. inputSchema/outputSchema use JSON Schema 2020-12 with references closed within each schema's `$defs`. Four explicit risk annotations are readOnlyHint=true, destructiveHint=false, idempotentHint=true, and openWorldHint=false; deterministic guards enforce actual permissions.

Server argument normalization explicitly applies Schema defaults. Tool argument JSON is capped at 16 KiB. Invalid fields, types, selectors, or limits yield INVALID_ARGUMENT without reading the target. Patterns are bounded, case-sensitive globs supporting `*` and `?`, up to 128 characters; other characters match literally. Combine filters with AND; packagePrefix matches package-segment boundaries.

| Diagnostic question | Tool and calling behavior |
| --- | --- |
| Slow startup | springboot_analyze_startup: read GET startup; sort by descending duration and stable identity, retaining parent chains and unit gaps. |
| Migration anomalies | springboot_check_migrations: engine=auto reads Flyway/Liquibase separately; prioritize anomalous states, then engine-reported order. |
| Source/runtime comparison | springboot_detect_drift: compare explicit dimensions only; detecting extra runtime objects requires complete expectations and runtime coverage. |
| Health anomalies | springboot_diagnose_health: healthy children and details are hidden by default; componentPath queries the local tree; probes use fixed health groups. |
| Bean or condition problems | springboot_inspect_beans: require a name, type, or package selector; read beans/conditions as needed, retaining usable Bean evidence if conditions are missing. |
| Configuration sources | springboot_inspect_config: require prefix/propertyKeyPattern, default includeValues=false; project only the operator-registered scope. |
| OpenAPI | springboot_search_openapi: schemaName is exclusive with operation selectors; httpMethod cannot stand alone. Fixed GET `/actuator/openapi`; in-document reference depth defaults to 2 and is capped at 8. |
| Route registration | springboot_verify_mappings: require path, method, or Controller selectors; read mappings only, without business-URL calls. |

Read each current tool Schema for exact selectors, enums, depth limits, and output fields. Examples do not define additional arguments.

## Results, pagination, and evidence

Build dependency relationships and reverse indices from all visible facts before filtering, counting, stable sorting, and pagination. maxResults defaults to and is capped at 50. Preserve truncated, truncationReasons, coverage, and nextAction on record/byte/depth/analysis limits; use totalMatched=null when a complete count cannot be established.

Continue with the original tool, target, and normalized query, adding only cursor. Snapshots share sanitized encoded records; cursors hold offsets and normal continuation handles only the current page. Default absolute TTL is 60 seconds with a 32 MiB total budget; continuation does not extend TTL. Policy-stamp changes revalidate the whole snapshot and remove associated handles if unsafe content is found.

nextAction.kind indicates page/refine/remediate/done; page uses nextCursor. filterSuggestions includes only safe arguments allowed by that tool; clients merge and revalidate them. On CURSOR_EXPIRED, restart without cursor; do not treat new results as continuation of the old snapshot.

- Bean aliases, parent chains, shadowing, nested conditions, and transitive blocking follow [normalization architecture](../architecture/cross-version-normalization.md). Uncovered source facts do not establish Bean absence.
- Preserve available components and gaps when health components are unreadable or status is missing; counts affected by gaps use totalMatched=null.
- Non-DispatcherServlet mappings coverage or unknown functional predicates remain partial/unknown; empty results cannot establish nonregistration.
- Missing migration fields use null/UNKNOWN; pending, MISSING_FAILED, and duration follow reported evidence. Liquibase version expectations do not replace changeSet identity.
- Omitted drift arrays mean no comparison; explicit empty arrays mean empty expectations. Bean/route/migration-version expectations total at most 100 entities. sourceRevision/sourceModifiedAt are caller declarations; insufficient evidence remains candidate/unknown.

## Configuration reads

env/configprops are disabled by default. Operators register property, prefix, or profile permissions through the CLI; intersect queries with policy. The connector reads only fixed `/actuator/env` and `/actuator/configprops`. Local filters neither shrink upstream responses nor expose dynamic paths such as `/env/{property}`.

includeValues defaults to false. Explicit value access still applies registration, field projection, and both sanitization layers. Values, input values, and origin share sensitivity context; mask or omit secrets. activeProfiles follows actual reports, never guessed property strings; unsafe source representations remain null/unknown. See [security architecture](../architecture/security-and-sanitization.md).

## Errors and local recipes

outputSchema validates the domain envelope in structuredContent. Fixed local logic produces DiagnosticError code, endpointId, httpStatus, retryable, message, and remediation. Recipes contain recipeId, action, configKeys, steps, requiresApproval, and retryAfterMs, without echoing original exceptions or upstream instructions.

| Observation | Actual code and handling |
| --- | --- |
| Invalid arguments | INVALID_ARGUMENT; refineQuery, no network access |
| Unregistered target/disabled capability | TARGET_NOT_REGISTERED / CAPABILITY_DISABLED |
| 401/403 | ENDPOINT_UNAUTHORIZED, retaining HTTP status; reviewAuthorization |
| 3xx | REDIRECT_BLOCKED, no redirect following; reviewAuthorization |
| Ordinary endpoint 404 | ENDPOINT_NOT_EXPOSED; reviewExposure |
| startup 404 | STARTUP_DATA_UNAVAILABLE; configureStartup, though status alone does not prove the collector is missing |
| Other rejected status, including 405 | ENDPOINT_UNAVAILABLE; startup 5xx suggests configureStartup, others use general endpoint guidance |
| Unsupported media/encoding or incomplete response | UNEXPECTED_CONTENT_TYPE / UNSUPPORTED_CONTENT_ENCODING / INCOMPLETE_RESPONSE |
| Timeout/connection failure | TARGET_TIMEOUT / TARGET_CONNECTION_REFUSED / TARGET_CONNECTION_FAILED |
| Unsafe output/cache or budget violation | Fixed codes such as UNSAFE_OUTPUT / SANITIZATION_FAILED / RESPONSE_TOO_LARGE; stop that branch |
| Expired cursor/changed query | CURSOR_EXPIRED / CURSOR_QUERY_MISMATCH; rebuild the query or restore original arguments |

`failed()` maps INVALID_ARGUMENT to invalid, ENDPOINT_UNAUTHORIZED/TARGET_NOT_REGISTERED to denied, and other failures to unavailable. data/totalMatched are null, coverage.state=unavailable, and errors is nonempty. Valid ok/partial diagnoses have isError=false, including health DOWN, failed migrations, and evidence-backed drift.

The implementation fixes retryable=false and retryAfterMs=null. INVALID_ARGUMENT recipes have requiresApproval=false; other error recipes use true. Check existing same-scope authorization: recipe flags neither revoke nor extend it. Project permission rules govern target configuration, exposure, credential permissions, and restarts.

## Frames and call budgets

Results contain structuredContent and one TextContent whose text is the same sanitized object in compact JSON. Complete results use resultType=complete. The full JSON-RPC tool response, including request id, SDK metadata, and both copies, is capped at 16,384 UTF-8 bytes and rechecked by the host and actual send layer. Static tools/list Schemas are not trimmed to this tool-result limit.

The server enforces a 15-second tool deadline and two read slots per target. Agents should limit a round to four calls and 64 KiB combined results, then summarize and narrow scope. This cross-call policy is caller-managed, not a host session counter. Stop the affected branch on authorization, network, safety, or evidence blockers while completing independent diagnostics.

## Offline contract checks

```bash
uv run --no-sync python scripts/validate_tool_contract.py
```

Run in the locked development environment. Synthetic in-memory data checks ordering, risk annotations, isolated Schemas, local references, and positive/negative examples without connecting to Spring Boot. See the [release workflow](../launch/README.md) for validation tiers.
