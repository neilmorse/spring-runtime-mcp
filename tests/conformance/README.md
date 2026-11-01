# Offline Conformance Suite

Run from the repository root:

```bash
uv run --no-sync python -m pytest -q tests/conformance
uv run --no-sync python -m pytest -q
```

Use the locked development environment prepared with `uv sync --dev --locked`; cached synchronization can add `--offline`. Tests do not resolve a hostname,
connect a socket, start a JVM, or require diagnostic credentials. The parent
`tests/conftest.py` blocks DNS and socket connection APIs; this suite also tests
that guard. The injected transport records policy arguments and returns local
bytes or exceptions. It never constructs a URL or follows a Location header.

## Coverage and evidence levels

| Matrix | Fixture / test | What is actually verified |
| --- | --- | --- |
| Boot 2.7 Servlet | `boot-2.7-servlet/` | javax descriptor, MVC dispatcher, V2 details / V3 components, two Flyway beans in one context |
| Boot 3.4 Servlet | `boot-3.4-servlet/` | Jakarta descriptor, MVC dispatcher, nested conditions, startup parent tree, Liquibase changeSets |
| Boot 4.1 WebFlux | `boot-4.1-webflux/` | Reactive handler descriptor and dispatcherHandlers; separate supplementary Jakarta Servlet example |
| Bean and Condition algorithms | `test_multiversion_fixtures.py` | Actual normalizers/handler, aliases, parent contexts, ANY/ALL/NONE children and two-hop source-factory-property attribution |
| Eight tools | `contracts/*.json`, `test_tools_contract.py` | Nonempty typed examples, input/outputSchema validation, URL/header/method escalation rejection, negative mutations, risk annotations and deterministic definition order |
| Connection refused / read timeout | `test_faults.py` | Real ResponseGateReader converts injected errno exceptions into safe codes; shared errors conform for all eight tools |
| 404 / startup unavailable | `test_faults.py` | Exposure recipe includes config key; startup recipe checks exposure and proposes native BufferingApplicationStartup configuration with approval |
| 401 / 403 / redirects | `test_faults.py` | Real gate checks status before JSON; GET + follow_redirects=False; exactly one request; structured authorization recipe |
| Hidden Health details | `faults/health-hidden*` | Real gate preserves DOWN-only body; independent partial golden has no fabricated child components |
| 2,500 Beans | `large/beans-2500.json`, `test_large_response.py` | Actual filtering and paging, disjoint successive pages without rereading, complete index before slicing, bounded associations at default depth |
| Every validated result | `assertions.py` | Published schema, explicit RFC3339 checker, risk booleans, eight-name order, identical structured/text copies and complete JSON-RPC ≤16,384 UTF-8 bytes |

All eight handlers and the official SDK STDIO host exist in the production package. The static examples here verify result shapes independently of handler execution. Conformance, unit, security and integration tests exercise different boundaries; examples alone do not prove live target behavior. For the call chain and the corresponding test entry points, see the [system overview](../../docs/architecture/system-overview.md) and [security test guide](../security/README.md).

## Transport boundary

`src/spring_runtime_mcp/transport/response_gate.py` implements an injectable
request/response policy boundary. It passes fixed GET, disabled redirects,
5-second timeout and an 8 MiB limit to a registered transport, enforces its own
await timeout, checks status/media type before JSON, and bounds accepted bytes.
The production stdlib connector is `transport/actuator_http.py`. It enforces loopback resolution, numeric-address connections, peer checks, TLS verification and bounded streaming. Injected transport tests here verify the gate; they do not by themselves prove connector behavior or a full live TLS/SNI matrix. See the [security architecture](../../docs/architecture/security-and-sanitization.md) for that boundary.

Fault recipes never change target configuration. Startup 404 does not prove
which of endpoint exposure, security or absent startup collection caused it;
the recipe explicitly asks the operator to check those prerequisites. For
hidden Health details, review `management.endpoint.health.show-details` and
existing authorization locally; never enable unrestricted details automatically.

The offline jsonschema installation lacks its optional RFC3339 checker.
`assertions.FORMATS` registers a deterministic calendar/offset checker so malformed
date-time values cannot silently pass. Negative tests retain the malformed values.
