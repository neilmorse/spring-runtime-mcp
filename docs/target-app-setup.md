# Target Spring Boot application setup

This guide configures standard observability in the target application. It installs no custom agent and does not turn business methods into MCP tools. The host reads registered loopback origins and supports `--token-env` binding to existing Bearer credentials. Basic, custom management base paths, and remote targets are unsupported. See [first query](first-query.md) for installation, credential forwarding, and queries, and [client configuration](client-configuration.md) for templates. Target dependencies, exposure, and restarts still require explicit application-maintainer authorization.

## 1. Check the version and existing authorization

The target needs `spring-boot-starter-actuator`, versioned by its own Spring Boot BOM. Use Flyway, Liquibase, and springdoc only when already needed by the application; diagnostics do not require business MCP starters, database tools, or bytecode agents.

| Boot version | Read-only ceiling | env/configprops value protection | Guide policy |
| --- | --- | --- | --- |
| 3.4+ / 4.x | Supports `management.endpoints.access.max-permitted` | `show-values: never` | Use the next template; configuration diagnostics stay disabled by default. |
| 3.0–3.3 | No equivalent global access ceiling | `show-values: never` | Remove unsupported access settings; enforce GET with the existing security layer. |
| 2.7 | No equivalent global access ceiling | Use legacy keys-to-sanitize; do not rely on show-values | Use the separate legacy template, disable env/configprops by default, and restrict HTTP methods. |

Version references: [Boot 3.4 access controls](https://docs.spring.io/spring-boot/3.4/reference/actuator/endpoints.html#actuator.endpoints.access), [Boot 3.3 endpoints](https://docs.spring.io/spring-boot/3.3/reference/actuator/endpoints.html), and [Boot 3.0 value masking](https://docs.spring.io/spring-boot/docs/3.0.13/reference/html/actuator.html#actuator.endpoints.sanitization). Legacy properties: [2.7 env API](https://docs.spring.io/spring-boot/docs/2.7.18/api/org/springframework/boot/actuate/autoconfigure/env/EnvironmentEndpointProperties.html) and [configprops API](https://docs.spring.io/spring-boot/docs/2.7.18/api/org/springframework/boot/actuate/autoconfigure/context/properties/ConfigurationPropertiesReportEndpointProperties.html).

An include list is not authorization; read-only does not make every GET safe. Exclude heapdump/logfile. Retain existing Spring Security, TLS, authentication, and business security chains; do not work around failures with `permitAll`, disabled CSRF, or `show-values=always`.

## 2. Boot 3.4+/4.x：application-local-mcp.yml

Save the complete template below in the **target application's** `src/main/resources/application-local-mcp.yml`. Example business and separate management ports are 8080 and 18081. Preserve the actual business port if different; the management port must be distinct and available.

```yaml
server:
  port: 8080
management:
  server:
    port: 18081
    address: 127.0.0.1
  endpoints:
    access:
      max-permitted: read-only
    web:
      base-path: /actuator
      exposure:
        include: health,beans,conditions,mappings,flyway,liquibase,startup,info,configprops,env
        exclude: shutdown,heapdump,logfile,sessions,loggers,caches,quartz
    jmx:
      exposure:
        exclude: "*"
  endpoint:
    env:
      access: none
      show-values: never
    configprops:
      access: none
      show-values: never
    health:
      show-details: never
```

Independent `management.server.address` binding requires a separate management port. Setting address while sharing the business port does not establish management isolation. See [management listener configuration](https://docs.spring.io/spring-boot/3.4/reference/actuator/monitoring.html). Do not change it to `0.0.0.0` or automatically expose ports for container/remote development. 127.0.0.1 belongs to the target process's namespace, not automatically the developer host.

include explicitly lists diagnostic capabilities; exclude additionally rejects dangerous reads. `env/configprops` remain unavailable through `access: none` despite appearing in the candidate list, matching this project's default. For ordinary Bean/route queries, narrow include to `health,beans,conditions,mappings`. Confirm need and authorization before enabling endpoints. Configuration cannot create migration data if Flyway/Liquibase is not installed.

Only when configuration-source diagnostics are needed and authorized, change each env/configprops `access: none` to `access: read-only`, keeping both `show-values: never`. Do not paste complete raw responses: `origin`, custom details, and resource fields may remain sensitive. MCP reads apply independent sanitization and registered-scope projection.

## 3. Legacy versions: remove unsupported properties

### Boot 3.0–3.3

Keep the previous ports, exposure, show-values, and health settings, but remove `management.endpoints.access` and both endpoint `access` properties. Set `management.endpoint.env.enabled: false` and `management.endpoint.configprops.enabled: false` to keep configuration diagnostics disabled. Explicit enablement must still retain show-values=never. Legacy applications need security-layer rejection of writes; enabled/exposure is not method authorization.

Use the application's existing Bearer authentication. Maintainers must merge rules into the security chain actually handling Actuator: permit authorized diagnostic roles to GET required fixed paths and reject other methods/unapproved paths. Start with `health`, `beans`, `conditions`, and `mappings`; separately approve `/actuator/health/liveness` and `/actuator/health/readiness` if needed.

Check chain scope, ordering, Bearer validators, and role mapping together. A separate higher-priority chain does not automatically inherit another chain's authentication. Adding `httpBasic()` cannot authenticate the MCP Bearer token. Use existing `SecurityFilterChain` for MVC and `SecurityWebFilterChain` for WebFlux, preserving business-route protection. Authentication depends on the application's implementation; generic new-chain code cannot replace a merge review. See [Boot security chains](https://docs.spring.io/spring-boot/3.3/reference/actuator/endpoints.html#actuator.endpoints.security).

A Basic-only management entry cannot be used directly by this MCP host. After a maintainer verifies and configures a usable Bearer entry, follow [first query](first-query.md) to forward the named variable and perform an actual tool call.

### Boot 2.7

Replace section 2 with the complete template below; do not mix in 3.4 access or 3.x show-values properties. `keys-to-sanitize: [".*"]` conservatively masks all legacy property keys but cannot guarantee safe arbitrary origins/exception text. env/configprops therefore remain disabled and excluded from exposure.

```yaml
server:
  port: 8080
management:
  server:
    port: 18081
    address: 127.0.0.1
  endpoints:
    web:
      base-path: /actuator
      exposure:
        include: health,beans,conditions,mappings,flyway,liquibase,startup,info
        exclude: shutdown,heapdump,logfile,sessions,loggers,caches,quartz,env,configprops
    jmx:
      exposure:
        exclude: "*"
  endpoint:
    env:
      enabled: false
      keys-to-sanitize: [".*"]
    configprops:
      enabled: false
      keys-to-sanitize: [".*"]
    health:
      show-details: never
```

Boot 2.7/Spring Security 5.7 likewise needs fixed-path GET/role rules merged into the existing Bearer chain, using supported APIs while preserving business chains and authentication providers. Keep env/configprops disabled and do not mistake legacy value protection for active modern properties. See [Boot 2.7 security](https://docs.spring.io/spring-boot/docs/2.7.18/reference/html/actuator.html#actuator.endpoints.security).

Do not expose startup on legacy applications without method-level rejection rules. env/configprops require separate security review, removal of their enabled/exclude restrictions, and continued all-key masking; this is not the default local startup configuration.

## 4. Enable nondestructive startup snapshots

Import these two standard classes in the application entry point. `Application` represents the target's own `@SpringBootApplication` class; use `OrdersApplication.class` in the first line below if that is its actual name.

```java
import org.springframework.boot.SpringApplication;
import org.springframework.boot.context.metrics.buffering.BufferingApplicationStartup;
```

Inside the existing `main(String[] args)`, replace direct `SpringApplication.run(...)` with these **three lines**:

```java
SpringApplication application = new SpringApplication(Application.class);
application.setApplicationStartup(new BufferingApplicationStartup(2048));
application.run(args);
```

This configures native startup collection, without business changes or a third-party agent, before run. 2048 is buffer capacity, not a duration threshold. Collection begins with a new startup; proposing an entry-point change or restart does not authorize automatic execution. See [official startup collection](https://docs.spring.io/spring-boot/3.4/reference/features/spring-application.html#features.spring-application.application-startup).

Read only `GET /actuator/startup`. `POST /actuator/startup` reads and drains the buffer and is not used for collection, recovery, or troubleshooting verification. Missing, capacity-limited, or previously drained events cannot be restored; an empty timeline does not establish absence of bottlenecks. See the [Startup Web API](https://docs.spring.io/spring-boot/3.4/api/rest/actuator/startup.html).

## 5. Activate and verify manually

For an existing Maven Wrapper project, run this in the **target application's repository**, not the MCP repository, which has no wrapper. Retain required development profiles alongside local-mcp using the target's existing startup process, and verify the effective configuration.

```bash
./mvnw spring-boot:run -Dspring-boot.run.profiles=local-mcp
```

MCP acceptance uses existing Bearer authentication and actual tool queries; see [first query](first-query.md) for forwarding. The Basic commands below are only for maintainers checking an entry that already supports Basic. Their success does not establish MCP authentication; do not add Basic just to run them.

The example diagnostic user is `mcp-reader`; first confirm an existing user with the authorized role, or substitute the actual authorized account. curl prompts for a password, keeping it out of commands, URLs, configuration, and chat. These commands print HTTP status only, save no diagnostic JSON, and follow no redirects.

```bash
curl --noproxy '*' --connect-timeout 2 --max-time 5 --user mcp-reader --request GET --output /dev/null --write-out '%{http_code}\n' http://127.0.0.1:18081/actuator/health
curl --noproxy '*' --connect-timeout 2 --max-time 5 --user mcp-reader --request GET --output /dev/null --write-out '%{http_code}\n' http://127.0.0.1:18081/actuator/startup
```

These examples assume local HTTP on the management port. For existing HTTPS, retain the real HTTPS origin and trusted certificates; do not use `-k`. Bearer-only applications should use their existing protected credential process, without downgrading to Basic or placing tokens in shell history. The host independently binds existing Bearer credentials through `--token-env`; it does not forward a client's MCP token.

| Observation | Next check |
| --- | --- |
| Connection refused/timeout | Check profiles, listener, whether 18081 is running, and the network namespace without broadening binding. |
| 401/403 | Check existing credentials, roles, and diagnostic-chain ordering; do not use permitAll. |
| 301/302 or `/login` | Check the existing authentication entry; do not use `curl -L` or treat HTML as JSON. |
| 404 | Distinguish disabled/unexposed endpoints, access=none, incorrect path/port, and missing native capability. |
| health 200/503 with status only | Details are not visible; retain unknowns and request when-authorized details only if needed, not always by default. |
| startup 404/empty events | Check exposure, version-specific method guards, the native collector, and a fresh startup; never repair with POST. |
| env/configprops unavailable | Disabled is the default; enable only for an explicit diagnostic need, retaining target and local sanitization. |

Verify startup information and actual listeners to ensure the management port binds only to 127.0.0.1. Environment variables, arguments, or other profiles can override YAML; a file alone cannot establish safe binding. Keep info/custom Health details minimal; target masking does not replace local sanitization.

## 6. OpenAPI and cleanup

An application using springdoc may expose `/v3/api-docs` on the business port by default. This connector reads only fixed `/actuator/openapi` on the registered origin. Custom `springdoc.api-docs.path` does not trigger fallback; maintainers must confirm management-endpoint availability for the installed version. This guide does not automatically enable another path, switch ports, or enable springdoc business MCP tools.

The Actuator access rules above do not automatically protect business-port springdoc paths; existing application security still applies. OpenAPI `servers`, remote `$ref`, and description cannot extend diagnostic targets. `springboot_search_openapi` already exists, but an available business `/v3/api-docs` does not establish fixed management-endpoint availability or successful MCP search.

After diagnostics, deactivate local-mcp or narrow exposure and revoke temporary authorization. Application maintainers decide configuration changes and restarts. Retain sanitized structured conclusions, not raw env/configprops, health exception stacks, logs, or memory dumps.
