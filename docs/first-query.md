# First query: from the public package to runtime evidence

[Chinese overview](../README.zh-CN.md) · [Synthetic route demo](demo.md) · [Share trial feedback](trial-feedback.md)

This guide uses **0.2.11 Alpha** on Linux. You need Python 3.11+, [uv](https://docs.astral.sh/uv/getting-started/installation/), a working MCP client, and permission to read an existing local application's management endpoints. The MCP server needs no JDK or source checkout. Windows/macOS and the complete Boot/client matrix remain unverified.

If you have no authorized application ready, start with the [synthetic demo](demo.md). It runs the packaged tool handlers offline; it does not test a live Spring Boot application or an MCP client connection.

## 1. Install outside the source checkout

Run these commands in a terminal. Keep this terminal open for the following steps; `trial_dir` identifies your new installation.

```bash
python3 --version
uv --version
trial_dir="$(mktemp -d /tmp/spring-runtime-trial.XXXXXX)"
uv venv "$trial_dir/venv"
uv pip install --python "$trial_dir/venv/bin/python" --default-index https://pypi.org/simple spring-runtime-mcp==0.2.11
"$trial_dir/venv/bin/spring-runtime-mcp" --version
printf 'MCP executable: %s\n' "$trial_dir/venv/bin/spring-runtime-mcp"
```

The version command should print `spring-runtime-mcp 0.2.11`. Copy the absolute executable path printed last. This verifies installation only; it does not contact an application.

If `uv` is missing, install it using its official instructions and restart the terminal that launches your client. If the index cannot resolve the release, record the command and error and check the official index before retrying. An existing PyPI project page alone does not prove that an install succeeded.

## 2. Obtain the minimum target information

Ask the application maintainer for:

- An authorized management origin, reachable from the MCP process, such as `http://127.0.0.1:18081`. An origin has no path, query, fragment, or embedded credentials.
- An existing fixed `/actuator` base path. The first route query requires authorized GET access to `/actuator/mappings`; health needs `/actuator/health` instead.
- A local registration ID, such as `local`. This identifies the target and is independent of Spring Context IDs.
- If authentication is required, an existing Bearer token supplied through an agreed environment variable, such as `SHOP_ACTUATOR_TOKEN`.

Only registered loopback targets, fixed endpoints, and optional Bearer authentication are supported. Basic authentication, arbitrary headers, remote targets, and custom Actuator base paths are unsupported. Keep existing HTTPS and trusted certificate validation. In a container or remote workspace, loopback refers to that process's network namespace.

Endpoint exposure, application dependencies, authentication changes, and restarts require the application maintainer's authorization. The [target setup reference](target-app-setup.md) covers broader configuration that is not a prerequisite for this route query. Configuration diagnostics are disabled by default; leave them disabled for this trial.

## 3. Register the STDIO server in Codex CLI

Merge the table below into your existing `~/.codex/config.toml`, preserving other settings. Replace the example executable path with the path printed in step 1 and the origin with the approved target. The fields follow the [official Codex MCP documentation](https://learn.chatgpt.com/docs/extend/mcp).

```toml
[mcp_servers.spring_runtime]
command = "/tmp/spring-runtime-trial.REPLACE/venv/bin/spring-runtime-mcp"
args = ["--base-url", "http://127.0.0.1:18081", "--target-id", "local", "--token-env", "SHOP_ACTUATOR_TOKEN"]
env_vars = ["SHOP_ACTUATOR_TOKEN"]
startup_timeout_sec = 20
tool_timeout_sec = 30
```

For an authorized target that needs no authentication, remove `--token-env`, its following variable name, and the `env_vars` line. Keep authentication enabled for targets that require it.

Have your existing credential mechanism supply the token to the parent process that launches Codex. `env_vars` forwards a variable; it does not create or refresh a token. The value has no `Bearer ` prefix or whitespace. Keep token values out of TOML, command arguments, prompts, and feedback reports. A token set in a different terminal may not be inherited by the client.

```bash
codex mcp list
codex
```

Listing a server proves that its registration was read. In the session, inspect the MCP connection and tool discovery, for example with `/mcp`. A client must initialize the server and discover eight tools before invoking one. Starting the MCP executable directly in a terminal normally waits for STDIO requests; it has no interactive prompt.

Other [client templates](client-configuration.md) do not establish interoperability with every client/version.

## 4. Make one query and check the evidence

Choose a route whose path, HTTP method, and handler the application maintainer can verify independently. Ask your assistant:

> Use `springboot_verify_mappings` to check GET /orders/{id}. Report the registered paths, HTTP methods, Controller class and handler method, together with coverage gaps and any truncation. Read mapping metadata only; do not call the business endpoint or change application configuration.

`/orders/{id}` is an example: replace it with a route actually present in your application. Inspect the current input schema; the corresponding arguments are:

```json
{"pathPattern":"/orders/{id}","httpMethod":"GET","maxResults":1}
```

The selector uses `pathPattern` and `httpMethod`, not `path` and `method`. `maxResults` is between 1 and 50. The server reads mapping metadata; the method selector does not cause a request to the business route.

Check the structured envelope in the tool result. If viewing the raw MCP JSON-RPC response, it is at `result.structuredContent`.

| Field | What to check |
| --- | --- |
| `status`, `errors` | Did the tool obtain usable evidence or report a fixed diagnostic error? |
| `data.items` | Do the paths, methods, `controllerClass`, and `handlerMethod` agree with the approved source or another independent observation? |
| `coverage.state`, `coverage.gaps` | Is the evidence complete for the registered scope, or are important facts unavailable? |
| `totalMatched` | This is the total before result pagination; null means the count cannot be established. |
| `truncated`, `nextAction` | Is this only part of the result, and does the response suggest narrowing a filter? |

One item can be returned while `totalMatched` is larger than one. A `partial` result can contain useful facts. Empty items alone do not prove that a route is absent; evaluate the count, visibility, gaps, and filters together. Responses are sanitized and bounded to 16 KiB.

For optional Bean producer/condition correlation, see the [Source catalog guide](source-catalog.md). A catalog is not required for the first route or health query and cannot replace invisible runtime evidence.

## 5. Report the stage that passed or failed

Record four separate stages: installation/registration, MCP initialization and eight-tool discovery, authorized endpoint access, and a query with independently checked evidence. Passing one stage does not establish the next. Share a [trial report](trial-feedback.md) for a success or a blocked attempt.

| Symptom | Next check |
| --- | --- |
| Executable not found or client spawn failure | Verify the absolute path, executable permission, and the client's environment. |
| Initialize/discovery failure | Check the client connection, startup timeout, and safe stderr messages; registration alone is insufficient. |
| `TARGET_CONNECTION_REFUSED` / `TARGET_TIMEOUT` | Ask the maintainer to check the approved port, running process, and network namespace. |
| `ENDPOINT_UNAUTHORIZED` | Check the existing token, role, and authentication chain; a 401/403 does not by itself identify which is wrong. |
| `ENDPOINT_NOT_EXPOSED` / `ENDPOINT_UNAVAILABLE` | Confirm the fixed path, endpoint availability, and permission with the maintainer. |
| `INVALID_ARGUMENT` | Re-read the tool's input schema and correct names, types, and limits. |
| `CAPABILITY_DISABLED` for configuration | Leave configuration diagnostics disabled and use the route query for this trial. |

Retain unknown/partial evidence. Do not broaden access or disable authentication to turn an incomplete result into a successful trial.
