# MCP client configuration

These are reference templates for individual clients. See the [first-query guide](first-query.md) for installation and Bearer forwarding, and [target setup](target-app-setup.md) for endpoint configuration. Templates do not establish a complete client compatibility matrix.

Public-package commands require Python 3.11+ and uv; source commands require the synchronized locked development environment. Replace repository paths with your checkout. Use absolute uv/uvx paths if desktop clients cannot find them. Credentials come from the parent process environment; forward variable names only.

## OpenAI Codex CLI

Merge into `~/.codex/config.toml` or a trusted project's `.codex/config.toml`. See [official OpenAI MCP configuration](https://learn.chatgpt.com/docs/extend/mcp).

```toml
[mcp_servers.spring_runtime]
command = "uvx"
args = ["--default-index", "https://pypi.org/simple", "spring-runtime-mcp==0.2.11", "--base-url", "http://127.0.0.1:18081"]
startup_timeout_sec = 20
tool_timeout_sec = 30
```

Run `codex mcp list` to check registration. Listing proves configuration was read, not that initialization or target authorization succeeded.

For a target with existing Bearer/JWT authentication, replace the same-named table with this public-package configuration while preserving other servers.
Use your existing credential mechanism to supply `SHOP_ACTUATOR_TOKEN` to the process launching Codex.
Keep token values out of TOML, command arguments, and prompts. `env_vars` forwards only the named variables; see the official configuration reference above.

```toml
[mcp_servers.spring_runtime]
command = "uvx"
args = ["--default-index", "https://pypi.org/simple", "spring-runtime-mcp==0.2.11", "--base-url", "http://127.0.0.1:18081", "--token-env", "SHOP_ACTUATOR_TOKEN"]
env_vars = ["SHOP_ACTUATOR_TOKEN"]
startup_timeout_sec = 20
tool_timeout_sec = 30
```

Forwarding does not create a missing parent-process variable; the MCP host will fail to start without it.
For source commands, likewise append `--token-env SHOP_ACTUATOR_TOKEN` and add `env_vars`.
Read inputSchema from the actual `tools/list` response before calling. For example, `springboot_verify_mappings` accepts
`{"pathPattern":"/orders/{id}","httpMethod":"GET","maxResults":1}`; `path`/`method` aliases are unsupported.
`maxResults` must be an integer from 1 to 50. This call reads mapping metadata only, never the business URL.

The following client templates are references, not complete interoperability checks. Field sources: [Claude Desktop](https://modelcontextprotocol.io/docs/develop/connect-local-servers), [Cursor](https://cursor.com/docs/mcp), and [VS Code](https://code.visualstudio.com/docs/agent-customization/mcp-servers).

## Claude Desktop / Claude Code

In Claude Desktop, open Settings → Developer → Edit Config to edit `claude_desktop_config.json`. Common locations are `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS and `%APPDATA%\Claude\claude_desktop_config.json` on Windows. Merge `mcpServers` without overwriting other servers. Commands require local `uv`; desktop processes may not inherit the terminal PATH. See the [local connection guide](https://modelcontextprotocol.io/docs/develop/connect-local-servers).

```json
{
  "mcpServers": {
    "spring-runtime": {
      "command": "uv",
      "args": ["run", "--locked", "--offline", "--project", "<absolute-repository-path>", "spring-runtime-mcp", "--base-url", "http://127.0.0.1:18081"]
    }
  }
}
```

Claude Code uses `.mcp.json` at the workspace root. Check with `claude mcp list` and in-session `/mcp`. Desktop and Code use separate configuration locations; editing one does not synchronize the other. See the [official Claude Code guide](https://code.claude.com/docs/en/mcp).

```json
{
  "mcpServers": {
    "spring-runtime": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--locked", "--offline", "--project", "<absolute-repository-path>", "spring-runtime-mcp", "--base-url", "http://127.0.0.1:18081"]
    }
  }
}
```

## Cursor

Merge into project `.cursor/mcp.json` or personal `~/.cursor/mcp.json`; inspect server status and loaded tools in MCP settings. See the [official Cursor guide](https://cursor.com/docs/mcp).

```json
{
  "mcpServers": {
    "spring-runtime": {
      "command": "uv",
      "args": ["run", "--locked", "--offline", "--project", "<absolute-repository-path>", "spring-runtime-mcp", "--base-url", "http://127.0.0.1:18081"]
    }
  }
}
```

## VS Code

Merge into `.vscode/mcp.json`, whose top-level key is `servers`. Use `MCP: List Servers` to inspect status and output. See the [official VS Code guide](https://code.visualstudio.com/docs/agent-customization/mcp-servers).

```json
{
  "servers": {
    "spring-runtime": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--locked", "--offline", "--project", "<absolute-repository-path>", "spring-runtime-mcp", "--base-url", "http://127.0.0.1:18081"]
    }
  }
}
```

Accept a first connection in order: MCP initialize succeeds → `tools/list` returns eight name-sorted tools → one read-only call returns sanitized Schema-valid data. For `ENOENT`, startup timeout, or handshake failure, check `uv` and checkout paths first; `replay` is not a substitute. For 401/403, check existing target authorization without disabling security or following `/login`.
