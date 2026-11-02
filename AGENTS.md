# Agent working rules

This project converts Actuator/OpenAPI data from registered loopback Spring Boot instances into eight read-only MCP tools.
Use the [documentation index](docs/README.md) to read relevant chapters; see [SPEC](SPEC.md) for scope. Tool Schemas define the fields. Do not pre-read every document.
Update the relevant current-state documents when code behavior changes. Document implemented behavior and limitations only; keep historical rationale and future ideas out of current descriptions.
Do not read or search `.human/` or `CHANGELOG.md` by default. Access only the scope explicitly requested by the user; ignore rules are not access controls.
Use `.agent/PLANS.md` only for tasks spanning multiple stages. Read an execution plan only when referenced by the current task; old records do not carry forward authorization or pending work.

## Implementation and security
Use four-space indentation, type annotations, and snake_case in Python; public JSON uses camelCase. Follow existing module responsibilities and preserve user changes.
Adapters have different signatures: check actual inputs and outputs before editing. See [implementation conventions](docs/architecture/implementation-conventions.md) for interfaces and error propagation.
Propagate missing evidence through gaps/Fact to the envelope, using null and unknown/partial. Never fabricate certainty with empty strings, defaults, or empty results.
Predefine new error codes in `diagnostics.py`, matching `[A-Z][A-Z0-9_]{0,63}`. Read production environment variables only in `cli.py`.
Prefix private helpers with `_`; inline type guards and do not add a standalone `type_guards.py`.
For Bean, condition, drift, or OpenAPI changes, check every relevant [graph, three-valued condition, and reference rule](docs/architecture/cross-version-normalization.md). Establish all visible associations before pagination.
Targets and endpoints must come from registered configuration. Use read-only GET only. Prohibit writes, redirects, environment proxies, arbitrary URL/path/header forwarding, and remote references. Never bypass authentication, TLS/peer checks, sanitization, or budgets.
External responses pass through two sanitization layers. Never expose credentials, raw env/configprops value trees, exception stacks, or remote instructions. Do not read heapdump or raw logfile; configuration diagnostics are disabled by default.
stdout carries JSON-RPC only; write sanitized logs to stderr. Sort the eight tools by name and retain all four risk annotations. maxResults defaults to and is capped at 50. The complete response containing both copies is limited to 16,384 bytes.
Preserve totalMatched, truncated, coverage, nextAction, and unknown-evidence semantics. See the [security architecture](docs/architecture/security-and-sanitization.md) for network and output details.
Protected core areas under `src/spring_runtime_mcp/`: `models/`, `policy/sanitization.py`, `diagnostics.py`, `transport/actuator_http.py`, `transport/response_gate.py`, and `server.py`.
Core-branch changes require existing characterization tests or explicit authorization. Add characterization tests first if module coverage is below 80% or critical except/raise/boundary branches are uncovered.
Explain and obtain confirmation before adding a catch-all. Preserve existing fixed protocol/tool error conversions and connector paths that clean up and re-raise.
For unauthorized changes to public Schemas, runtime dependencies, target/IP ranges, exposure/collection configuration, restarts, or releases, prepare a concrete patch and impact assessment before asking for confirmation. Do not ask again for authorization covering the same scope.

## Validation and delivery
Use the uv.lock environment: first run `uv sync --dev --locked`, adding `--offline` once caches are complete. Default tests use synthetic data and self-hosted loopback fixtures only. Real instances require separate authorization.
Choose checks using the [validation workflow](docs/launch/README.md): Python changes require pytest and Ruff lint/format; src type changes also require mypy; Schema/validator changes require contract checks; packaging/resource changes require builds and wheel resource checks.
For documentation-only changes, check wording, paths, and links, then stop once those checks pass. Never weaken security tests or misrepresent checks, compatibility, or root causes. Do not commit, push, or publish without authorization.
Complete authorized edits, validation, and necessary fixes, then report behavior changes, actual checks, and remaining limits. A blocker pauses only the affected branch of work; continue independent work.
