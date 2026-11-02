# ADR 004: Configuration diagnostics disabled by default

**Status**: implemented

## Constraint

env/configprops capabilities are **disabled by default**. Operators explicitly register allowed prefixes, properties, or profile access through the CLI. Tool queries intersect that policy and cannot widen it.

```bash
spring-runtime-mcp --base-url http://127.0.0.1:18081 --config-prefix spring.application
```

```bash
spring-runtime-mcp --base-url http://127.0.0.1:18081 --config-property spring.application.name
```

`--config-prefix` and `--config-property` accept one value per occurrence; repeat them for multiple entries. `--config-profiles` is a Boolean switch for active-profile reads. These are host startup examples, not completed MCP queries. Existing target authentication still applies; see the [first-query guide](../../first-query.md) for Bearer forwarding.

## Values and evidence

includeValues defaults to false. Value output requires both CLI `--config-allow-values` and tool includeValues=true. Even then, registration scope, field projection, sensitive-context propagation, sanitization, and the independent output gate still apply.

The connector reads complete fixed `/actuator/env` and `/actuator/configprops` responses within upstream budgets. Local selectors do not reduce upstream response size or create a dynamic `/env/{property}` request.

Without the required capability, return CAPABILITY_DISABLED with an unavailable envelope. Changing host registration does not itself expose endpoints or grant application permissions. Target changes and restarts require authorization.

## Operational effects

Operators control what the tool may project, and values stay hidden unless explicitly allowed. A narrower scope still needs an authorized, readable upstream endpoint. Property names, origins, inputs, and binding values can share sensitivity; sanitization alone does not justify unrestricted configuration collection.

A changed scope requires reconfiguring the host. Existing authorization, TLS, and target-side value protection remain in effect. Keep unknown sources and unavailable values null/unknown rather than filling them with guessed defaults.

## References

- [CLI arguments](../../../src/spring_runtime_mcp/cli.py)
- [Configuration policy](../../../src/spring_runtime_mcp/policy/configuration.py)
- [Configuration adapter](../../../src/spring_runtime_mcp/adapters/config.py)
- [Configuration tool reference](../../contracts/tools-schema/springboot_inspect_config.md)
- [ADR 005: loopback targets](005-loopback-only-targets.md)
