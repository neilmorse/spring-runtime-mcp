# 首次接入：公开包到第一次只读查询

本路径使用公开发行包 **0.2.6 Alpha**，无需检出源码、JDK 或开发依赖。
需要 Python 3.11+、[uv](https://docs.astral.sh/uv/getting-started/installation/)、已可用的编码客户端，以及应用维护者授予的目标读取权限。
Linux 命令示例；Windows/macOS 本轮未验收。历史验收记录不代表本次运行。

## 1. 安装并确认入口

在仓库外执行，安装到自己选择的全新目录（下面路径必须尚不存在）：

```bash
python3 --version
uv --version
uv venv /tmp/spring-runtime-user
uv pip install --python /tmp/spring-runtime-user/bin/python --default-index https://pypi.org/simple spring-runtime-mcp==0.2.6
/tmp/spring-runtime-user/bin/spring-runtime-mcp --version
```

最后应输出 `spring-runtime-mcp 0.2.6`。此命令只核验入口，不连接目标。
也可以使用 `uvx --default-index https://pypi.org/simple spring-runtime-mcp==0.2.6 --version`；首次下载可能超过客户端握手等待时间，先在终端完成安装，再接入客户端。

`uv`/`uvx` 找不到时按官方安装说明安装并重启启动客户端的终端；用 `command -v uv` 核验 PATH。推荐配置绝对入口路径，避免桌面进程与终端 PATH 不一致。
索引报找不到版本时，记录命令、索引与错误。PyPI 项目页有版本元数据，不等于所用镜像的 simple 索引已有文件，更不等于安装成功。可核对上述明确的公开 PyPI 索引后重试一次；不要随意换源或把本地 wheel 安装记为公开命名安装成功。

## 2. 向维护者取得最小登记信息

- 已获权、在客户端所在网络命名空间可达的回环管理 origin，例如 `http://127.0.0.1:18081`。
- 固定 `/actuator` 基路径；首次路由查询需要已启用、已暴露且获权读取的 `mappings`。健康查询需要 `health`；Bean/条件查询分别需要 `beans`/`conditions`。
- 自选登记 ID，例如 `local`；它标识本地目标，不是 Spring Context ID。
- 若目标要求 Bearer，取得已有安全流程提供的令牌，并约定变量名，例如 `SHOP_ACTUATOR_TOKEN`。

`--base-url` 只接受 http(s) origin，不包含 `/actuator`、用户信息、查询串或 fragment；当前只支持回环、标准基路径及既有 Bearer，不支持 Basic、自定义头或远程目标。已有 HTTPS 继续验证受信证书。
[目标配置指南](target-app-setup.md)供维护者按需审阅；新增依赖、暴露端点、凭据权限和重启都需要维护者授权，不应把整份观测配置作为首次查询前提。不要启用 env/configprops。

## 3. 最小 Codex CLI 配置

字段依据 [OpenAI 官方 MCP 文档](https://learn.chatgpt.com/docs/extend/mcp)（2026-11-01 核对）：`command`、`args`、`env_vars`、`startup_timeout_sec`、`tool_timeout_sec`。
将入口替换为第 1 步实际安装的绝对路径。已有配置只合并该表，不覆盖其他服务器。

```toml
[mcp_servers.spring_runtime]
command = "/tmp/spring-runtime-user/bin/spring-runtime-mcp"
args = ["--base-url", "http://127.0.0.1:18081", "--target-id", "local", "--token-env", "SHOP_ACTUATOR_TOKEN"]
env_vars = ["SHOP_ACTUATOR_TOKEN"]
startup_timeout_sec = 20
tool_timeout_sec = 30
```

无 Bearer 的已授权目标，删除 `--token-env` 及紧随的变量名，并删除 `env_vars` 行。
令牌值必须由既有凭据流程注入**启动 Codex 的父进程环境**；`env_vars` 只列变量名，负责转发到 MCP 子进程，不生成或刷新令牌。不加 `Bearer ` 前缀，不含空白/换行；宿主自行组装认证头。不要把值写入 TOML、shell 参数、历史、提示词或报告。变量存在于另一个终端不代表当前客户端能继承；修改环境后重新启动客户端及 MCP 子进程。

可用独立目录试验，保留全局配置：

```bash
mkdir -p /tmp/spring-runtime-codex
# 将上面的 TOML 保存为 /tmp/spring-runtime-codex/config.toml（无令牌值）
CODEX_HOME=/tmp/spring-runtime-codex codex mcp list
CODEX_HOME=/tmp/spring-runtime-codex codex
```

独立 `CODEX_HOME` 还隔离客户端登录状态；如需登录，沿用客户端官方登录流程，不把全局认证文件复制进报告。`mcp list` 只能证明登记被读取；实际会话握手与查询仍需下一步。直接在终端启动宿主后等待 STDIO 客户端是正常行为，没有交互提示也不证明卡住；退出可按 Ctrl-C。不要把 replay 命令配置为宿主。

其他客户端模板见 README，属于参考模板；本轮不声明 Claude、Cursor 或 VS Code 验收通过。

## 4. 发现工具并查询

要求客户端按顺序完成 `initialize` → 初始化通知 → `tools/list`。应发现按名称排序的八工具：

```text
springboot_analyze_startup
springboot_check_migrations
springboot_detect_drift
springboot_diagnose_health
springboot_inspect_beans
springboot_inspect_config
springboot_search_openapi
springboot_verify_mappings
```

发现工具不读取目标，也不证明目标鉴权成功。先查看实际 `inputSchema`，从获权 Controller 源码选择一条已知路由；以下 `/orders/{id}` 仅为示例，必须替换为目标已有路由：

```json
{"pathPattern":"/orders/{id}","httpMethod":"GET","maxResults":1}
```

请客户端调用 `springboot_verify_mappings`，只读取 mappings，不请求业务 URL。
核对 `data.items` 的路径、HTTP 方法和 handler 是否与源码相符。故意使用 `path`/`method` 会得到 `INVALID_ARGUMENT`；按返回的 inputSchema 提示改为 `pathPattern`/`httpMethod` 再试。`maxResults` 只能为 1–50 的整数。

分别确认四层：登记读取成功、协议握手与八工具成功、目标获权读取成功、查询有可交叉核对的事实。前一层成功不能代替后一层。
`partial` 可以是有效结果：结合 `coverage.gaps`、`totalMatched`、`truncated`、`nextAction` 解读。`totalMatched: null` 表示不能确认完整数量；空结果不能直接证明对象不存在。健康详情隐藏、条件缺失、源码类型图不完整或预算截断都应保留 unknown/partial。不要为消除 partial 自动扩大权限。

基础查询成功后，如需 Bean 生产者/条件关联，再按[源码目录指南](source-catalog.md)登记已核实的 source catalog；它不是首次路由/健康查询前提，也不能补齐不可见的运行证据。

## 5. 按故障层修正

提示与错误码是本地安全模板；不要粘贴令牌、原始响应或堆栈求助。下面的下一步是检查项，不是单凭错误就确定根因。

| 可见现象 | 能确定什么 | 下一步与授权边界 |
| --- | --- | --- |
| 命令不存在、客户端 spawn 失败 | 入口未启动 | 核对安装环境、绝对路径、可执行权限和客户端 PATH；无需改目标 |
| 索引无对应版本 | 当前安装未成功 | 区分项目元数据、simple 索引和下载结果；记录失败后核对明确的公开源 |
| `--version` 与安装元数据不一致 | 当前源码/环境可能混用 | 开发者在检出目录运行 `uv sync --dev --locked --offline --reinstall-package spring-runtime-mcp`，强制重装本地包后重新核验入口与元数据；仅同步依赖可能保留旧元数据；公开包用户使用全新环境重装，不需开发依赖 |
| 宿主没有输出、一直等待 | 可能仅在等 STDIO 客户端 | 由客户端启动并 initialize；不要以手工启动无输出判断目标故障 |
| base-url / ADDRESS_DENIED 启动提示 | 本地登记未通过校验 | 使用不带路径的回环 origin；不扩大白名单、关闭 TLS 或代理守卫 |
| token 变量缺失/为空 | MCP 子进程未取得非空值 | 检查父进程环境与 `env_vars`；只检查是否存在，不打印值；刷新/提权需维护者授权 |
| token 格式非法 | 本地 Bearer 格式校验失败 | 沿用凭据流程重新取得无前缀、无空白的令牌；格式通过不代表目标接受 |
| catalog 不可读/非普通文件/非法内容 | 启动前目录加载失败 | 核对当前用户读取权限、绝对路径、大小和 JSON 格式；`SOURCE_TARGET_MISMATCH` 时使目录 targetId 与登记一致；不更改工具 Schema |
| 登记成功但 initialize 失败 | 登记不等于宿主启动/协议成功 | 看客户端安全 stderr，核对 command、参数、变量、安装耗时与超时；不要先改应用安全链 |
| list 成功，`TARGET_CONNECTION_REFUSED` / `TARGET_TIMEOUT` / `TARGET_CONNECTION_FAILED` | 协议可用，但本次读取失败 | 核对端口、进程、网络命名空间、监听和响应时限；重启、目标配置变更需授权 |
| `ENDPOINT_UNAUTHORIZED`，401/403 | 请求被拒绝，不能单凭状态码确定令牌过期或角色原因 | 维护者核对令牌有效性、角色、诊断安全链及网关；不改 permitAll、不跟随登录重定向 |
| `ENDPOINT_NOT_EXPOSED` / `ENDPOINT_UNAVAILABLE` | 本次端点未能提供证据 | 核对端口/固定路径、版本、是否启用/暴露及原生能力；404 可能被安全链重写，新增暴露/重启需授权 |
| `CAPABILITY_DISABLED` | 本地能力未登记 | 配置诊断默认关闭属正常；首次查询换 mappings/health，不启用 env/configprops |
| `INVALID_ARGUMENT` | 工具参数不符合契约 | 读取该工具实际 inputSchema，改正字段名、选择器、类型及 1–50 限制；无需目标改动 |
| 有事实但 partial、健康只有 status、条件 unknown | 当前证据不支持完整结论 | 保留已知事实并报告 gaps；只有诊断确实需要时才向维护者申请额外证据 |

## 源码开发路径（与公开安装分开）

开发者检出仓库后使用 `uv sync --dev --locked` 与 `uv run --no-sync spring-runtime-mcp ...`。
缓存完整后可加 `--offline`。本地 wheel/源码候选验收需明确标注，不能替代公开命名安装证据。
