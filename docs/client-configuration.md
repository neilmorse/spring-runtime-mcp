# MCP 客户端配置

以下保留各客户端的参考模板。首次安装和 Bearer 转发见[首次接入指南](first-query.md)，目标端点配置见[目标指南](target-app-setup.md)。这些模板不构成完整客户端兼容性验收。

公开包命令需要 Python 3.11+ 和 uv；源码命令需要已同步的锁定开发环境。将仓库路径替换为当前检出目录，桌面客户端找不到命令时使用 uv/uvx 的绝对路径。凭据值由父进程环境提供，只转发变量名称。

## OpenAI Codex CLI

合并到 `~/.codex/config.toml`，或受信任项目中的 `.codex/config.toml`。[OpenAI 官方 MCP 配置](https://developers.openai.com/codex/mcp)。

```toml
[mcp_servers.spring_runtime]
command = "uvx"
args = ["--default-index", "https://pypi.org/simple", "spring-runtime-mcp==0.2.9", "--base-url", "http://127.0.0.1:18081"]
startup_timeout_sec = 20
tool_timeout_sec = 30
```

运行 `codex mcp list` 检查登记。列出登记仅说明配置被读取，不证明进程握手或目标端点授权。

对于已有 Bearer/JWT 鉴权的目标，可以用以下公开发行包配置替换上面的同名表；合并时保留其他服务器配置。
通过现有凭据配置流程，将 `SHOP_ACTUATOR_TOKEN` 提供给启动 Codex 的进程环境。
令牌值不要写入 TOML、命令参数或提示词；`env_vars` 只转发指定名称的环境变量，见上述官方配置说明。

```toml
[mcp_servers.spring_runtime]
command = "uvx"
args = ["--default-index", "https://pypi.org/simple", "spring-runtime-mcp==0.2.9", "--base-url", "http://127.0.0.1:18081", "--token-env", "SHOP_ACTUATOR_TOKEN"]
env_vars = ["SHOP_ACTUATOR_TOKEN"]
startup_timeout_sec = 20
tool_timeout_sec = 30
```

父进程没有该变量时，转发不会创建令牌，MCP 宿主会启动失败。
使用源码版命令时，同样追加 `--token-env SHOP_ACTUATOR_TOKEN`，并加入 `env_vars`。
调用前读取实际 `tools/list` 的 inputSchema；例如 `springboot_verify_mappings` 使用
`{"pathPattern":"/orders/{id}","httpMethod":"GET","maxResults":1}`，不接受 `path`/`method` 别名。
`maxResults` 必须是 1–50 的整数；该调用只读取映射元数据，不访问业务 URL。

以下为客户端参考模板，不构成完整互操作验收。字段来源：[Claude Desktop](https://modelcontextprotocol.io/docs/develop/connect-local-servers)、[Cursor](https://cursor.com/docs/mcp)、[VS Code](https://code.visualstudio.com/docs/agent-customization/mcp-servers)。

## Claude Desktop / Claude Code

Claude Desktop 通过 Settings → Developer → Edit Config 打开 `claude_desktop_config.json`；macOS 常见位置为 `~/Library/Application Support/Claude/claude_desktop_config.json`，Windows 为 `%APPDATA%\Claude\claude_desktop_config.json`。合并 `mcpServers`，不要覆盖已有服务器。命令依赖本机 `uv`；桌面客户端可能不继承终端 PATH。[本地接入说明](https://modelcontextprotocol.io/docs/develop/connect-local-servers)。

```json
{
  "mcpServers": {
    "spring-runtime": {
      "command": "uv",
      "args": ["run", "--locked", "--offline", "--project", "<仓库绝对路径>", "spring-runtime-mcp", "--base-url", "http://127.0.0.1:18081"]
    }
  }
}
```

Claude Code 在工作区根目录使用 `.mcp.json`，配置如下；用 `claude mcp list` 和会话内 `/mcp` 检查。Desktop 与 Code 的配置位置独立，不能认为修改一个会同步另一个。[Claude Code 官方说明](https://code.claude.com/docs/en/mcp)。

```json
{
  "mcpServers": {
    "spring-runtime": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--locked", "--offline", "--project", "<仓库绝对路径>", "spring-runtime-mcp", "--base-url", "http://127.0.0.1:18081"]
    }
  }
}
```

## Cursor

合并到项目 `.cursor/mcp.json`，或个人 `~/.cursor/mcp.json`；在 MCP 设置中检查服务状态与已加载工具。[Cursor 官方说明](https://cursor.com/docs/mcp)。

```json
{
  "mcpServers": {
    "spring-runtime": {
      "command": "uv",
      "args": ["run", "--locked", "--offline", "--project", "<仓库绝对路径>", "spring-runtime-mcp", "--base-url", "http://127.0.0.1:18081"]
    }
  }
}
```

## VS Code

合并到 `.vscode/mcp.json`，这里的顶层键是 `servers`。通过 `MCP: List Servers` 检查状态和输出。[VS Code 官方说明](https://code.visualstudio.com/docs/agent-customization/mcp-servers)。

```json
{
  "servers": {
    "spring-runtime": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--locked", "--offline", "--project", "<仓库绝对路径>", "spring-runtime-mcp", "--base-url", "http://127.0.0.1:18081"]
    }
  }
}
```

首次接入的验收顺序为：MCP initialize 完成 → `tools/list` 返回按名字排序的八个工具 → 一次只读调用返回符合 Schema 的脱敏结构。出现 `ENOENT`、启动超时或握手失败，先核查 `uv` 与仓库路径，不能用 `replay` 顶替。401/403 则检查目标现有授权，不关闭安全控制、不跟随 `/login`。
