# ADR 005: Registered loopback targets only

**Status**: implemented

## Constraint

Targets must resolve within **127.0.0.0/8 or ::1** and come from registered configuration. Tool arguments cannot supply arbitrary origins, paths, or headers. Loopback registration does not grant permission to inspect every local process; application authorization remains required.

For each connection, resolve the target and validate the complete address set before connecting by numeric IP. Check the actual peer as well. Alternate address representations must pass the existing validation; they do not widen the allowed range.

## Transport and credentials

The connector uses fixed GET endpoints, disables environment proxies and redirects, and retains default HTTPS certificate and original-host name validation. Authentication credentials are bound to the registered connector and are never forwarded to another origin because of a redirect or upstream instruction.

Loopback restrictions reduce SSRF exposure but do not make arbitrary local services trusted. Fixed endpoints, registered capabilities, authentication, response budgets, sanitization, and the output gate remain necessary.

## Network namespaces and limits

127.0.0.1 refers to the MCP process's network namespace. A container or remote development process does not automatically reach a developer host's application. Do not automatically broaden bindings, expose ports, or create forwarding rules as a connection workaround.

The current product does not provide a remote-target mode or configurable nonloopback allowlist. Any application exposure, forwarding, credential, or restart change requires its own authorization and cannot be inferred from permission to run a diagnostic query.

## References

- [HTTP connector](../../../src/spring_runtime_mcp/transport/actuator_http.py)
- [Security architecture](../security-and-sanitization.md)
- [Target setup](../../target-app-setup.md)
- [First query](../../first-query.md)
- [ADR 004: configuration opt-in](004-config-diagnostics-opt-in.md)
