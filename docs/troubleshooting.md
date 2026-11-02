# Troubleshooting

Use the fixed diagnostic code and the stage reached to choose the next check. Codes and recipes are implemented in [diagnostics.py](../src/spring_runtime_mcp/diagnostics.py); [calling policy](contracts/tool-calling-policy.md) defines status and remediation semantics. An HTTP status or empty result alone does not establish a root cause.

## First identify the stage

1. Installation and registration: is the executable available, and did the client load its configuration?
2. MCP initialization and discovery: did the session initialize and discover eight tools?
3. Authorized endpoint access: could the host read the required registered endpoint?
4. Query evidence: does the result agree with independently checked facts, including coverage and truncation?

See [first query](first-query.md) for the full workflow and [trial feedback](trial-feedback.md) for a minimal report. Registration success does not prove a query succeeded. A directly launched STDIO executable normally waits for requests without an interactive prompt.

## Argument and query errors

### INVALID_ARGUMENT

Arguments violate the tool contract. Check the actual inputSchema for required selectors, types, enums, lengths, and combined constraints. maxResults is 1–50; depth bounds are tool-specific. Invalid arguments do not read the target.

For OpenAPI operations, provide pathPattern or operationId; httpMethod cannot stand alone. schemaName is exclusive with operation selectors. The mappings tool separately permits a method-only selector.

Invalid OpenAPI example:

```json
{"httpMethod":"GET"}
```

Valid OpenAPI example:

```json
{"pathPattern":"/orders","httpMethod":"GET","maxResults":1}
```

Correct arguments using the [tool reference](contracts/tools-schema/README.md). Argument correction itself does not require changing target permissions.

## Target and authorization errors

### TARGET_NOT_REGISTERED

The requested target is not registered. Match targetId (default local) to the CLI registration. Check the approved --base-url and the corresponding SPRING_RUNTIME_BASE_URL / SPRING_RUNTIME_TARGET_ID defaults. A URL is not a tool argument.

### CAPABILITY_DISABLED

The required capability is disabled. Configuration diagnostics are disabled by default; register only the authorized prefixes/properties/profile scope when needed. --config-prefix and --config-property take one value per occurrence; --config-profiles is a Boolean switch.

Value output additionally needs both --config-allow-values and includeValues=true. Registration cannot widen target permissions or bypass sanitization. For a first trial, use mappings or health without enabling configuration diagnostics. See [configuration diagnostics](contracts/tools-schema/springboot_inspect_config.md).

### ENDPOINT_UNAUTHORIZED

The endpoint returned 401/403. Check existing Bearer credentials, parent-process environment forwarding, role mapping, and the security chain handling Actuator. Status alone cannot distinguish a missing/expired token from a role or chain problem.

--token-env names the variable; the parent process must supply its value. env_vars forwards the named variable and does not create a token. Keep token values out of commands, TOML, prompts, and reports. The host does not support Basic or arbitrary header forwarding.

Do not add permitAll, disable authentication, or change health-detail visibility to bypass a denial. See [target setup](target-app-setup.md) and [client configuration](client-configuration.md).

## Endpoint access errors

### ENDPOINT_NOT_EXPOSED

An ordinary endpoint returned 404. Ask the maintainer to check endpoint availability, exposure, version-specific access controls, fixed base path, and the registered management origin. A 404 does not uniquely establish missing exposure; authentication or path handling may also affect what is visible.

| Tool | Required fixed endpoint(s) |
| --- | --- |
| springboot_inspect_beans | beans; conditions when analysis requires it |
| springboot_verify_mappings | mappings |
| springboot_diagnose_health | health and the selected fixed health group |
| springboot_check_migrations | flyway and/or liquibase according to engine |
| springboot_analyze_startup | startup |
| springboot_inspect_config | env/configprops within registered policy |
| springboot_search_openapi | openapi |
| springboot_detect_drift | Endpoints needed for the explicit expectation dimensions |

All paths use the registered origin's fixed `/actuator/` table. Changes to dependencies, endpoint exposure, security rules, or restarts require maintainer authorization. See [target setup](target-app-setup.md).

### STARTUP_DATA_UNAVAILABLE

The startup endpoint returned 404. Check the installed Boot version's native startup capability, endpoint enablement/exposure, security method guards, and whether BufferingApplicationStartup was configured before run. The code is not proof that the collector alone is missing.

New startup data requires an authorized new startup. Missing, truncated, or drained events cannot be restored by a query. Read GET snapshots only; never POST, which drains the buffer. startup 5xx uses ENDPOINT_UNAVAILABLE with configuration guidance while retaining the original HTTP status. See [startup diagnostics](contracts/tools-schema/springboot_analyze_startup.md).

### REDIRECT_BLOCKED

The endpoint returned 3xx. Check the approved scheme, port, management origin, base path, and authentication entry. Use the correct existing HTTPS origin and trusted certificate configuration when applicable. Do not follow redirects or infer a new target from Location. HTML login pages are not diagnostic JSON.

Other rejected HTTP statuses, including 405, use ENDPOINT_UNAVAILABLE. Health-family 503 JSON can be valid health evidence; a reachable process is not necessarily healthy.

## Network and timeout errors

### TARGET_TIMEOUT

A read or shared tool deadline expired. Check the target's load, responsiveness, network namespace, read queue, and the work requested.

The CLI --timeout sets reader timeout, default 5 seconds, accepting values greater than 0 and at most 60 seconds. Services separately waits at most 5 seconds per read. The fixed 15-second tool deadline includes queueing, multiple endpoint reads, analysis, and output checks; changing the CLI value does not extend it.

Restore the default only if the reader was deliberately configured shorter. For an endpoint already taking more than 5 seconds, increasing the CLI value does not extend Services' wait. Maintainers should investigate the target response and load. Selective filters, lower maxResults, and shallower supported depth can reduce local work/output, but they do not shrink the fixed upstream response.

### TARGET_CONNECTION_REFUSED

A connection was refused. Ask the maintainer to check whether the approved process and port are listening and reachable from the MCP process's namespace. Keep the registered origin and loopback boundaries; do not automatically expose ports, broaden bindings, or create forwarding rules.

### TARGET_CONNECTION_FAILED

Connection setup failed. Check network reachability, DNS resolution, trusted certificates, certificate validity, and original-host name matching. The connector verifies the entire resolved address set, connects by numeric IP, and checks the peer. Do not disable TLS verification or environment-proxy restrictions as a workaround.

Cancellation and timeout abort the connection and wait briefly for worker cleanup. System DNS calls cannot be forcibly terminated, so tool timeout does not prove every underlying thread stopped immediately. See [security architecture](architecture/security-and-sanitization.md).

## Data and budget errors

### RESPONSE_TOO_LARGE

Safe output cannot fit the complete 16,384-byte JSON-RPC tool-response budget, including both structured and text copies. Narrow selectors, reduce returned records, or use supported depth/detail controls.

Generic pagination reduces this page's record count; Bean tools may trim associations. Tools do not all use the same halving algorithm or guarantee one retained item. A result that still cannot fit returns a fixed error. Upstream response budgets are separate from output and graph budgets.

### UNEXPECTED_CONTENT_TYPE

The endpoint returned an unsupported media type. Check the fixed path, management origin, target security chain, and any gateway transformation. Accepted JSON representations include application/json and supported Actuator v2/v3 JSON media types. Do not interpret an HTML error/login page as JSON or follow a redirect.

Related fixed read failures include UNSUPPORTED_CONTENT_ENCODING, INCOMPLETE_RESPONSE, malformed JSON, and header/body budget violations. Preserve the code and endpoint identity; do not paste the original body into a report. See [security architecture](architecture/security-and-sanitization.md) for accepted encodings and read limits.

## Cursor and pagination errors

### CURSOR_EXPIRED

The snapshot is unavailable. Default TTL is 60 seconds from creation, not from the previous page; LRU eviction or process restart can remove it earlier. Start a new query without cursor. The new result is a new observation, not continuation of the expired snapshot.

### CURSOR_QUERY_MISMATCH

The cursor does not match the tool or normalized query. Resend the original tool and arguments, adding only nextCursor as cursor. Do not change filters or maxResults for continuation. If you want a different query, omit cursor and start again.

Interpret totalMatched, truncated, coverage.gaps, and nextAction together. Depth/analysis truncation may have no nextCursor. Null totals must stay unknown. See the [common envelope](contracts/tools-schema/common-envelope.md).

## Safety and sanitization errors

### UNSAFE_OUTPUT

The independent safety gate rejected output or cached data. Preserve the guard and stop that diagnostic branch. Report minimal fixed codes and a reviewed synthetic reproduction through the [security policy](../SECURITY.md). Do not export raw data, disable sanitization, or weaken a failing security assertion.

### SANITIZATION_FAILED

The sanitization boundary could not produce safe data. Treat the branch as failed. A more precise query may help isolate a reproduction, but cannot justify bypassing the gate. Report persistent failures using reviewed, minimal information and preserve unavailable/unknown evidence.

## Reference

[Calling policy](contracts/tool-calling-policy.md) defines actual error/status/recipe mappings. INVALID_ARGUMENT maps to invalid; ENDPOINT_UNAUTHORIZED/TARGET_NOT_REGISTERED map to denied; other failed envelopes map to unavailable. Failures have data=null, totalMatched=null, unavailable coverage, and nonempty errors. Health DOWN, failed migrations, and evidence-backed drift can instead be valid ok/partial diagnoses.

retryable is currently false and retryAfterMs null. Recipe approval flags must be interpreted alongside existing same-scope authorization. A suggested action does not grant permission to change or restart a target.

See [tool Schemas](contracts/tools-schema/README.md), [implementation conventions](architecture/implementation-conventions.md), and [target setup](target-app-setup.md) for field constraints and boundaries.
